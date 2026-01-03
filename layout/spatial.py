"""Spatial utilities for collision detection and geometry."""
from typing import List, Tuple, Set, Optional, Dict
from dataclasses import dataclass
import math


@dataclass
class Point:
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __hash__(self):
        return hash((self.x, self.y))


@dataclass 
class Rect:
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def overlaps(self, other: 'Rect', margin: int = 0) -> bool:
        """Check if two rectangles overlap with optional margin."""
        return not (
            self.x + self.width + margin <= other.x or
            other.x + other.width + margin <= self.x or
            self.y + self.height + margin <= other.y or
            other.y + other.height + margin <= self.y
        )
    
    def separation_vector(self, other: 'Rect') -> Tuple[float, float]:
        """Get vector to separate this rect from other (push self away)."""
        c1 = self.center
        c2 = other.center
        
        dx = c1.x - c2.x
        dy = c1.y - c2.y
        
        # Calculate overlap on each axis
        overlap_x = (self.width + other.width) / 2 - abs(dx)
        overlap_y = (self.height + other.height) / 2 - abs(dy)
        
        if overlap_x <= 0 or overlap_y <= 0:
            return (0, 0)  # No overlap
        
        # Push in direction of smallest overlap
        if overlap_x < overlap_y:
            return (overlap_x * (1 if dx > 0 else -1), 0)
        else:
            return (0, overlap_y * (1 if dy > 0 else -1))


class SpatialHash:
    """Spatial hash grid for fast collision detection."""
    
    def __init__(self, cell_size: int = 10):
        self.cell_size = cell_size
        self.cells: Dict[Tuple[int, int], Set[str]] = {}
    
    def _get_cells(self, rect: Rect) -> List[Tuple[int, int]]:
        """Get all cells that a rectangle occupies."""
        cells = []
        x1 = rect.x // self.cell_size
        y1 = rect.y // self.cell_size
        x2 = (rect.x + rect.width) // self.cell_size
        y2 = (rect.y + rect.height) // self.cell_size
        
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                cells.append((x, y))
        return cells
    
    def insert(self, id: str, rect: Rect) -> None:
        """Insert a rectangle into the spatial hash."""
        for cell in self._get_cells(rect):
            if cell not in self.cells:
                self.cells[cell] = set()
            self.cells[cell].add(id)
    
    def remove(self, id: str, rect: Rect) -> None:
        """Remove a rectangle from the spatial hash."""
        for cell in self._get_cells(rect):
            if cell in self.cells:
                self.cells[cell].discard(id)
    
    def query(self, rect: Rect) -> Set[str]:
        """Get all IDs that might intersect with the given rectangle."""
        result = set()
        for cell in self._get_cells(rect):
            if cell in self.cells:
                result.update(self.cells[cell])
        return result
    
    def clear(self) -> None:
        """Clear all entries."""
        self.cells.clear()


def delaunay_triangulation(points: List[Point]) -> List[Tuple[int, int]]:
    """
    Simple Delaunay triangulation using Bowyer-Watson algorithm.
    Returns list of edges as index pairs.
    """
    if len(points) < 2:
        return []
    
    if len(points) == 2:
        return [(0, 1)]
    
    # For small point sets, use simple approach
    # For production, would use scipy.spatial.Delaunay
    
    # Create super-triangle
    min_x = min(p.x for p in points) - 100
    max_x = max(p.x for p in points) + 100
    min_y = min(p.y for p in points) - 100
    max_y = max(p.y for p in points) + 100
    
    dx = max_x - min_x
    dy = max_y - min_y
    dmax = max(dx, dy) * 2
    
    # Super triangle vertices
    p1 = Point(min_x - dmax, min_y - dmax)
    p2 = Point(min_x + dmax * 2, min_y - dmax)
    p3 = Point(min_x + dmax / 2, max_y + dmax)
    
    all_points = [p1, p2, p3] + list(points)
    triangles = [(0, 1, 2)]  # Start with super triangle
    
    # Add each point
    for i, p in enumerate(points, start=3):
        bad_triangles = []
        
        for tri in triangles:
            if _point_in_circumcircle(p, all_points[tri[0]], all_points[tri[1]], all_points[tri[2]]):
                bad_triangles.append(tri)
        
        # Find boundary polygon
        polygon = []
        for tri in bad_triangles:
            for j in range(3):
                edge = (tri[j], tri[(j + 1) % 3])
                # Check if edge is shared
                shared = False
                for other in bad_triangles:
                    if other == tri:
                        continue
                    if edge[0] in other and edge[1] in other:
                        shared = True
                        break
                if not shared:
                    polygon.append(edge)
        
        # Remove bad triangles
        for tri in bad_triangles:
            triangles.remove(tri)
        
        # Create new triangles
        for edge in polygon:
            triangles.append((edge[0], edge[1], i))
    
    # Remove triangles connected to super triangle
    triangles = [t for t in triangles if all(v >= 3 for v in t)]
    
    # Convert to edges (adjust indices back)
    edges = set()
    for tri in triangles:
        for j in range(3):
            e = tuple(sorted([tri[j] - 3, tri[(j + 1) % 3] - 3]))
            edges.add(e)
    
    return list(edges)


def _point_in_circumcircle(p: Point, a: Point, b: Point, c: Point) -> bool:
    """Check if point p is inside circumcircle of triangle abc."""
    ax, ay = a.x - p.x, a.y - p.y
    bx, by = b.x - p.x, b.y - p.y
    cx, cy = c.x - p.x, c.y - p.y
    
    det = (
        (ax * ax + ay * ay) * (bx * cy - cx * by) -
        (bx * bx + by * by) * (ax * cy - cx * ay) +
        (cx * cx + cy * cy) * (ax * by - bx * ay)
    )
    
    # Check orientation
    orient = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
    
    if orient > 0:
        return det > 0
    return det < 0


def minimum_spanning_tree(points: List[Point], edges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Compute MST using Kruskal's algorithm.
    Returns list of edges in the MST.
    """
    if not edges:
        return []
    
    # Calculate edge weights
    weighted_edges = []
    for e in edges:
        dist = points[e[0]].distance_to(points[e[1]])
        weighted_edges.append((dist, e))
    
    weighted_edges.sort()
    
    # Union-Find
    parent = list(range(len(points)))
    rank = [0] * len(points)
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px == py:
            return False
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1
        return True
    
    mst = []
    for _, edge in weighted_edges:
        if union(edge[0], edge[1]):
            mst.append(edge)
            if len(mst) == len(points) - 1:
                break
    
    return mst


def line_intersects_rect(p1: Tuple[int, int], p2: Tuple[int, int], rect: Rect) -> bool:
    """Check if line segment intersects rectangle."""
    # Check if either endpoint is inside
    if (rect.x <= p1[0] < rect.x + rect.width and 
        rect.y <= p1[1] < rect.y + rect.height):
        return True
    if (rect.x <= p2[0] < rect.x + rect.width and 
        rect.y <= p2[1] < rect.y + rect.height):
        return True
    
    # Check line against each edge
    edges = [
        ((rect.x, rect.y), (rect.x + rect.width, rect.y)),
        ((rect.x + rect.width, rect.y), (rect.x + rect.width, rect.y + rect.height)),
        ((rect.x + rect.width, rect.y + rect.height), (rect.x, rect.y + rect.height)),
        ((rect.x, rect.y + rect.height), (rect.x, rect.y)),
    ]
    
    for e in edges:
        if _segments_intersect(p1, p2, e[0], e[1]):
            return True
    
    return False


def _segments_intersect(p1, p2, p3, p4) -> bool:
    """Check if line segments p1-p2 and p3-p4 intersect."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4) and 
            ccw(p1, p2, p3) != ccw(p1, p2, p4))






