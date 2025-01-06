"""Shape definitions for the crosshatch pattern generator."""

import math
import skia
from typing import List, Protocol, Sequence, TypeAlias
from algorithms.types import Point
from algorithms.math import Matrix2D
from map.props.rotation import Rotation
from algorithms.intersections import shape_intersects, shape_group_intersect

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
        from algorithms.intersections import shape_contains
        return shape_contains(self, other)
        
    def intersects(self, other: 'Shape') -> bool:
        """Check if this shape intersects with another shape."""
        from algorithms.intersections import shape_intersects
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

    def rotate(self, rotation: 'Rotation') -> None:
        """Rotate all shapes in this group by 90-degree increment in-place."""
        for shape in self.includes:
            shape.rotate(rotation)
        for shape in self.excludes:
            shape.rotate(rotation)
        self._bounds_dirty = True
    
    def translate(self, dx: float, dy: float) -> None:
        """Translate all shapes in this group by the given amounts in-place."""
        for shape in self.includes:
            shape.translate(dx, dy)
        for shape in self.excludes:
            shape.translate(dx, dy)
        self._bounds_dirty = True
    
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
        
    def _bounds_intersect(self, other: Rectangle) -> bool:
        """Test if this shape group's bounds intersect a rectangle."""
        bounds = self.bounds
        return (bounds.x < other.x + other.width and
                bounds.x + bounds.width > other.x and
                bounds.y < other.y + other.height and
                bounds.y + bounds.height > other.y)
    
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
        from algorithms.intersections import rect_rect_contains, rect_circle_contains
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
    
    def translate(self, dx: float, dy: float) -> None:
        """Translate this rectangle by the given amounts in-place."""
        self.x += dx
        self.y += dy
        self._inflated_x += dx
        self._inflated_y += dy
    
    def make_translated(self, dx: float, dy: float) -> 'Rectangle':
        """Return a new rectangle translated by the given amounts."""
        return Rectangle(self.x + dx, self.y + dy, self.width, self.height, self._inflate)
    
    def rotate(self, rotation: 'Rotation') -> None:
        """Rotate this rectangle by the given 90-degree increment in-place."""
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
        
        # For 90/270 degree rotations, swap width and height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            self.width, self.height = self.height, self.width
        
        # Update inflated values
        self._inflated_x = self.x - self._inflate
        self._inflated_y = self.y - self._inflate
        self._inflated_width = self.width + 2 * self._inflate
        self._inflated_height = self.height + 2 * self._inflate
        # Update bounds for any observers
        self._bounds_dirty = True
    
    def make_rotated(self, rotation: 'Rotation') -> 'Rectangle':
        """Return a new rectangle rotated by the given 90-degree increment."""
        # Calculate center point
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        # Skip rotation if center is at origin
        if abs(center_x) < 1e-6 and abs(center_y) < 1e-6:
            return Rectangle(
                -self.width / 2,
                -self.height / 2,
                self.width,
                self.height,
                self._inflate
            )
            
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_center_x = center_x * math.cos(angle) - center_y * math.sin(angle)
        new_center_y = center_x * math.sin(angle) + center_y * math.cos(angle)
        
        # Calculate new top-left position relative to rotated center
        new_x = new_center_x - self.width / 2
        new_y = new_center_y - self.height / 2
        
        # For 90/270 degree rotations, swap width and height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            return Rectangle(new_x, new_y, self.height, self.width, self._inflate)
        return Rectangle(new_x, new_y, self.width, self.height, self._inflate)
        
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
        from algorithms.intersections import rect_rect_intersect
        return rect_rect_intersect(self, other)
    
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
        
    def translate(self, dx: float, dy: float) -> None:
        """Translate this circle by the given amounts in-place."""
        self.cx += dx
        self.cy += dy
        self._bounds_dirty = True
    
    def make_translated(self, dx: float, dy: float) -> 'Circle':
        """Return a new circle translated by the given amounts."""
        return Circle(self.cx + dx, self.cy + dy, self.radius, self._inflate)
    
    def rotate(self, rotation: 'Rotation') -> None:
        """Rotate this circle by the given 90-degree increment in-place."""
        # Skip rotation if center is at origin
        if abs(self.cx) < 1e-6 and abs(self.cy) < 1e-6:
            return
            
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_cx = self.cx * math.cos(angle) - self.cy * math.sin(angle)
        new_cy = self.cx * math.sin(angle) + self.cy * math.cos(angle)
        
        self.cx = new_cx
        self.cy = new_cy
        self._bounds_dirty = True
    
    def make_rotated(self, rotation: 'Rotation') -> 'Circle':
        """Return a new circle rotated by the given 90-degree increment."""
        # Skip rotation if center is at origin
        if abs(self.cx) < 1e-6 and abs(self.cy) < 1e-6:
            return Circle(0, 0, self.radius, self._inflate)
            
        # Get rotation angle in radians
        angle = rotation.radians
            
        # Rotate center point around origin
        new_cx = self.cx * math.cos(angle) - self.cy * math.sin(angle)
        new_cy = self.cx * math.sin(angle) + self.cy * math.cos(angle)
        return Circle(new_cx, new_cy, self.radius, self._inflate)
        
    def _bounds_intersect(self, other: Rectangle) -> bool:
        """Test if this circle's bounds intersect a rectangle."""
        from algorithms.intersections import rect_circle_intersect
        return rect_circle_intersect(other, self)
