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
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape."""
        ...
    
    @property
    def bounds(self) -> 'Rectangle':
        """Get the bounding rectangle that encompasses this shape."""
        ...
    
    def draw(self, canvas: 'skia.Canvas', paint: 'skia.Paint') -> None:
        """Draw this shape on a canvas with the given paint."""
        ...
    
    def to_path(self) -> 'skia.Path':
        """Convert this shape to a Skia path."""
        ...
    
    def inflated(self, amount: float) -> 'Shape':
        """Return a new shape inflated by the given amount."""
        ...
    
    def translated(self, dx: float, dy: float) -> 'Shape':
        """Return a new shape translated by the given amounts."""
        ...
    
    def rotated(self, angle: float) -> 'Shape':
        """Return a new shape rotated by the given angle in radians."""
        ...
    
    def rotate_90(self, rotation: 'Rotation') -> 'Shape':
        """Return a new shape rotated by the given 90-degree increment."""
        ...
    
    @property
    def is_valid(self) -> bool:
        """Check if this shape is valid and can be rendered."""
        ...

class ShapeGroup:
    """A group of shapes that can be combined to create complex shapes."""
    
    def __init__(self, includes: Sequence[Shape], excludes: Sequence[Shape]) -> None:
        self.includes = list(includes)
        self.excludes = list(excludes)
        self._bounds: Rectangle | None = None
        self._bounds_dirty = True

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
    
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape group."""
        return (
            any(shape.contains(px, py) for shape in self.includes) and
            not any(shape.contains(px, py) for shape in self.excludes)
        )
    
    def to_path(self) -> skia.Path:
        """Convert this shape group to a Skia path."""
        if not self.includes:
            return skia.Path()
            
        # Start with the first included shape
        result_path = self.includes[0].to_path()
        
        # Union with remaining included shapes
        for shape in self.includes[1:]:
            result_path = skia.Op(result_path, shape.to_path(), skia.PathOp.kUnion_PathOp)
            
        # Subtract excluded shapes
        for shape in self.excludes:
            result_path = skia.Op(result_path, shape.to_path(), skia.PathOp.kDifference_PathOp)
            
        return result_path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this shape group using Skia's path operations."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'ShapeGroup':
        """Return a new shape group with all shapes inflated."""
        return ShapeGroup(
            includes=[s.inflated(amount) for s in self.includes],
            excludes=[s.inflated(amount) for s in self.excludes]
        )
        
    def rotated(self, angle: float) -> 'ShapeGroup':
        """Return a new shape group with all shapes rotated by angle in radians."""
        return ShapeGroup(
            includes=[s.rotated(angle) for s in self.includes],
            excludes=[s.rotated(angle) for s in self.excludes]
        )
    
    def rotate_90(self, rotation: 'Rotation') -> 'ShapeGroup':
        """Return a new shape group with all shapes rotated by 90-degree increment."""
        return ShapeGroup(
            includes=[s.rotate_90(rotation) for s in self.includes],
            excludes=[s.rotate_90(rotation) for s in self.excludes]
        )
    
    def _recalculate_bounds(self) -> None:
        """Calculate bounds by combining all included shapes' bounds."""
        if not self.is_valid:
            return
        
        # Start with the first shape's bounds
        bounds = self.includes[0].bounds
        
        # Expand bounds to include all other shapes
        for shape in self.includes[1:]:
            other_bounds = shape.bounds
            bounds = Rectangle(
                min(bounds.x, other_bounds.x),
                min(bounds.y, other_bounds.y),
                max(bounds.x + bounds.width, other_bounds.x + other_bounds.width) - min(bounds.x, other_bounds.x),
                max(bounds.y + bounds.height, other_bounds.y + other_bounds.height) - min(bounds.y, other_bounds.y)
            )
        
        self._bounds = bounds
        self._bounds_dirty = False

    @property
    def is_valid(self) -> bool:
        """Check if this shape group is valid (has at least one included shape)."""
        return len(self.includes) > 0
    
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
    
    def to_path(self) -> skia.Path:
        """Convert this rectangle to a Skia path."""
        path = skia.Path()
        if self._inflate > 0:
            path.addRRect(
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
            path.addRect(
                skia.Rect.MakeXYWH(
                    self._inflated_x,
                    self._inflated_y,
                    self._inflated_width,
                    self._inflated_height
                )
            )
        return path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this rectangle on a canvas."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'Rectangle':
        """Return a new rectangle inflated by the given amount."""
        return Rectangle(self.x, self.y, self.width, self.height, self._inflate + amount)
    
    def translated(self, dx: float, dy: float) -> 'Rectangle':
        """Return a new rectangle translated by the given amounts."""
        return Rectangle(self.x + dx, self.y + dy, self.width, self.height, self._inflate)
    
    def rotated(self, angle: float) -> 'Rectangle':
        """Return a new rectangle rotated by the given angle in radians."""
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
            
        # Rotate center point around origin
        new_center_x = center_x * math.cos(angle) - center_y * math.sin(angle)
        new_center_y = center_x * math.sin(angle) + center_y * math.cos(angle)
        
        # Calculate new top-left position relative to rotated center
        new_x = new_center_x - self.width / 2
        new_y = new_center_y - self.height / 2
        
        return Rectangle(new_x, new_y, self.width, self.height, self._inflate)
    
    def rotate_90(self, rotation: 'Rotation') -> 'Rectangle':
        """Return a new rectangle rotated by the given 90-degree increment."""
        return self.rotated(rotation.radians)
        
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

class Circle:
    def __init__(self, cx: float, cy: float, radius: float, inflate: float = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius  # Original radius
        self._inflate = inflate
        self._inflated_radius = radius + inflate

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
    
    def to_path(self) -> skia.Path:
        """Convert this circle to a Skia path."""
        path = skia.Path()
        path.addCircle(self.cx, self.cy, self._inflated_radius)
        return path

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this circle on a canvas."""
        canvas.drawPath(self.to_path(), paint)
    
    def inflated(self, amount: float) -> 'Circle':
        """Return a new circle inflated by the given amount."""
        return Circle(self.cx, self.cy, self.radius, self._inflate + amount)
        
    def translated(self, dx: float, dy: float) -> 'Circle':
        """Return a new circle translated by the given amounts."""
        return Circle(self.cx + dx, self.cy + dy, self.radius, self._inflate)
    
    def rotated(self, angle: float) -> 'Circle':
        """Return a new circle rotated by the given angle in radians."""
        # Skip rotation if center is at origin
        if abs(self.cx) < 1e-6 and abs(self.cy) < 1e-6:
            return Circle(0, 0, self.radius, self._inflate)
            
        # Rotate center point around origin
        new_cx = self.cx * math.cos(angle) - self.cy * math.sin(angle)
        new_cy = self.cx * math.sin(angle) + self.cy * math.cos(angle)
        return Circle(new_cx, new_cy, self.radius, self._inflate)
    
    def rotate_90(self, rotation: 'Rotation') -> 'Circle':
        """Return a new circle rotated by the given 90-degree increment."""
        return self.rotated(rotation.radians)
