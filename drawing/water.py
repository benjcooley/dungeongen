"""Water visual rendering with Skia.

Renders water regions as filled polygons with shoreline and ripple effects.
"""

from typing import List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass
import math
import skia

if TYPE_CHECKING:
    from map.water_layer import WaterShape


Point = Tuple[float, float]
Contour = List[Point]


@dataclass
class WaterStyle:
    """Visual style for water rendering."""
    # Fill - transparent gray for black & white maps
    fill_color: Tuple[int, int, int, int] = (80, 80, 80, 100)
    
    # Shoreline stroke
    stroke_color: Tuple[int, int, int, int] = (40, 40, 40, 255)
    stroke_width: float = 3.5  # Thicker shoreline
    
    # Ripple lines
    ripple_color: Tuple[int, int, int, int] = (40, 40, 40, 200)
    ripple_width: float = 1.75  # Thicker ripples (half of stroke)
    ripple_insets: Tuple[float, float] = (8.0, 16.0)  # Ripple offsets from shore
    ripple_dash_range: Tuple[float, float] = (8.0, 40.0)  # Longer dashes
    ripple_gap_range: Tuple[float, float] = (16.0, 80.0)  # Longer gaps


def render_water(
    canvas: skia.Canvas,
    contours: List[Contour],
    style: Optional[WaterStyle] = None
) -> None:
    """Render water regions to a Skia canvas.
    
    Uses even-odd fill rule so that contours inside other contours
    create dry "island" areas (donut shapes).
    
    Args:
        canvas: Skia canvas to draw on
        contours: List of water contour polygons
        style: Visual style (uses default if None)
    """
    if style is None:
        style = WaterStyle()
    
    if not contours:
        return
    
    # Build a single combined path with even-odd fill for proper island handling
    combined_path = skia.Path()
    combined_path.setFillType(skia.PathFillType.kEvenOdd)
    
    for contour in contours:
        if len(contour) < 3:
            continue
        _add_contour_to_path(combined_path, contour)
    
    # Draw fill (even-odd rule handles islands automatically)
    fill_paint = skia.Paint(
        Color=skia.Color(*style.fill_color[:3], style.fill_color[3]),
        AntiAlias=True,
        Style=skia.Paint.kFill_Style
    )
    canvas.drawPath(combined_path, fill_paint)
    
    # Draw shoreline strokes for all contours
    stroke_paint = skia.Paint(
        Color=skia.Color(*style.stroke_color[:3], style.stroke_color[3]),
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeWidth=style.stroke_width
    )
    canvas.drawPath(combined_path, stroke_paint)
    
    # Draw ripple lines at each inset level for each contour
    for ci, contour in enumerate(contours):
        if len(contour) < 3:
            continue
        for li, inset in enumerate(style.ripple_insets):
            inset_contour = offset_polygon(contour, -inset)
            if len(inset_contour) >= 3:
                # Use contour index + level as seed for consistent but varied ripples
                _draw_ripple_line(canvas, inset_contour, style, seed=ci * 100 + li)


def render_water_shape(
    canvas: skia.Canvas,
    shape: "WaterShape",
    style: Optional[WaterStyle] = None
) -> None:
    """Render a WaterShape (outer boundary + islands) to a Skia canvas.
    
    Uses even-odd fill so islands appear as dry areas.
    
    Args:
        canvas: Skia canvas to draw on
        shape: WaterShape with outer contour and islands
        style: Visual style (uses default if None)
    """
    render_water(canvas, shape.all_contours, style)


def render_water_shapes(
    canvas: skia.Canvas,
    shapes: List["WaterShape"],
    style: Optional[WaterStyle] = None,
    bounds_filter: Optional[Tuple[float, float, float, float]] = None
) -> None:
    """Render multiple WaterShapes, optionally filtered by bounds.
    
    Args:
        canvas: Skia canvas to draw on
        shapes: List of WaterShape objects
        style: Visual style (uses default if None)
        bounds_filter: Optional (min_x, min_y, max_x, max_y) - only render
                       shapes that intersect this rectangle
    """
    for shape in shapes:
        # Skip shapes outside bounds filter
        if bounds_filter is not None:
            if not _bounds_intersect(shape.bounds, bounds_filter):
                continue
        
        render_water_shape(canvas, shape, style)


def _bounds_intersect(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float]
) -> bool:
    """Check if two bounding boxes intersect."""
    a_min_x, a_min_y, a_max_x, a_max_y = a
    b_min_x, b_min_y, b_max_x, b_max_y = b
    
    return (a_min_x <= b_max_x and a_max_x >= b_min_x and
            a_min_y <= b_max_y and a_max_y >= b_min_y)


def _contour_to_path(contour: Contour) -> skia.Path:
    """Convert a contour to a Skia path."""
    path = skia.Path()
    if not contour:
        return path
    
    path.moveTo(contour[0][0], contour[0][1])
    for x, y in contour[1:]:
        path.lineTo(x, y)
    path.close()
    
    return path


def _add_contour_to_path(path: skia.Path, contour: Contour) -> None:
    """Add a contour as a subpath to an existing Skia path."""
    if not contour:
        return
    
    path.moveTo(contour[0][0], contour[0][1])
    for x, y in contour[1:]:
        path.lineTo(x, y)
    path.close()


def _draw_ripple_line(
    canvas: skia.Canvas,
    contour: Contour,
    style: WaterStyle,
    seed: int = 0
) -> None:
    """Draw curvature-aware ripple lines along a contour.
    
    Gaps only appear in straight sections - ripples always flow
    through corners unbroken to avoid crossing artifacts.
    """
    import random
    
    if len(contour) < 3:
        return
    
    rng = random.Random(seed)
    
    paint = skia.Paint(
        Color=skia.Color(*style.ripple_color[:3], style.ripple_color[3]),
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeWidth=style.ripple_width,
        StrokeCap=skia.Paint.kRound_Cap
    )
    
    # Build distance -> curvature map
    curvatures = _compute_curvatures(contour)
    total_length = _contour_length(contour)
    
    if total_length < 10:
        return
    
    # Find positions where gaps are allowed (low curvature = straight sections)
    curvature_threshold = 0.15  # Below this = "straight enough" for gaps
    gap_allowed = _find_low_curvature_regions(contour, curvatures, curvature_threshold)
    
    min_dash, max_dash = style.ripple_dash_range
    min_gap, max_gap = style.ripple_gap_range
    
    # Random phase offset
    pos = rng.uniform(0, max_gap)
    sample_spacing = 2.0
    
    while pos < total_length:
        # Determine dash length
        dash_len = rng.uniform(min_dash, max_dash)
        end_pos = pos + dash_len
        
        # Extend through any corners until we hit a straight section
        while end_pos < total_length and not _can_gap_at(end_pos, gap_allowed, total_length):
            end_pos += 3.0  # Extend past the corner
        
        end_pos = min(end_pos, total_length)
        
        # Sample points for this segment
        points = []
        sample_pos = pos
        while sample_pos <= end_pos:
            pt = _point_at_distance(contour, sample_pos % total_length)
            if pt:
                points.append(pt)
            sample_pos += sample_spacing
        
        end_pt = _point_at_distance(contour, end_pos % total_length)
        if end_pt and (not points or points[-1] != end_pt):
            points.append(end_pt)
        
        # Draw the curved segment
        if len(points) >= 2:
            path = skia.Path()
            path.moveTo(points[0][0], points[0][1])
            for pt in points[1:]:
                path.lineTo(pt[0], pt[1])
            canvas.drawPath(path, paint)
        
        # Find next valid gap position
        gap_len = rng.uniform(min_gap, max_gap)
        next_pos = end_pos + gap_len
        
        # Skip past any corners to find a valid start position
        attempts = 0
        while next_pos < total_length and not _can_gap_at(next_pos, gap_allowed, total_length) and attempts < 20:
            next_pos += 2.0
            attempts += 1
        
        pos = next_pos


def _compute_curvatures(contour: Contour) -> List[float]:
    """Compute curvature at each vertex of a contour.
    
    Returns list of curvature values (higher = sharper corner).
    """
    n = len(contour)
    curvatures = []
    
    for i in range(n):
        p0 = contour[(i - 1) % n]
        p1 = contour[i]
        p2 = contour[(i + 1) % n]
        
        # Vectors from p1 to neighbors
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        
        # Lengths
        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if len1 < 1e-6 or len2 < 1e-6:
            curvatures.append(0.0)
            continue
        
        # Normalize
        v1 = (v1[0]/len1, v1[1]/len1)
        v2 = (v2[0]/len2, v2[1]/len2)
        
        # Dot product gives cos(angle) - closer to -1 = straighter
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        
        # Convert to curvature (0 = straight, 1 = sharp corner)
        # dot = -1 means 180° (straight), dot = 1 means 0° (hairpin)
        curvature = (1.0 + dot) / 2.0  # Normalize to 0-1
        curvatures.append(curvature)
    
    return curvatures


def _find_low_curvature_regions(
    contour: Contour,
    curvatures: List[float],
    threshold: float
) -> List[Tuple[float, float]]:
    """Find distance ranges where curvature is below threshold.
    
    Returns list of (start_dist, end_dist) tuples for "straight" regions.
    """
    n = len(contour)
    regions = []
    
    # Build cumulative distance array
    distances = [0.0]
    for i in range(n):
        p1 = contour[i]
        p2 = contour[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        distances.append(distances[-1] + math.sqrt(dx*dx + dy*dy))
    
    # Find contiguous low-curvature regions
    in_region = False
    region_start = 0.0
    
    for i in range(n):
        is_low = curvatures[i] < threshold
        
        if is_low and not in_region:
            region_start = distances[i]
            in_region = True
        elif not is_low and in_region:
            regions.append((region_start, distances[i]))
            in_region = False
    
    if in_region:
        regions.append((region_start, distances[n]))
    
    return regions


def _can_gap_at(distance: float, gap_regions: List[Tuple[float, float]], total_length: float) -> bool:
    """Check if a gap is allowed at this distance (in a straight section)."""
    distance = distance % total_length
    for start, end in gap_regions:
        if start <= distance <= end:
            return True
    return False


def _contour_length(contour: Contour) -> float:
    """Calculate total perimeter length of a contour."""
    if len(contour) < 2:
        return 0.0
    
    total = 0.0
    for i in range(len(contour)):
        p1 = contour[i]
        p2 = contour[(i + 1) % len(contour)]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        total += math.sqrt(dx * dx + dy * dy)
    return total


def _point_at_distance(contour: Contour, distance: float) -> Optional[Point]:
    """Get the point at a given distance along the contour."""
    if len(contour) < 2 or distance < 0:
        return None
    
    traveled = 0.0
    n = len(contour)
    
    for i in range(n):
        p1 = contour[i]
        p2 = contour[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        seg_len = math.sqrt(dx * dx + dy * dy)
        
        if seg_len < 1e-6:
            continue
        
        if traveled + seg_len >= distance:
            # Interpolate within this segment
            t = (distance - traveled) / seg_len
            return (p1[0] + dx * t, p1[1] + dy * t)
        
        traveled += seg_len
    
    # Return last point if we've gone past the end
    return contour[-1]


def _generate_ripple_curves(
    contour: Contour,
    style: WaterStyle,
    seed: int = 0
) -> List[List[Point]]:
    """Generate curvature-aware ripple curves along a contour.
    
    Gaps only appear in straight sections - ripples always flow
    through corners unbroken to avoid crossing artifacts.
    
    Returns list of point lists, each representing a curved segment.
    """
    import random
    
    if len(contour) < 3:
        return []
    
    rng = random.Random(seed)
    curves = []
    
    # Build curvature map
    curvatures = _compute_curvatures(contour)
    total_length = _contour_length(contour)
    
    if total_length < 10:
        return []
    
    # Find positions where gaps are allowed
    curvature_threshold = 0.15
    gap_allowed = _find_low_curvature_regions(contour, curvatures, curvature_threshold)
    
    min_dash, max_dash = style.ripple_dash_range
    min_gap, max_gap = style.ripple_gap_range
    sample_spacing = 2.0
    
    # Random phase offset
    pos = rng.uniform(0, max_gap)
    
    while pos < total_length:
        dash_len = rng.uniform(min_dash, max_dash)
        end_pos = pos + dash_len
        
        # Extend through any corners until we hit a straight section
        while end_pos < total_length and not _can_gap_at(end_pos, gap_allowed, total_length):
            end_pos += 3.0
        
        end_pos = min(end_pos, total_length)
        
        # Sample multiple points along this segment
        points = []
        sample_pos = pos
        while sample_pos <= end_pos:
            pt = _point_at_distance(contour, sample_pos % total_length)
            if pt:
                points.append(pt)
            sample_pos += sample_spacing
        
        # Make sure we get the end point
        end_pt = _point_at_distance(contour, end_pos % total_length)
        if end_pt and (not points or points[-1] != end_pt):
            points.append(end_pt)
        
        if len(points) >= 2:
            curves.append(points)
        
        # Find next valid gap position
        gap_len = rng.uniform(min_gap, max_gap)
        next_pos = end_pos + gap_len
        
        # Skip past any corners to find a valid start position
        attempts = 0
        while next_pos < total_length and not _can_gap_at(next_pos, gap_allowed, total_length) and attempts < 20:
            next_pos += 2.0
            attempts += 1
        
        pos = next_pos
    
    return curves


def offset_polygon(contour: Contour, distance: float) -> Contour:
    """Offset a polygon inward (negative) or outward (positive).
    
    Uses simple vertex normal offsetting. For complex shapes,
    consider a proper polygon offset library.
    
    Args:
        contour: Original polygon vertices
        distance: Offset distance (negative = inward/shrink)
        
    Returns:
        Offset polygon vertices
    """
    if len(contour) < 3:
        return list(contour)
    
    n = len(contour)
    result = []
    
    for i in range(n):
        # Get adjacent vertices
        p_prev = contour[(i - 1) % n]
        p_curr = contour[i]
        p_next = contour[(i + 1) % n]
        
        # Edge vectors
        e1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        e2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        
        # Edge normals (perpendicular, pointing inward for CCW polygons)
        n1 = _normalize((-e1[1], e1[0]))
        n2 = _normalize((-e2[1], e2[0]))
        
        if n1 is None or n2 is None:
            result.append(p_curr)
            continue
        
        # Average normal (bisector)
        avg_n = ((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2)
        avg_n = _normalize(avg_n)
        
        if avg_n is None:
            result.append(p_curr)
            continue
        
        # Compute offset factor to maintain distance along bisector
        # This prevents sharp corners from being too far or too close
        dot = n1[0] * avg_n[0] + n1[1] * avg_n[1]
        if abs(dot) < 0.1:
            factor = 1.0
        else:
            factor = 1.0 / max(dot, 0.1)
        factor = min(factor, 3.0)  # Clamp to avoid extreme offsets at sharp angles
        
        # Offset vertex
        offset_dist = distance * factor
        new_x = p_curr[0] + avg_n[0] * offset_dist
        new_y = p_curr[1] + avg_n[1] * offset_dist
        result.append((new_x, new_y))
    
    return result


def _normalize(v: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """Normalize a 2D vector."""
    length = math.sqrt(v[0] * v[0] + v[1] * v[1])
    if length < 1e-10:
        return None
    return (v[0] / length, v[1] / length)


# ============================================================================
# SVG rendering (for debugging/web)
# ============================================================================

def contour_to_svg_path(contour: Contour, close: bool = True) -> str:
    """Convert a contour to an SVG path string."""
    if not contour:
        return ""
    
    parts = [f"M {contour[0][0]:.2f},{contour[0][1]:.2f}"]
    for x, y in contour[1:]:
        parts.append(f"L {x:.2f},{y:.2f}")
    
    if close:
        parts.append("Z")
    
    return " ".join(parts)


def render_water_shape_svg(
    shape: "WaterShape",
    style: Optional[WaterStyle] = None
) -> str:
    """Generate SVG elements for a WaterShape (outer + islands)."""
    return render_water_svg(shape.all_contours, style)


def render_water_shapes_svg(
    shapes: List["WaterShape"],
    style: Optional[WaterStyle] = None,
    bounds_filter: Optional[Tuple[float, float, float, float]] = None
) -> str:
    """Generate SVG for multiple WaterShapes, optionally filtered by bounds."""
    elements = []
    for shape in shapes:
        if bounds_filter is not None:
            if not _bounds_intersect(shape.bounds, bounds_filter):
                continue
        elements.append(render_water_shape_svg(shape, style))
    return "\n".join(elements)


def render_water_svg(
    contours: List[Contour],
    style: Optional[WaterStyle] = None
) -> str:
    """Generate SVG elements for water regions.
    
    Uses even-odd fill rule so contours inside other contours
    create dry "island" areas.
    """
    if style is None:
        style = WaterStyle()
    
    if not contours:
        return ""
    
    elements = []
    
    # Combine all contours into a single path with even-odd fill
    path_parts = []
    for contour in contours:
        if len(contour) < 3:
            continue
        path_parts.append(contour_to_svg_path(contour))
    
    if path_parts:
        combined_path = " ".join(path_parts)
        
        # Fill + stroke with even-odd rule
        fr, fg, fb, fa = style.fill_color
        sr, sg, sb, sa = style.stroke_color
        fill = f"rgba({fr},{fg},{fb},{fa/255:.2f})"
        stroke = f"rgba({sr},{sg},{sb},{sa/255:.2f})"
        
        elements.append(
            f'<path d="{combined_path}" '
            f'fill="{fill}" '
            f'fill-rule="evenodd" '
            f'stroke="{stroke}" '
            f'stroke-width="{style.stroke_width}"/>'
        )
    
    # Ripples for each contour (randomized curved segments)
    rr, rg, rb, ra = style.ripple_color
    ripple_stroke = f"rgba({rr},{rg},{rb},{ra/255:.2f})"
    
    for ci, contour in enumerate(contours):
        if len(contour) < 3:
            continue
        for li, inset in enumerate(style.ripple_insets):
            inset_contour = offset_polygon(contour, -inset)
            if len(inset_contour) >= 3:
                curves = _generate_ripple_curves(
                    inset_contour, style, seed=ci * 100 + li
                )
                for curve_points in curves:
                    if len(curve_points) >= 2:
                        # Build SVG path from points
                        path_d = f"M {curve_points[0][0]:.2f},{curve_points[0][1]:.2f}"
                        for pt in curve_points[1:]:
                            path_d += f" L {pt[0]:.2f},{pt[1]:.2f}"
                        elements.append(
                            f'<path d="{path_d}" '
                            f'fill="none" '
                            f'stroke="{ripple_stroke}" '
                            f'stroke-width="{style.ripple_width}" '
                            f'stroke-linecap="round"/>'
                        )
    
    return "\n".join(elements)
