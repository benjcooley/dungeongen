"""Shape definitions for the crosshatch pattern generator."""

import math
import skia
from typing import List, Protocol, Sequence, TypeAlias
from algorithms.types import Point
from algorithms.math import Matrix2D
from map.props.rotation import Rotation

# Forward declaration of Rectangle type
Rectangle: TypeAlias = 'Rectangle'

class Shape(Protocol):
    """Protocol defining the interface for shapes."""
    @property
    def inflate(self) -> float:
        """Get the inflation amount for this shape."""
        ...

    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape."""
        ...
        
    def contains_shape(self, other: 'Shape') -> bool:
        """Check if another shape is fully contained within this shape."""
        return shape_contains(self, other)
        
    def intersects(self, other: 'Shape') -> bool:
        """Check if this shape intersects with another shape."""
        return shape_intersects(self, other)
    
    @property
    def bounds(self) -> 'Rectangle':
        """Get the bounding rectangle that encompasses this shape."""
        ...
    
    def draw(self, canvas: 'skia.Canvas', paint: 'skia.Paint') -> None:
        """Draw this shape on a canvas with the given paint."""
        ...
    
    @property
    def path(self) -> 'skia.Path':
        """Get the cached Skia path for this shape."""
        ...
        
    def to_path(self) -> 'skia.Path':
        """Convert this shape to a Skia path (deprecated, use path property)."""
        return self.path
    
    def inflated(self, amount: float) -> 'Shape':
        """Return a new shape inflated by the given amount."""
        ...
    
    def translate(self, dx: float, dy: float) -> None:
        """Translate this shape by the given amounts in-place."""
        ...
    
    def rotate(self, rotation: 'Rotation') -> None:
        """Rotate this shape by the given 90-degree increment in-place."""
        ...

    def make_translated(self, dx: float, dy: float) -> 'Shape':
        """Return a new shape translated by the given amounts."""
        ...
    
    def make_rotated(self, rotation: 'Rotation') -> 'Shape':
        """Return a new shape rotated by the given 90-degree increment."""
        ...
    
    @property
    def is_valid(self) -> bool:
        """Check if this shape is valid and can be rendered."""
        ...
        
    def intersects(self, other: 'Shape') -> bool:
        """Check if this shape intersects with another shape.
        
        Args:
            other: Another shape to test intersection with
            
        Returns:
            True if the shapes intersect, False otherwise
        """
        ...

class ShapeGroup:
    """A group of shapes that can be combined to create complex shapes."""
    
    def __init__(self, includes: Sequence[Shape], excludes: Sequence[Shape]) -> None:
        self.includes = list(includes)
        self.excludes = list(excludes)
        self._bounds: Rectangle | None = None
        self._bounds_dirty = True
        self._inflate: float = 0.0

    @property
    def inflate(self) -> float:
        """Get the inflation amount for this shape group."""
        return self._inflate

    def add_include(self, shape: Shape) -> None:
        """Add a shape to the includes list."""
        self.includes.append(shape)
        self._bounds_dirty = True

    def remove_include(self, shape: Shape) -> None:
        """Remove a shape from the includes list."""
        if shape in self.includes:
            self.includes.remove(shape)
            self._bounds_dirty = True
            
    def remove_include_at(self, index: int) -> None:
        """Remove a shape from the includes list at the specified index."""
        if 0 <= index < len(self.includes):
            self.includes.pop(index)
            self._bounds_dirty = True

    def add_exclude(self, shape: Shape) -> None:
        """Add a shape to the excludes list."""
        self.excludes.append(shape)
        self._bounds_dirty = True

    def remove_exclude(self, shape: Shape) -> None:
        """Remove a shape from the excludes list."""
        if shape in self.excludes:
            self.excludes.remove(shape)
            self._bounds_dirty = True
            
    def remove_exclude_at(self, index: int) -> None:
        """Remove a shape from the excludes list at the specified index."""
        if 0 <= index < len(self.excludes):
            self.excludes.pop(index)
            self._bounds_dirty = True
    
    @classmethod
    def combine(cls, shapes: Sequence[Shape]) -> 'ShapeGroup':
        """Combine multiple shapes into a new ShapeGroup.
        
        Combines ShapeGroups by merging their includes/excludes lists.
        Other shapes are added to includes list.
        """
        includes: List[Shape] = []
        excludes: List[Shape] = []
        
        for shape in shapes:
            if isinstance(shape, ShapeGroup):
                includes.extend(shape.includes)
                excludes.extend(shape.excludes)
            else:
                includes.append(shape)
        
        return cls(includes=includes, excludes=excludes)
    
    @classmethod
    def half_circle(cls, cx: float, cy: float, radius: float, angle: float, inflate: float = 0) -> 'ShapeGroup':
        """Create a half circle as a ShapeGroup.
        
        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            radius: Circle radius
            angle: Angle in degrees (0, 90, 180, or 270) indicating which half to keep
                  0 = right half, 90 = top half, 180 = left half, 270 = bottom half
            inflate: Optional inflation amount
            
        Returns:
            A ShapeGroup representing a half circle
            
        Raises:
            ValueError: If angle is not 0, 90, 180, or 270
        """
        if angle not in (0, 90, 180, 270):
            raise ValueError("Angle must be 0, 90, 180, or 270 degrees")
            
        # Create the base circle
        circle = Circle(cx, cy, radius, inflate)
        
        # Calculate rectangle to exclude half the circle
        rect_size = (radius + inflate) * 2
        if angle == 0:  # Right half (exclude left)
            rect = Rectangle(cx - rect_size, cy - rect_size, rect_size, rect_size * 2)
        elif angle == 90:  # Top half (exclude bottom)
            rect = Rectangle(cx - rect_size, cy, rect_size * 2, rect_size)
        elif angle == 180:  # Left half (exclude right)
            rect = Rectangle(cx, cy - rect_size, rect_size, rect_size * 2)
        else:  # angle == 270, Bottom half (exclude top)
            rect = Rectangle(cx - rect_size, cy - rect_size, rect_size * 2, rect_size)
            
        return cls(includes=[circle], excludes=[rect])
    
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape group."""
        return (
            any(shape.contains(px, py) for shape in self.includes) and
            not any(shape.contains(px, py) for shape in self.excludes)
        )
    
    def __init__(self, includes: Sequence[Shape], excludes: Sequence[Shape]) -> None:
        self.includes = list(includes)
        self.excludes = list(excludes)
        self._bounds: Rectangle | None = None
        self._bounds_dirty = True
        self._cached_path: skia.Path | None = None
        self._inflate: float = 0.0
        
    @property
    def path(self) -> skia.Path:
        """Get the cached Skia path for this shape group."""
        if self._cached_path is None:
            if not self.includes:
                self._cached_path = skia.Path()
            else:
                # Start with the first included shape
                self._cached_path = self.includes[0].path
                
                # Union with remaining included shapes
                for shape in self.includes[1:]:
                    self._cached_path = skia.Op(self._cached_path, shape.path, skia.PathOp.kUnion_PathOp)
                    
                # Subtract excluded shapes
                for shape in self.excludes:
                    self._cached_path = skia.Op(self._cached_path, shape.path, skia.PathOp.kDifference_PathOp)
        return self._cached_path
        
    def to_path(self) -> skia.Path:
        """Convert this shape group to a Skia path (deprecated, use path property)."""
        return self.path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this shape group using Skia's path operations."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'ShapeGroup':
        """Return a new shape group with included shapes inflated.
        
        Only inflates the included shapes, excludes remain unchanged.
        This matches the expected behavior where excluded areas should
        not grow when inflating the overall shape.
        """
        new_group = ShapeGroup(
            includes=[s.inflated(amount) for s in self.includes],
            excludes=list(self.excludes)  # Keep excludes unchanged
        )
        new_group._inflate = self._inflate + amount
        return new_group

    def rotate(self, rotation: 'Rotation') -> 'ShapeGroup':
        """Rotate all shapes in this group by 90-degree increment in-place."""
        for shape in self.includes:
            shape.rotate(rotation)
        for shape in self.excludes:
            shape.rotate(rotation)
        self._bounds_dirty = True
        return self
    
    def translate(self, dx: float, dy: float) -> 'ShapeGroup':
        """Translate all shapes in this group by the given amounts in-place."""
        for shape in self.includes:
            shape.translate(dx, dy)
        for shape in self.excludes:
            shape.translate(dx, dy)
        self._bounds_dirty = True
        return self
    
    def make_rotated(self, rotation: 'Rotation') -> 'ShapeGroup':
        """Return a new shape group with all shapes rotated by 90-degree increment."""
        return ShapeGroup(
            includes=[s.make_rotated(rotation) for s in self.includes],
            excludes=[s.make_rotated(rotation) for s in self.excludes]
        )
        
    def make_translated(self, dx: float, dy: float) -> 'ShapeGroup':
        """Return a new shape group with all shapes translated by the given amounts."""
        return ShapeGroup(
            includes=[s.make_translated(dx, dy) for s in self.includes],
            excludes=[s.make_translated(dx, dy) for s in self.excludes]
        )
    
    def _recalculate_bounds(self) -> None:
        """Calculate bounds using Skia path operations to handle excludes."""
        if not self.is_valid:
            return
            
        # Get bounds from final path which accounts for excludes
        path_bounds = self.path.getBounds()
        self._bounds = Rectangle(
            path_bounds.left(),
            path_bounds.top(),
            path_bounds.width(),
            path_bounds.height()
        )
        self._bounds_dirty = False

    @property
    def is_valid(self) -> bool:
        """Check if this shape group is valid (has at least one included shape)."""
        return len(self.includes) > 0
        
    def intersects(self, other: 'Shape') -> bool:
        """Check if this shape group intersects with another shape."""
        from algorithms.intersections import shape_group_intersect
        return shape_group_intersect(self, other)
        
    def intersects(self, other: 'Shape') -> bool:
        """Test if this shape group intersects with another shape."""
        # Get bounds once to avoid recursion
        my_bounds = self.bounds
        other_bounds = other.bounds
        
        # Quick bounds check
        if not (my_bounds.x < other_bounds.x + other_bounds.width and
                my_bounds.x + my_bounds.width > other_bounds.x and
                my_bounds.y < other_bounds.y + other_bounds.height and
                my_bounds.y + my_bounds.height > other_bounds.y):
            return False
            
        # If bounds intersect, do detailed shape intersection test
        return shape_intersects(self, other)
    
    @property
    def bounds(self) -> Rectangle:
        """Get the current bounding rectangle, recalculating if needed."""
        if not self.is_valid:
            return Rectangle(0, 0, 0, 0)
        if self._bounds_dirty or self._bounds is None:
            self._recalculate_bounds()
        return self._bounds

class Rectangle:
    """A rectangle that can be inflated to create a rounded rectangle effect.
    
    When inflated, the rectangle's corners become rounded with radius equal to
    the inflation amount, effectively creating a rounded rectangle shape.
    """
    
    @property
    def is_valid(self) -> bool:
        """Check if this rectangle is valid (has positive width and height)."""
        return self.width > 0 and self.height > 0
    
    @property
    def bounds(self) -> 'Rectangle':
        """Return this rectangle as bounds."""
        if not self.is_valid:
            return Rectangle(0, 0, 0, 0)
        return Rectangle(self._inflated_x, self._inflated_y, self._inflated_width, self._inflated_height)
    
    def __init__(self, x: float, y: float, width: float, height: float, inflate: float = 0) -> None:
        self.x = x  # Original x
        self.y = y  # Original y
        self.width = width  # Original width
        self.height = height  # Original height
        self._inflate = inflate
        self._inflated_x = x - inflate
        self._inflated_y = y - inflate
        self._inflated_width = width + 2 * inflate
        self._inflated_height = height + 2 * inflate

    @property
    def inflate(self) -> float:
        """Get the inflation amount for this rectangle."""
        return self._inflate

    @property
    def inflated(self) -> 'Rectangle':
        """Return a new Rectangle instance with the inflated dimensions.
        
        Note: The inflated rectangle effectively becomes a rounded rectangle,
        where the corner radius equals the inflation amount. This is because
        the contains() method uses a distance check that creates rounded corners.
        """
        return Rectangle(
            self._inflated_x,
            self._inflated_y,
            self._inflated_width,
            self._inflated_height
        )

    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this rectangle.
        
        For inflated rectangles, this creates rounded corners with radius equal to
        the inflation amount. Points must be within the rectangle and not in the
        corner regions beyond the rounded corners.
        """
        # First check if point is within the basic rectangle bounds
        if not (self._inflated_x <= px <= self._inflated_x + self._inflated_width and
                self._inflated_y <= py <= self._inflated_y + self._inflated_height):
            return False
            
        # If not inflated, we're done
        if self._inflate <= 0:
            return True
            
        # For inflated rectangles, check corner regions
        dx = max(0, abs(px - (self._inflated_x + self._inflated_width / 2)) - (self._inflated_width / 2 - self._inflate))
        dy = max(0, abs(py - (self._inflated_y + self._inflated_height / 2)) - (self._inflated_height / 2 - self._inflate))
        
        # Point must be within the rounded corner radius
        return math.sqrt(dx * dx + dy * dy) <= self._inflate
        
    def contains_shape(self, other: 'Shape') -> bool:
        """Check if this rectangle fully contains another shape."""
        from algorithms.shapes import Circle
        
        if isinstance(other, Rectangle):
            return rect_rect_contains(self, other)
        elif isinstance(other, Circle):
            return rect_circle_contains(self, other)
        else:
            # For other shapes, use Skia path operations
            result = skia.Op(self.path, other.path, skia.PathOp.kDifference_PathOp)
            return result.isEmpty()
    
    def __init__(self, x: float, y: float, width: float, height: float, inflate: float = 0) -> None:
        self.x = x  # Original x
        self.y = y  # Original y
        self.width = width  # Original width
        self.height = height  # Original height
        self._inflate = inflate
        self._inflated_x = x - inflate
        self._inflated_y = y - inflate
        self._inflated_width = width + 2 * inflate
        self._inflated_height = height + 2 * inflate
        self._cached_path: skia.Path | None = None
        
    @property
    def path(self) -> skia.Path:
        """Get the cached Skia path for this rectangle."""
        if self._cached_path is None:
            self._cached_path = skia.Path()
            if self._inflate > 0:
                self._cached_path.addRRect(
                    skia.RRect.MakeRectXY(
                        skia.Rect.MakeXYWH(
                            self._inflated_x,
                            self._inflated_y,
                            self._inflated_width,
                            self._inflated_height
                        ),
                        self._inflate,  # x radius
                        self._inflate   # y radius
                    )
                )
            else:
                self._cached_path.addRect(
                    skia.Rect.MakeXYWH(
                        self._inflated_x,
                        self._inflated_y,
                        self._inflated_width,
                        self._inflated_height
                    )
                )
        return self._cached_path
        
    def to_path(self) -> skia.Path:
        """Convert this rectangle to a Skia path (deprecated, use path property)."""
        return self.path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this rectangle on a canvas."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'Rectangle':
        """Return a new rectangle inflated by the given amount."""
        return Rectangle(self.x, self.y, self.width, self.height, self._inflate + amount)
    
    def translate(self, dx: float, dy: float) -> 'Rectangle':
        """Translate this rectangle by the given amounts in-place."""
        self.x += dx
        self.y += dy
        self._inflated_x += dx
        self._inflated_y += dy
        return self
    
    def make_translated(self, dx: float, dy: float) -> 'Rectangle':
        """Return a new rectangle translated by the given amounts."""
        return Rectangle(self.x + dx, self.y + dy, self.width, self.height, self._inflate)
    
    def rotate(self, rotation: 'Rotation') -> 'Rectangle':
        """Rotate this rectangle by the given 90-degree increment in-place."""
        # For 90/270 degree rotations, swap width and height first
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            self.width, self.height = self.height, self.width
            
        # Calculate center point
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_center_x = center_x * math.cos(angle) - center_y * math.sin(angle)
        new_center_y = center_x * math.sin(angle) + center_y * math.cos(angle)
        
        # Calculate new top-left position relative to rotated center
        self.x = new_center_x - self.width / 2
        self.y = new_center_y - self.height / 2
        
        # Update inflated values
        self._inflated_x = self.x - self._inflate
        self._inflated_y = self.y - self._inflate
        self._inflated_width = self.width + 2 * self._inflate
        self._inflated_height = self.height + 2 * self._inflate
        
        # Clear cached path since shape changed
        self._cached_path = None
        return self
    
    def make_rotated(self, rotation: 'Rotation') -> 'Rectangle':
        """Return a new rectangle rotated by the given 90-degree increment."""
        # For 90/270 degree rotations, swap width and height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            width, height = self.height, self.width
        else:
            width, height = self.width, self.height

        # Calculate center point
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_center_x = center_x * math.cos(angle) - center_y * math.sin(angle)
        new_center_y = center_y * math.cos(angle) + center_x * math.sin(angle)
        
        # Calculate new top-left position relative to rotated center
        return Rectangle(
            new_center_x - width / 2,
            new_center_y - height / 2,
            width,
            height,
            self._inflate
        )
        
    def adjust(self, left: float, top: float, right: float, bottom: float) -> 'Rectangle':
        """Return a new rectangle with edges adjusted by the given amounts.
        
        Args:
            left: Amount to adjust left edge (negative moves left)
            top: Amount to adjust top edge (negative moves up)
            right: Amount to adjust right edge (positive expands)
            bottom: Amount to adjust bottom edge (positive expands)
            
        Returns:
            A new Rectangle with adjusted edges
        """
        return Rectangle(
            self.x + left,
            self.y + top,
            self.width + (right - left),
            self.height + (bottom - top),
            self._inflate
        )
        
    @property
    def left(self) -> float:
        """Get the left edge x-coordinate."""
        return self._inflated_x
        
    @property 
    def top(self) -> float:
        """Get the top edge y-coordinate."""
        return self._inflated_y
        
    @property
    def right(self) -> float:
        """Get the right edge x-coordinate."""
        return self._inflated_x + self._inflated_width
        
    @property
    def bottom(self) -> float:
        """Get the bottom edge y-coordinate."""
        return self._inflated_y + self._inflated_height

    @property
    def p1(self) -> Point:
        """Get the top-left point of the rectangle."""
        return (self._inflated_x, self._inflated_y)
        
    @property
    def p2(self) -> Point:
        """Get the bottom-right point of the rectangle."""
        return (self._inflated_x + self._inflated_width, 
                self._inflated_y + self._inflated_height)

    @property
    def center(self) -> tuple[float, float]:
        """Get the center point of this rectangle.
        
        Returns:
            Tuple of (center_x, center_y) coordinates
        """
        return (
            self.x + self.width / 2,
            self.y + self.height / 2
        )
        
    def _bounds_intersect(self, other: 'Rectangle') -> bool:
        """Test if this rectangle's bounds intersect another rectangle."""
        return rect_rect_intersect(self, other)
        
    def intersects(self, other: 'Shape') -> bool:
        """Test if this rectangle intersects with another shape."""
        return shape_intersects(self, other)
    
    @classmethod
    def centered_grid(cls, grid_width: float, grid_height: float) -> 'Rectangle':
        """Create a rectangle centered at (0,0) with dimensions in grid units.
        
        Args:
            grid_width: Width in grid units
            grid_height: Height in grid units
            
        Returns:
            A new Rectangle centered at origin with given grid dimensions
        """
        from constants import CELL_SIZE
        width = grid_width * CELL_SIZE
        height = grid_height * CELL_SIZE
        return cls(-width/2, -height/2, width, height)

    @classmethod
    def rotated_rect(cls, center_x: float, center_y: float, width: float, height: float, rotation: 'Rotation', inflate: float = 0) -> 'Rectangle':
        """Create a rectangle with dimensions swapped based on rotation.
        
        Args:
            center_x: X center of rectangle
            center_y: Y center of rectangle
            width: Width in drawing units
            height: Height in drawing units
            rotation: Rotation angle in 90° increments
            inflate: Optional inflation amount
            
        Returns:
            A new Rectangle with width/height swapped if rotation is 90° or 270°
        """
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            return cls(center_x - height / 2, center_y - width / 2, height, width, inflate)
        return cls(center_x - width / 2, center_y - height / 2, width, height, inflate)

class Circle:
    def __init__(self, cx: float, cy: float, radius: float, inflate: float = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius  # Original radius
        self._inflate = inflate
        self._inflated_radius = radius + inflate

    @property
    def inflate(self) -> float:
        """Get the inflation amount for this circle."""
        return self._inflate

    @property
    def inflated(self) -> 'Circle':
        """Return a new Circle instance with the inflated radius."""
        return Circle(self.cx, self.cy, self._inflated_radius)

    def contains(self, px: float, py: float) -> bool:
        return math.sqrt((px - self.cx)**2 + (py - self.cy)**2) <= self._inflated_radius
        
    def contains_shape(self, other: 'Shape') -> bool:
        """Check if this circle fully contains another shape."""
        return shape_contains(self, other)
    
    @property
    def is_valid(self) -> bool:
        """Check if this circle is valid (has positive radius)."""
        return self.radius > 0
    
    @property
    def bounds(self) -> Rectangle:
        """Get the bounding rectangle for this circle."""
        if not self.is_valid:
            return Rectangle(0, 0, 0, 0)
        return Rectangle(
            self.cx - self._inflated_radius,
            self.cy - self._inflated_radius,
            self._inflated_radius * 2,
            self._inflated_radius * 2
        )
    
    def __init__(self, cx: float, cy: float, radius: float, inflate: float = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius  # Original radius
        self._inflate = inflate
        self._inflated_radius = radius + inflate
        self._cached_path: skia.Path | None = None
        
    @property
    def path(self) -> skia.Path:
        """Get the cached Skia path for this circle."""
        if self._cached_path is None:
            self._cached_path = skia.Path()
            self._cached_path.addCircle(self.cx, self.cy, self._inflated_radius)
        return self._cached_path
        
    def to_path(self) -> skia.Path:
        """Convert this circle to a Skia path (deprecated, use path property)."""
        return self.path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this circle on a canvas."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'Circle':
        """Return a new circle inflated by the given amount."""
        return Circle(self.cx, self.cy, self.radius, self._inflate + amount)
        
    def translate(self, dx: float, dy: float) -> 'Circle':
        """Translate this circle by the given amounts in-place."""
        self.cx += dx
        self.cy += dy
        self._bounds_dirty = True
        return self
    
    def make_translated(self, dx: float, dy: float) -> 'Circle':
        """Return a new circle translated by the given amounts."""
        return Circle(self.cx + dx, self.cy + dy, self.radius, self._inflate)
    
    def rotate(self, rotation: 'Rotation') -> 'Circle':
        """Rotate this circle by the given 90-degree increment in-place."""
        # Skip rotation if center is at origin
        if abs(self.cx) < 1e-6 and abs(self.cy) < 1e-6:
            return self
            
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_cx = self.cx * math.cos(angle) - self.cy * math.sin(angle)
        new_cy = self.cy * math.cos(angle) + self.cx * math.sin(angle)
        
        self.cx = new_cx
        self.cy = new_cy
        self._cached_path = None
        return self
    
    def make_rotated(self, rotation: 'Rotation') -> 'Circle':
        """Return a new circle rotated by the given 90-degree increment."""
        # Skip rotation if center is at origin
        if abs(self.cx) < 1e-6 and abs(self.cy) < 1e-6:
            return Circle(0, 0, self.radius, self._inflate)
            
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_cx = self.cx * math.cos(angle) - self.cy * math.sin(angle)
        new_cy = self.cy * math.cos(angle) + self.cx * math.sin(angle)
        return Circle(new_cx, new_cy, self.radius, self._inflate)
        
    def intersects(self, other: Shape) -> bool:
        """Test if this circle intersects with another shape."""
        if isinstance(other, Rectangle):
            return rect_circle_intersect(other, self)
        elif isinstance(other, Circle):
            return circle_circle_intersect(self, other)
        return shape_intersects(self, other)


def shape_intersects(shape1: 'Shape', shape2: 'Shape') -> bool:
    """Test if two shapes intersect.
    
    Uses Skia path operations for complex shapes (ShapeGroups or inflated shapes),
    and simpler geometric tests for basic shapes.
    
    Args:
        shape1: First shape to test
        shape2: Second shape to test
        
    Returns:
        True if shapes intersect, False otherwise
    """
        
    # Use Skia for ShapeGroups or inflated shapes
    if (isinstance(shape1, ShapeGroup) or isinstance(shape2, ShapeGroup) or
        getattr(shape1, '_inflate', 0) != 0 or getattr(shape2, '_inflate', 0) != 0):
        result = skia.Op(shape1.path, shape2.path, skia.PathOp.kIntersect_PathOp)
        return not result.isEmpty()
        
    # Use geometric tests for basic shapes
    if isinstance(shape1, Rectangle):
        if isinstance(shape2, Rectangle):
            return rect_rect_intersect(shape1, shape2)
        elif isinstance(shape2, Circle):
            return rect_circle_intersect(shape1, shape2)
    elif isinstance(shape1, Circle):
        if isinstance(shape2, Circle):
            return circle_circle_intersect(shape1, shape2)
        elif isinstance(shape2, Rectangle):
            return rect_circle_intersect(shape2, shape1)
            
    # Fall back to Skia for unknown shape combinations
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

def rect_circle_contains(rect: 'Rectangle', circle: 'Circle') -> bool:
    """Test if rectangle fully contains circle."""
    # Circle must be inside rectangle bounds with radius margin
    return (circle.cx - circle.radius >= rect.x and
            circle.cx + circle.radius <= rect.x + rect.width and
            circle.cy - circle.radius >= rect.y and
            circle.cy + circle.radius <= rect.y + rect.height)


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
    if not group.intersects(other.bounds):
        return False
        
    # Must intersect at least one include shape
    if not any(shape.intersects(other) for shape in group.includes):
        return False
        
    # If any exclude fully contains the shape, no intersection
    if any(shape.contains_shape(other) for shape in group.excludes):
        return False
        
    return True
