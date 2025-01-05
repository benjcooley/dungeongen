"""Shape intersection testing functions."""

from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from algorithms.shapes import Rectangle, Circle, Shape, ShapeGroup

def shape_intersects(shape1: 'Shape', shape2: 'Shape') -> bool:
    """Test if two shapes intersect using Skia path operations.
    
    Args:
        shape1: First shape to test
        shape2: Second shape to test
        
    Returns:
        True if shapes intersect, False otherwise
    """
    # Quick bounds check first
    if not shape1._bounds_intersect(shape2.bounds):
        return False
        
    # Use Skia path intersection
    result = skia.Op(shape1.path, shape2.path, skia.PathOp.kIntersect_PathOp)
    return not result.isEmpty()

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

def shape_contains(shape1: 'Shape', shape2: 'Shape') -> bool:
    """Test if shape1 fully contains shape2.
    
    Args:
        shape1: Container shape
        shape2: Shape to test if contained
        
    Returns:
        True if shape2 is fully contained within shape1
        
    Raises:
        TypeError: If shape combination is not supported
    """
    # Handle ShapeGroup specially
    if isinstance(shape1, ShapeGroup):
        return shape_group_contains(shape1, shape2)
    elif isinstance(shape2, ShapeGroup):
        # A non-group shape can't contain a group
        return False
        
    # Test rectangle combinations
    if isinstance(shape1, Rectangle):
        if isinstance(shape2, Rectangle):
            return rect_rect_contains(shape1, shape2)
        elif isinstance(shape2, Circle):
            return rect_circle_contains(shape1, shape2)
            
    # Test circle combinations        
    elif isinstance(shape1, Circle):
        if isinstance(shape2, Circle):
            return circle_circle_contains(shape1, shape2)
        elif isinstance(shape2, Rectangle):
            return circle_rect_contains(shape1, shape2)
            
    raise TypeError(f"Contains test not implemented between {type(shape1)} and {type(shape2)}")

def rect_rect_contains(rect1: 'Rectangle', rect2: 'Rectangle') -> bool:
    """Test if rect1 fully contains rect2."""
    return (rect2.x >= rect1.x and
            rect2.x + rect2.width <= rect1.x + rect1.width and
            rect2.y >= rect1.y and
            rect2.y + rect2.height <= rect1.y + rect1.height)

def circle_circle_contains(circle1: 'Circle', circle2: 'Circle') -> bool:
    """Test if circle1 fully contains circle2."""
    dx = circle1.cx - circle2.cx
    dy = circle1.cy - circle2.cy
    dist = math.sqrt(dx * dx + dy * dy)
    return dist + circle2.radius <= circle1.radius

def rect_circle_contains(rect: 'Rectangle', circle: 'Circle') -> bool:
    """Test if rectangle fully contains circle."""
    # Circle must be inside rectangle bounds with radius margin
    return (circle.cx - circle.radius >= rect.x and
            circle.cx + circle.radius <= rect.x + rect.width and
            circle.cy - circle.radius >= rect.y and
            circle.cy + circle.radius <= rect.y + rect.height)

def circle_rect_contains(circle: 'Circle', rect: 'Rectangle') -> bool:
    """Test if circle fully contains rectangle."""
    # Check all four corners of rectangle
    corners = [
        (rect.x, rect.y),
        (rect.x + rect.width, rect.y),
        (rect.x, rect.y + rect.height),
        (rect.x + rect.width, rect.y + rect.height)
    ]
    return all(
        math.sqrt((x - circle.cx)**2 + (y - circle.cy)**2) <= circle.radius
        for x, y in corners
    )

def shape_group_contains(group: 'ShapeGroup', other: 'Shape') -> bool:
    """Test if a shape group fully contains another shape.
    
    A shape is contained if:
    1. It's fully contained by at least one include shape
    2. It doesn't intersect any exclude shapes
    """
    # Must be contained by at least one include shape
    if not any(shape.contains_shape(other) for shape in group.includes):
        return False
        
    # Must not intersect any exclude shapes at all
    if any(shape.intersects(other) for shape in group.excludes):
        return False
        
    return True

def shape_group_intersect(group: 'ShapeGroup', other: 'Shape') -> bool:
    """Test intersection between a shape group and another shape.
    
    A shape intersects if:
    1. It intersects at least one include shape
    2. Has some portion not fully contained by any exclude shape
    """
    # Quick rejection using bounds
    if not group._bounds_intersect(other.bounds):
        return False
        
    # Must intersect at least one include shape
    if not any(shape.intersects(other) for shape in group.includes):
        return False
        
    # If any exclude fully contains the shape, no intersection
    if any(shape.contains_shape(other) for shape in group.excludes):
        return False
        
    return True
