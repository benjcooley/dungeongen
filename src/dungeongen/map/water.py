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
    boundary: List[Tuple[float, float]]  # Polygon points in map coordinates
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
        # Scale coordinates - these work in map coordinates (pixels)
        # Divide by ~100 to get reasonable blob sizes
        scale = 0.01
        base = self.noise.noise2(x * scale * 0.6, y * scale * 0.6)
        shape = self.noise2.noise2(x * scale * 1.5, y * scale * 1.5)
        detail = self.noise3.noise2(x * scale * 3.0, y * scale * 3.0)
        return base * 0.6 + shape * 0.3 + detail * 0.1
    
    def generate_water_regions(
        self,
        bounds: Tuple[float, float, float, float],
        threshold: float = 0.1,
        resolution: float = 10.0,  # Sample spacing in map units
        floor_mask: Optional[Callable[[float, float], bool]] = None,
        min_area: float = 500.0,  # Minimum area in map units squared
        smooth: bool = True
    ) -> List[WaterRegion]:
        """
        Generate water regions within bounds.
        
        Args:
            bounds: (min_x, min_y, max_x, max_y) in map coordinates
            threshold: Noise threshold for water
            resolution: Sample spacing
            floor_mask: Optional function(x, y) -> bool, True if valid floor
            min_area: Minimum polygon area to keep
            smooth: Whether to apply Chaikin smoothing
        """
        min_x, min_y, max_x, max_y = bounds
        
        # Sample grid dimensions
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
        
        # Filter and create regions
        regions = []
        for contour in contours:
            if len(contour) < 3:
                continue
            
            area = self._polygon_area(contour)
            if area < min_area:
                continue
            
            if smooth:
                contour = chaikin_smooth(contour, iterations=2)
            
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
        """Marching squares with proper contour tracing."""
        
        edge_crossings: Dict[Tuple[int, int, int], Tuple[float, float]] = {}
        
        for iy in range(ny - 1):
            for ix in range(nx - 1):
                v00 = grid.get((ix, iy), -1)
                v10 = grid.get((ix+1, iy), -1)
                v11 = grid.get((ix+1, iy+1), -1)
                v01 = grid.get((ix, iy+1), -1)
                
                case = 0
                if v00 >= threshold: case |= 1
                if v10 >= threshold: case |= 2
                if v11 >= threshold: case |= 4
                if v01 >= threshold: case |= 8
                
                if case == 0 or case == 15:
                    continue
                
                x0 = origin_x + ix * resolution
                y0 = origin_y + iy * resolution
                x1 = x0 + resolution
                y1 = y0 + resolution
                
                def lerp(va, vb, pa, pb):
                    if abs(vb - va) < 1e-10:
                        return (pa + pb) / 2
                    t = (threshold - va) / (vb - va)
                    return pa + t * (pb - pa)
                
                if (v00 >= threshold) != (v10 >= threshold):
                    edge_crossings[(ix, iy, 0)] = (lerp(v00, v10, x0, x1), y0)
                
                if (v10 >= threshold) != (v11 >= threshold):
                    edge_crossings[(ix, iy, 1)] = (x1, lerp(v10, v11, y0, y1))
                
                if (v01 >= threshold) != (v11 >= threshold):
                    edge_crossings[(ix, iy, 2)] = (lerp(v01, v11, x0, x1), y1)
                
                if (v00 >= threshold) != (v01 >= threshold):
                    edge_crossings[(ix, iy, 3)] = (x0, lerp(v00, v01, y0, y1))
        
        # Trace contours
        contours = []
        used_edges: Set[Tuple[int, int, int]] = set()
        
        def get_connected_edge(ix, iy, entry_edge) -> Optional[int]:
            v00 = grid.get((ix, iy), -1)
            v10 = grid.get((ix+1, iy), -1)
            v11 = grid.get((ix+1, iy+1), -1)
            v01 = grid.get((ix, iy+1), -1)
            
            case = 0
            if v00 >= threshold: case |= 1
            if v10 >= threshold: case |= 2
            if v11 >= threshold: case |= 4
            if v01 >= threshold: case |= 8
            
            connections = {
                1: {3: 0, 0: 3},
                2: {0: 1, 1: 0},
                3: {3: 1, 1: 3},
                4: {1: 2, 2: 1},
                5: {3: 0, 0: 3, 1: 2, 2: 1},
                6: {0: 2, 2: 0},
                7: {3: 2, 2: 3},
                8: {2: 3, 3: 2},
                9: {2: 0, 0: 2},
                10: {0: 1, 1: 0, 2: 3, 3: 2},
                11: {2: 1, 1: 2},
                12: {1: 3, 3: 1},
                13: {1: 0, 0: 1},
                14: {0: 3, 3: 0},
            }
            
            if case in connections and entry_edge in connections[case]:
                return connections[case][entry_edge]
            return None
        
        def get_adjacent_cell(ix, iy, edge) -> Optional[Tuple[int, int, int]]:
            if edge == 0:
                return (ix, iy - 1, 2) if iy > 0 else None
            elif edge == 1:
                return (ix + 1, iy, 3) if ix < nx - 2 else None
            elif edge == 2:
                return (ix, iy + 1, 0) if iy < ny - 2 else None
            elif edge == 3:
                return (ix - 1, iy, 1) if ix > 0 else None
            return None
        
        for start_key in edge_crossings:
            if start_key in used_edges:
                continue
            
            contour = []
            current = start_key
            max_steps = len(edge_crossings) * 2
            steps = 0
            
            while current and steps < max_steps:
                steps += 1
                ix, iy, edge = current
                
                if current in used_edges:
                    break
                
                if current in edge_crossings:
                    contour.append(edge_crossings[current])
                    used_edges.add(current)
                else:
                    break
                
                exit_edge = get_connected_edge(ix, iy, edge)
                if exit_edge is None:
                    break
                
                adjacent = get_adjacent_cell(ix, iy, exit_edge)
                if adjacent is None:
                    break
                
                current = adjacent
            
            if len(contour) >= 3:
                contours.append(contour)
        
        return contours
    
    def _polygon_area(self, points: List[Tuple[float, float]]) -> float:
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
    iterations: int = 2
) -> List[Tuple[float, float]]:
    """Chaikin's corner-cutting algorithm for smooth curves."""
    if len(points) < 3:
        return points
    
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    
    for _ in range(iterations):
        if len(points) < 3:
            break
        new_points = []
        n = len(points)
        for i in range(n):
            p0 = points[i]
            p1 = points[(i + 1) % n]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.extend([q, r])
        points = new_points
    
    return points

