"""Marching Squares algorithm for isocontour extraction.

Extracts polygon contours from a 2D scalar field at a given threshold.
Can be used for water shorelines, terrain elevation contours, density fields, etc.
"""

from typing import List, Tuple, Dict, Set, Optional, Callable
import numpy as np


# Type aliases
Point = Tuple[float, float]
Segment = Tuple[Point, Point]
Contour = List[Point]


def extract_contours(
    field: np.ndarray,
    threshold: float,
    origin: Tuple[float, float] = (0.0, 0.0),
    cell_size: float = 1.0,
    sample_fn: Optional[Callable[[float, float], float]] = None
) -> List[Contour]:
    """Extract isocontours from a scalar field using marching squares.
    
    Args:
        field: 2D numpy array of scalar values
        threshold: Isovalue threshold (contour where field crosses this value)
        origin: World-space origin (x, y) of the field
        cell_size: Size of each cell in world units
        sample_fn: Optional function to sample field at world coordinates
                   (used for boundary edge segment water checks)
        
    Returns:
        List of contours, each a list of (x, y) points in world coordinates
    """
    height, width = field.shape
    
    # Collect all line segments from marching squares
    segments = _collect_segments(field, threshold, origin, cell_size, width, height)
    
    # Add boundary edge segments to close contours that touch edges
    if sample_fn is not None:
        _add_boundary_segments(
            segments, field, threshold, origin, cell_size, 
            width, height, sample_fn
        )
    
    # Trace segments into closed contours
    contours = _trace_contours(segments, tolerance=cell_size * 0.01)
    
    return contours


def _collect_segments(
    field: np.ndarray,
    threshold: float,
    origin: Tuple[float, float],
    cell_size: float,
    width: int,
    height: int
) -> List[Segment]:
    """Collect line segments from all marching squares cells."""
    
    segments: List[Segment] = []
    ox, oy = origin
    
    for iy in range(height - 1):
        for ix in range(width - 1):
            # Corner values (top-left, top-right, bottom-right, bottom-left)
            v00 = field[iy, ix]          # top-left
            v10 = field[iy, ix + 1]      # top-right
            v11 = field[iy + 1, ix + 1]  # bottom-right
            v01 = field[iy + 1, ix]      # bottom-left
            
            # Compute case (4 bits)
            case = 0
            if v00 >= threshold: case |= 1
            if v10 >= threshold: case |= 2
            if v11 >= threshold: case |= 4
            if v01 >= threshold: case |= 8
            
            # Skip uniform cells
            if case == 0 or case == 15:
                continue
            
            # Cell world coordinates
            x0 = ox + ix * cell_size
            y0 = oy + iy * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            
            # Interpolate edge crossing points
            def lerp(va, vb, pa, pb):
                if abs(vb - va) < 1e-10:
                    return (pa + pb) / 2
                t = (threshold - va) / (vb - va)
                return pa + t * (pb - pa)
            
            top = (lerp(v00, v10, x0, x1), y0)
            right = (x1, lerp(v10, v11, y0, y1))
            bottom = (lerp(v01, v11, x0, x1), y1)
            left = (x0, lerp(v00, v01, y0, y1))
            
            # Get segments for this case
            cell_segments = _case_segments(case, top, right, bottom, left)
            segments.extend(cell_segments)
    
    return segments


def _case_segments(
    case: int,
    top: Point,
    right: Point,
    bottom: Point,
    left: Point
) -> List[Segment]:
    """Return line segments for a marching squares case.
    
    Corner layout:
      0---top---1
      |         |
     left     right
      |         |
      3--bottom-2
      
    Cases (binary): bit0=corner0, bit1=corner1, bit2=corner2, bit3=corner3
    """
    case_table = {
        # Single corner cases
        1:  [(left, top)],
        2:  [(top, right)],
        4:  [(right, bottom)],
        8:  [(bottom, left)],
        # Two adjacent corners
        3:  [(left, right)],
        6:  [(top, bottom)],
        12: [(right, left)],
        9:  [(bottom, top)],
        # Two opposite corners (saddle points)
        5:  [(left, top), (right, bottom)],
        10: [(top, right), (bottom, left)],
        # Three corners (one missing)
        7:  [(left, bottom)],
        11: [(bottom, right)],
        13: [(right, top)],
        14: [(top, left)],
    }
    return case_table.get(case, [])


def _add_boundary_segments(
    segments: List[Segment],
    field: np.ndarray,
    threshold: float,
    origin: Tuple[float, float],
    cell_size: float,
    width: int,
    height: int,
    sample_fn: Callable[[float, float], float]
) -> None:
    """Add edge segments along grid boundary to close contours."""
    
    ox, oy = origin
    x_min = ox
    x_max = ox + (width - 1) * cell_size
    y_min = oy
    y_max = oy + (height - 1) * cell_size
    
    # Collect boundary points from interior segments
    boundary_points: Dict[str, List[float]] = {
        'top': [], 'bottom': [], 'left': [], 'right': []
    }
    
    tol = 0.01
    for p1, p2 in segments:
        for p in [p1, p2]:
            if abs(p[1] - y_min) < tol:
                boundary_points['top'].append(p[0])
            if abs(p[1] - y_max) < tol:
                boundary_points['bottom'].append(p[0])
            if abs(p[0] - x_min) < tol:
                boundary_points['left'].append(p[1])
            if abs(p[0] - x_max) < tol:
                boundary_points['right'].append(p[1])
    
    # Check corners and add if above threshold
    corners = [
        ('top-left', x_min, y_min),
        ('top-right', x_max, y_min),
        ('bottom-left', x_min, y_max),
        ('bottom-right', x_max, y_max),
    ]
    for corner_name, cx, cy in corners:
        if sample_fn(cx, cy) >= threshold:
            if 'top' in corner_name:
                boundary_points['top'].append(cx)
            if 'bottom' in corner_name:
                boundary_points['bottom'].append(cx)
            if 'left' in corner_name:
                boundary_points['left'].append(cy)
            if 'right' in corner_name:
                boundary_points['right'].append(cy)
    
    # Add edge segments between consecutive boundary points
    def add_edge_segs(fixed_coord: float, varying_points: List[float], is_x_fixed: bool):
        varying_points = sorted(set(varying_points))
        if len(varying_points) < 2:
            return
        
        for i in range(len(varying_points) - 1):
            c1 = varying_points[i]
            c2 = varying_points[i + 1]
            mid = (c1 + c2) / 2
            
            # Sample actual field at midpoint
            if is_x_fixed:
                x, y = fixed_coord, mid
            else:
                x, y = mid, fixed_coord
            
            if sample_fn(x, y) >= threshold:
                if is_x_fixed:
                    segments.append(((fixed_coord, c1), (fixed_coord, c2)))
                else:
                    segments.append(((c1, fixed_coord), (c2, fixed_coord)))
    
    add_edge_segs(y_min, boundary_points['top'], False)
    add_edge_segs(y_max, boundary_points['bottom'], False)
    add_edge_segs(x_min, boundary_points['left'], True)
    add_edge_segs(x_max, boundary_points['right'], True)


def _trace_contours(
    segments: List[Segment],
    tolerance: float
) -> List[Contour]:
    """Connect segments into closed contours."""
    
    if not segments:
        return []
    
    def point_key(p: Point) -> Tuple[int, int]:
        return (round(p[0] / tolerance), round(p[1] / tolerance))
    
    # Build adjacency map
    point_to_segments: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    
    for seg_idx, (p1, p2) in enumerate(segments):
        k1 = point_key(p1)
        k2 = point_key(p2)
        
        if k1 not in point_to_segments:
            point_to_segments[k1] = []
        point_to_segments[k1].append((seg_idx, 0))
        
        if k2 not in point_to_segments:
            point_to_segments[k2] = []
        point_to_segments[k2].append((seg_idx, 1))
    
    # Trace contours
    used_segments: Set[int] = set()
    contours: List[Contour] = []
    
    for start_seg_idx in range(len(segments)):
        if start_seg_idx in used_segments:
            continue
        
        contour: Contour = []
        seg_idx = start_seg_idx
        direction = 0  # 0 = forward, 1 = backward
        
        for _ in range(len(segments) * 2):
            if seg_idx in used_segments:
                break
            
            used_segments.add(seg_idx)
            p1, p2 = segments[seg_idx]
            
            if direction == 0:
                contour.append(p1)
                current_point = p2
            else:
                contour.append(p2)
                current_point = p1
            
            # Find next segment
            key = point_key(current_point)
            candidates = point_to_segments.get(key, [])
            
            next_seg = None
            next_dir = 0
            for cand_idx, cand_end in candidates:
                if cand_idx not in used_segments:
                    next_seg = cand_idx
                    next_dir = 1 if cand_end == 1 else 0
                    break
            
            if next_seg is None:
                break
            
            seg_idx = next_seg
            direction = next_dir
        
        if len(contour) >= 3:
            contours.append(contour)
    
    return contours

