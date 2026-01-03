"""Chaikin's corner-cutting algorithm for polygon/polyline smoothing.

Produces smooth curves from angular polygons by iteratively cutting corners.
Can preserve boundary points/edges when smoothing contours that touch boundaries.

Also includes Douglas-Peucker simplification for reducing point count.
"""

from typing import List, Tuple, Optional
import math


Point = Tuple[float, float]
BoundaryRect = Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)


def smooth_polygon(
    points: List[Point],
    iterations: int = 2,
    boundary_rect: Optional[BoundaryRect] = None
) -> List[Point]:
    """Smooth a closed polygon using Chaikin's corner-cutting algorithm.
    
    Args:
        points: List of (x, y) polygon vertices
        iterations: Number of smoothing passes (more = smoother)
        boundary_rect: Optional (min_x, min_y, max_x, max_y) - if provided,
                      points on the boundary edges are kept fixed
                      
    Returns:
        Smoothed polygon vertices
    """
    if len(points) < 3:
        return list(points)
    
    # Remove duplicate endpoint if present
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    
    points = list(points)
    
    for _ in range(iterations):
        if len(points) < 3:
            break
        points = _chaikin_pass(points, boundary_rect, closed=True)
    
    return points


def smooth_polyline(
    points: List[Point],
    iterations: int = 2,
    boundary_rect: Optional[BoundaryRect] = None
) -> List[Point]:
    """Smooth an open polyline using Chaikin's corner-cutting algorithm.
    
    Args:
        points: List of (x, y) polyline vertices
        iterations: Number of smoothing passes
        boundary_rect: Optional boundary for fixed points
        
    Returns:
        Smoothed polyline vertices
    """
    if len(points) < 3:
        return list(points)
    
    points = list(points)
    
    for _ in range(iterations):
        if len(points) < 3:
            break
        points = _chaikin_pass(points, boundary_rect, closed=False)
    
    return points


def _chaikin_pass(
    points: List[Point],
    boundary_rect: Optional[BoundaryRect],
    closed: bool
) -> List[Point]:
    """Single pass of Chaikin subdivision."""
    
    new_points: List[Point] = []
    n = len(points)
    
    # For open polylines, keep first point
    if not closed:
        new_points.append(points[0])
    
    # Process each segment
    end_idx = n if closed else n - 1
    for i in range(end_idx):
        p0 = points[i]
        p1 = points[(i + 1) % n]
        
        p0_on_boundary = _is_on_boundary(p0, boundary_rect)
        p1_on_boundary = _is_on_boundary(p1, boundary_rect)
        
        # If segment lies along boundary edge, keep p0 (don't subdivide)
        if _segment_on_boundary(p0, p1, boundary_rect):
            new_points.append(p0)
        # If p0 is on boundary but p1 is not, keep p0 fixed + add one point
        elif p0_on_boundary and not p1_on_boundary:
            new_points.append(p0)
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.append(r)
        # If p1 is on boundary but p0 is not, add one point (p1 kept by next segment)
        elif p1_on_boundary and not p0_on_boundary:
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            new_points.append(q)
        else:
            # Normal Chaikin subdivision: create two points at 1/4 and 3/4
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.extend([q, r])
    
    # For open polylines, keep last point
    if not closed:
        new_points.append(points[-1])
    
    return new_points


def _is_on_boundary(p: Point, boundary_rect: Optional[BoundaryRect]) -> bool:
    """Check if point lies on any edge of the boundary rectangle."""
    if boundary_rect is None:
        return False
    
    min_x, min_y, max_x, max_y = boundary_rect
    tol = 0.01
    
    return (abs(p[0] - min_x) < tol or abs(p[0] - max_x) < tol or
            abs(p[1] - min_y) < tol or abs(p[1] - max_y) < tol)


def _segment_on_boundary(
    p0: Point,
    p1: Point,
    boundary_rect: Optional[BoundaryRect]
) -> bool:
    """Check if segment lies along a boundary edge (both points on same edge)."""
    if boundary_rect is None:
        return False
    
    min_x, min_y, max_x, max_y = boundary_rect
    tol = 0.01
    
    # Both points on left edge
    if abs(p0[0] - min_x) < tol and abs(p1[0] - min_x) < tol:
        return True
    # Both points on right edge
    if abs(p0[0] - max_x) < tol and abs(p1[0] - max_x) < tol:
        return True
    # Both points on top edge
    if abs(p0[1] - min_y) < tol and abs(p1[1] - min_y) < tol:
        return True
    # Both points on bottom edge
    if abs(p0[1] - max_y) < tol and abs(p1[1] - max_y) < tol:
        return True
    
    return False


# ============================================================================
# Fast Point Thinning (O(n))
# ============================================================================

def thin_points(
    points: List[Point],
    min_distance: float = 3.0
) -> List[Point]:
    """Remove points that are too close together. O(n) and very fast.
    
    Args:
        points: List of (x, y) vertices
        min_distance: Minimum distance between consecutive points
        
    Returns:
        Thinned point list
    """
    if len(points) < 3:
        return list(points)
    
    result = [points[0]]
    min_dist_sq = min_distance * min_distance
    
    for p in points[1:]:
        last = result[-1]
        dx = p[0] - last[0]
        dy = p[1] - last[1]
        if dx * dx + dy * dy >= min_dist_sq:
            result.append(p)
    
    return result


# ============================================================================
# Catmull-Rom to Cubic Bezier Conversion
# ============================================================================

def catmull_rom_to_bezier(
    points: List[Point],
    closed: bool = True,
    tension: float = 0.5
) -> List[Tuple[Point, Point, Point, Point]]:
    """Convert control points to cubic Bezier segments using Catmull-Rom.
    
    Catmull-Rom splines pass through all control points and produce
    smooth curves. This converts them to cubic Bezier format that
    Skia can render natively on the GPU.
    
    Args:
        points: Control points (the curve will pass through all of them)
        closed: If True, create a closed loop
        tension: Controls curve tightness (0.5 = standard Catmull-Rom)
        
    Returns:
        List of (p0, p1, p2, p3) Bezier segment tuples where:
        - p0 = start point
        - p1 = first control point  
        - p2 = second control point
        - p3 = end point
    """
    if len(points) < 2:
        return []
    
    if len(points) == 2:
        # Just a line
        return [(points[0], points[0], points[1], points[1])]
    
    segments = []
    n = len(points)
    
    # Catmull-Rom to Bezier conversion factor
    alpha = tension
    
    num_segments = n if closed else n - 1
    
    for i in range(num_segments):
        # Get 4 points for Catmull-Rom (p0, p1, p2, p3)
        # The curve is drawn between p1 and p2
        if closed:
            p0 = points[(i - 1) % n]
            p1 = points[i]
            p2 = points[(i + 1) % n]
            p3 = points[(i + 2) % n]
        else:
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[min(n - 1, i + 1)]
            p3 = points[min(n - 1, i + 2)]
        
        # Convert to cubic Bezier control points
        # Using standard Catmull-Rom to Bezier formula
        b0 = p1
        b1 = (
            p1[0] + (p2[0] - p0[0]) / (6 / alpha),
            p1[1] + (p2[1] - p0[1]) / (6 / alpha)
        )
        b2 = (
            p2[0] - (p3[0] - p1[0]) / (6 / alpha),
            p2[1] - (p3[1] - p1[1]) / (6 / alpha)
        )
        b3 = p2
        
        segments.append((b0, b1, b2, b3))
    
    return segments

