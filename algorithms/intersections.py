"""Shape intersection testing functions."""

from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from algorithms.shapes import Rectangle, Circle, Shape, ShapeGroup

def rect_rect_intersect(rect1: 'Rectangle', rect2: 'Rectangle') -> bool:
    """Test intersection between two rectangles."""
    return (rect1.x < rect2.x + rect2.width and
            rect1.x + rect1.width > rect2.x and
            rect1.y < rect2.y + rect2.height and
            rect1.y + rect1.height > rect2.y)

def circle_circle_intersect(circle1: 'Circle', circle2: 'Circle') -> bool:
    """Test intersection between two circles."""
    dx = circle1.cx - circle2.cx
    dy = circle1.cy - circle2.cy
    radii_sum = circle1.radius + circle2.radius
    return (dx * dx + dy * dy) <= (radii_sum * radii_sum)

def rect_circle_intersect(rect: 'Rectangle', circle: 'Circle') -> bool:
    """Test intersection between a rectangle and circle."""
    # Find closest point on rectangle to circle center
    closest_x = max(rect.x, min(circle.cx, rect.x + rect.width))
    closest_y = max(rect.y, min(circle.cy, rect.y + rect.height))
    
    # Compare distance from closest point to circle center
    dx = circle.cx - closest_x
    dy = circle.cy - closest_y
    return (dx * dx + dy * dy) <= (circle.radius * circle.radius)

def shape_group_intersect(group: 'ShapeGroup', other: 'Shape') -> bool:
    """Test intersection between a shape group and another shape."""
    # Quick rejection using bounds
    if not group._bounds_intersect(other.bounds):
        return False
        
    # Check if any included shape intersects
    for shape in group.includes:
        if shape.intersects(other):
            # Check if any excluded shape fully contains the other shape
            for exclude in group.excludes:
                if exclude.contains(other):
                    return False
            return True
            
    return False
