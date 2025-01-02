"""Line intersection utilities."""

from typing import Tuple
from algorithms.types import Point, Line

def intersect_lines(line1: Line, line2: Line) -> Tuple[Point, float] | None:
    """Check if lines intersect and return intersection point and t value.
    
    Args:
        line1: First line as tuple of start and end points
        line2: Second line as tuple of start and end points
        
    Returns:
        Tuple of intersection point and t parameter value, or None if no intersection
    """
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    dx1, dy1 = x2 - x1, y2 - y1
    dx2, dy2 = x4 - x3, y4 - y3

    determinant = dx1 * dy2 - dy1 * dx2
    if determinant == 0:
        return None  # Parallel lines

    t2 = ((dy1 * (x3 - x1)) - (dx1 * (y3 - y1))) / determinant
    t1 = ((x3 - x1) + dx2 * t2) / dx1 if abs(dx1) > abs(dy1) else ((y3 - y1) + dy2 * t2) / dy1

    if 0 <= t1 <= 1 and 0 <= t2 <= 1:
        intersection_x = x1 + t1 * dx1
        intersection_y = y1 + t1 * dy1
        return ((intersection_x, intersection_y), t1)

    return None
