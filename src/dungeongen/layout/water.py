"""Water generation using Marching Squares algorithm."""

from typing import List, Tuple, Callable, Optional, Dict, Set
from dataclasses import dataclass
import math

try:
    from opensimplex import OpenSimplex
except ImportError:
    OpenSimplex = None


@dataclass
class WaterRegion:
    """A water pool with organic boundary."""
    boundary: List[Tuple[float, float]]  # Polygon points
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y


class WaterGenerator:
    """Generates water regions from noise using marching squares."""
    
    def __init__(self, seed: int):
        self.seed = seed
        if OpenSimplex is None:
            raise ImportError("opensimplex library required for water generation")
        self.noise = OpenSimplex(seed)
        self.noise2 = OpenSimplex(seed + 1000)
        self.noise3 = OpenSimplex(seed + 2000)
    
    def sample(self, x: float, y: float) -> float:
        """Sample combined water noise at a point."""
        base = self.noise.noise2(x * 0.06, y * 0.06)
        shape = self.noise2.noise2(x * 0.15, y * 0.15)
        detail = self.noise3.noise2(x * 0.3, y * 0.3)
        return base * 0.6 + shape * 0.3 + detail * 0.1
    
    def generate_water_regions(
        self,
        bounds: Tuple[int, int, int, int],
        threshold: float = 0.1,
        resolution: float = 0.5,
        floor_mask: Optional[Callable[[float, float], bool]] = None,
        min_area: float = 1.0,
        smooth: bool = False
    ) -> List[WaterRegion]:
        """Generate water regions within bounds."""
        
        min_x, min_y, max_x, max_y = bounds
        
        # Sample grid
        nx = int((max_x - min_x) / resolution) + 2
        ny = int((max_y - min_y) / resolution) + 2
        
        # Build value grid
        grid = {}
        for iy in range(ny):
            for ix in range(nx):
                x = min_x + ix * resolution
                y = min_y + iy * resolution
                
                if floor_mask and not floor_mask(x, y):
                    grid[(ix, iy)] = -1.0
                else:
                    grid[(ix, iy)] = self.sample(x, y)
        
        # Extract contours
        contours = self._marching_squares(grid, nx, ny, threshold, min_x, min_y, resolution)
        
        # Grid boundary for preserving edge segments during smoothing
        grid_boundary = (
            min_x,
            min_y,
            min_x + (nx - 1) * resolution,
            min_y + (ny - 1) * resolution
        )
        
        # Filter and create regions
        regions = []
        for contour in contours:
            if len(contour) < 3:
                continue
            
            area = self._polygon_area(contour)
            if area < min_area:
                continue
            
            if smooth:
                contour = chaikin_smooth(contour, iterations=2, boundary_rect=grid_boundary)
            
            xs = [p[0] for p in contour]
            ys = [p[1] for p in contour]
            region_bounds = (min(xs), min(ys), max(xs), max(ys))
            regions.append(WaterRegion(boundary=contour, bounds=region_bounds))
        
        return regions
    
    def _marching_squares(
        self, 
        grid: Dict[Tuple[int, int], float],
        nx: int, 
        ny: int,
        threshold: float,
        origin_x: float,
        origin_y: float,
        resolution: float
    ) -> List[List[Tuple[float, float]]]:
        """
        Marching squares - collect segments then trace contours.
        """
        
        # Collect all line segments from all cells
        # Each segment is ((x1,y1), (x2,y2))
        all_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        
        for iy in range(ny - 1):
            for ix in range(nx - 1):
                v00 = grid.get((ix, iy), -1)      # top-left
                v10 = grid.get((ix+1, iy), -1)    # top-right
                v11 = grid.get((ix+1, iy+1), -1)  # bottom-right
                v01 = grid.get((ix, iy+1), -1)    # bottom-left
                
                # Compute case (4 bits)
                case = 0
                if v00 >= threshold: case |= 1
                if v10 >= threshold: case |= 2
                if v11 >= threshold: case |= 4
                if v01 >= threshold: case |= 8
                
                if case == 0 or case == 15:
                    continue
                
                # Cell world coordinates
                x0 = origin_x + ix * resolution
                y0 = origin_y + iy * resolution
                x1 = x0 + resolution
                y1 = y0 + resolution
                
                # Interpolate crossing points
                def lerp(va, vb, pa, pb):
                    if abs(vb - va) < 1e-10:
                        return (pa + pb) / 2
                    t = (threshold - va) / (vb - va)
                    return pa + t * (pb - pa)
                
                # Edge crossing points
                top = (lerp(v00, v10, x0, x1), y0)
                right = (x1, lerp(v10, v11, y0, y1))
                bottom = (lerp(v01, v11, x0, x1), y1)
                left = (x0, lerp(v00, v01, y0, y1))
                
                # Get segments for this case
                segments = self._case_segments(case, top, right, bottom, left)
                all_segments.extend(segments)
        
        # Add boundary edge segments to close contours that touch the grid edges
        self._add_boundary_segments(
            all_segments, nx, ny, threshold, origin_x, origin_y, resolution
        )
        
        # Now trace contours from segments
        return self._trace_segments(all_segments, resolution * 0.01)
    
    def _add_boundary_segments(
        self,
        segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        nx: int,
        ny: int,
        threshold: float,
        origin_x: float,
        origin_y: float,
        resolution: float
    ) -> None:
        """
        Add edge segments along the grid boundary to close contours that touch edges.
        """
        # Grid boundary coordinates
        x_min = origin_x
        x_max = origin_x + (nx - 1) * resolution
        y_min = origin_y
        y_max = origin_y + (ny - 1) * resolution
        
        # Collect boundary points from interior segments
        boundary_points: Dict[str, List[float]] = {
            'top': [], 'bottom': [], 'left': [], 'right': []
        }
        
        for p1, p2 in segments:
            for p in [p1, p2]:
                if abs(p[1] - y_min) < 0.01:
                    boundary_points['top'].append(p[0])
                if abs(p[1] - y_max) < 0.01:
                    boundary_points['bottom'].append(p[0])
                if abs(p[0] - x_min) < 0.01:
                    boundary_points['left'].append(p[1])
                if abs(p[0] - x_max) < 0.01:
                    boundary_points['right'].append(p[1])
        
        # Check corners and add them if water exists there
        corners = [
            ('top-left', x_min, y_min),
            ('top-right', x_max, y_min),
            ('bottom-left', x_min, y_max),
            ('bottom-right', x_max, y_max),
        ]
        for corner_name, cx, cy in corners:
            if self.sample(cx, cy) >= threshold:
                if 'top' in corner_name:
                    boundary_points['top'].append(cx)
                if 'bottom' in corner_name:
                    boundary_points['bottom'].append(cx)
                if 'left' in corner_name:
                    boundary_points['left'].append(cy)
                if 'right' in corner_name:
                    boundary_points['right'].append(cy)
        
        # Add edge segments between consecutive boundary points where water exists
        def add_edge_segments(edge_name: str, fixed_coord: float, 
                             varying_points: List[float], is_x_fixed: bool) -> None:
            varying_points = sorted(set(varying_points))
            if len(varying_points) < 2:
                return
            
            for i in range(len(varying_points) - 1):
                c1 = varying_points[i]
                c2 = varying_points[i + 1]
                mid = (c1 + c2) / 2
                
                # Sample actual noise at the midpoint
                if is_x_fixed:
                    x, y = fixed_coord, mid
                else:
                    x, y = mid, fixed_coord
                
                if self.sample(x, y) >= threshold:
                    if is_x_fixed:
                        segments.append(((fixed_coord, c1), (fixed_coord, c2)))
                    else:
                        segments.append(((c1, fixed_coord), (c2, fixed_coord)))
        
        add_edge_segments('top', y_min, boundary_points['top'], False)
        add_edge_segments('bottom', y_max, boundary_points['bottom'], False)
        add_edge_segments('left', x_min, boundary_points['left'], True)
        add_edge_segments('right', x_max, boundary_points['right'], True)
    
    def _case_segments(
        self,
        case: int,
        top: Tuple[float, float],
        right: Tuple[float, float],
        bottom: Tuple[float, float],
        left: Tuple[float, float]
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Return line segments for marching squares case.
        
        Corner layout:
          0---top---1
          |         |
         left     right
          |         |
          3--bottom-2
          
        Cases (binary): bit0=corner0, bit1=corner1, bit2=corner2, bit3=corner3
        """
        
        # Each case defines which edges to connect
        case_table = {
            # Single corner cases
            1:  [(left, top)],           # corner 0 only
            2:  [(top, right)],          # corner 1 only
            4:  [(right, bottom)],       # corner 2 only
            8:  [(bottom, left)],        # corner 3 only
            
            # Two adjacent corners
            3:  [(left, right)],         # corners 0,1
            6:  [(top, bottom)],         # corners 1,2
            12: [(right, left)],         # corners 2,3
            9:  [(bottom, top)],         # corners 3,0
            
            # Two opposite corners (saddle points - ambiguous)
            5:  [(left, top), (right, bottom)],   # corners 0,2
            10: [(top, right), (bottom, left)],   # corners 1,3
            
            # Three corners (one missing)
            7:  [(left, bottom)],        # missing corner 3
            11: [(bottom, right)],       # missing corner 2
            13: [(right, top)],          # missing corner 1
            14: [(top, left)],           # missing corner 0
        }
        
        return case_table.get(case, [])
    
    def _trace_segments(
        self,
        segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
        tolerance: float
    ) -> List[List[Tuple[float, float]]]:
        """
        Connect segments into closed contours.
        """
        if not segments:
            return []
        
        # Build adjacency: for each point, which segments touch it
        # Use rounded coordinates as keys for matching
        def point_key(p):
            return (round(p[0] / tolerance), round(p[1] / tolerance))
        
        # Map from point key to list of (segment_idx, which_end)
        # which_end: 0 = start, 1 = end
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
        contours = []
        
        for start_seg_idx in range(len(segments)):
            if start_seg_idx in used_segments:
                continue
            
            # Start a new contour
            contour = []
            seg_idx = start_seg_idx
            direction = 0  # 0 = forward (start to end), 1 = backward (end to start)
            
            max_steps = len(segments) * 2
            for _ in range(max_steps):
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
                        # If we arrived at this segment's start (end=0), go forward
                        # If we arrived at this segment's end (end=1), go backward
                        next_dir = 1 if cand_end == 1 else 0
                        break
                
                if next_seg is None:
                    break
                
                seg_idx = next_seg
                direction = next_dir
            
            if len(contour) >= 3:
                contours.append(contour)
        
        return contours
    
    def _polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula."""
        if len(points) < 3:
            return 0.0
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0


def chaikin_smooth(
    points: List[Tuple[float, float]],
    iterations: int = 2,
    boundary_rect: Optional[Tuple[float, float, float, float]] = None
) -> List[Tuple[float, float]]:
    """Chaikin's corner-cutting algorithm for smooth curves.
    
    If boundary_rect is provided (min_x, min_y, max_x, max_y), points on the
    boundary edges are kept fixed and segments along edges are not smoothed.
    """
    if len(points) < 3:
        return points
    
    # Remove duplicate endpoint if present
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    
    def is_on_boundary(p: Tuple[float, float]) -> bool:
        if boundary_rect is None:
            return False
        min_x, min_y, max_x, max_y = boundary_rect
        tol = 0.01
        return (abs(p[0] - min_x) < tol or abs(p[0] - max_x) < tol or
                abs(p[1] - min_y) < tol or abs(p[1] - max_y) < tol)
    
    def segment_on_boundary(p0: Tuple[float, float], p1: Tuple[float, float]) -> bool:
        """Check if segment lies along a boundary edge."""
        if boundary_rect is None:
            return False
        min_x, min_y, max_x, max_y = boundary_rect
        tol = 0.01
        # Both points on same edge
        return ((abs(p0[0] - min_x) < tol and abs(p1[0] - min_x) < tol) or
                (abs(p0[0] - max_x) < tol and abs(p1[0] - max_x) < tol) or
                (abs(p0[1] - min_y) < tol and abs(p1[1] - min_y) < tol) or
                (abs(p0[1] - max_y) < tol and abs(p1[1] - max_y) < tol))
    
    for _ in range(iterations):
        if len(points) < 3:
            break
        new_points = []
        n = len(points)
        for i in range(n):
            p0 = points[i]
            p1 = points[(i + 1) % n]
            
            p0_on_boundary = is_on_boundary(p0)
            p1_on_boundary = is_on_boundary(p1)
            
            # If segment is along boundary, keep p0 only (p1 added by next iteration)
            if segment_on_boundary(p0, p1):
                new_points.append(p0)
            # If p0 is on boundary but p1 is not, keep p0 fixed and add one subdivision point
            elif p0_on_boundary and not p1_on_boundary:
                new_points.append(p0)
                r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
                new_points.append(r)
            # If p1 is on boundary but p0 is not, add one subdivision point (p1 kept by next segment)
            elif p1_on_boundary and not p0_on_boundary:
                q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
                new_points.append(q)
            else:
                # Normal Chaikin subdivision
                q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
                r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
                new_points.extend([q, r])
        points = new_points
    
    return points
