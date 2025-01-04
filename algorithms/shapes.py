"""Shape definitions for the crosshatch pattern generator."""

import math
import skia
from typing import List, Protocol, Sequence, TYPE_CHECKING
from algorithms.types import Point

if TYPE_CHECKING:
    from algorithms.shapes import Rectangle

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
    
    def inflated(self, amount: float) -> 'Shape':
        """Return a new shape inflated by the given amount."""
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
    
    def __init__(self, includes: Sequence[Shape], excludes: Sequence[Shape]) -> None:
        self.includes = list(includes)
        self.excludes = list(excludes)
    
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape group."""
        return (
            any(shape.contains(px, py) for shape in self.includes) and
            not any(shape.contains(px, py) for shape in self.excludes)
        )
    
    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this shape group using Skia's path operations."""
        if not self.includes:
            return
            
        # Create path for included shapes
        include_path = skia.Path()
        for shape in self.includes:
            shape_path = skia.Path()
            if isinstance(shape, Rectangle):
                shape_path.addRect(skia.Rect.MakeXYWH(
                    shape._inflated_x, shape._inflated_y,
                    shape._inflated_width, shape._inflated_height
                ))
            elif isinstance(shape, Circle):
                shape_path.addCircle(shape.cx, shape.cy, shape._inflated_radius)
            include_path.addPath(shape_path)
            
        # Subtract excluded shapes
        for shape in self.excludes:
            exclude_path = skia.Path()
            if isinstance(shape, Rectangle):
                exclude_path.addRect(skia.Rect.MakeXYWH(
                    shape._inflated_x, shape._inflated_y,
                    shape._inflated_width, shape._inflated_height
                ))
            elif isinstance(shape, Circle):
                exclude_path.addCircle(shape.cx, shape.cy, shape._inflated_radius)
            include_path.op(exclude_path, skia.PathOp.kDifference_PathOp)
            
        canvas.drawPath(include_path, paint)
    
    def inflated(self, amount: float) -> 'ShapeGroup':
        """Return a new shape group with all shapes inflated."""
        return ShapeGroup(
            includes=[s.inflated(amount) for s in self.includes],
            excludes=[s.inflated(amount) for s in self.excludes]
        )
    
    def _recalculate_bounds(self) -> None:
        """Calculate bounds by combining all included shapes' bounds."""
        if not self.includes:
            raise ValueError("Shape group must have at least one included shape")
        
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
    def bounds(self) -> Rectangle:
        """Get the current bounding rectangle, recalculating if needed."""
        if self._bounds_dirty or self._bounds is None:
            self._recalculate_bounds()
        return self._bounds

class Rectangle:
    """A rectangle that can be inflated to create a rounded rectangle effect.
    
    When inflated, the rectangle's corners become rounded with radius equal to
    the inflation amount, effectively creating a rounded rectangle shape.
    """
    
    @property
    def bounds(self) -> 'Rectangle':
        """Return this rectangle as bounds."""
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
        dx = max(0, abs(px - (self._inflated_x + self._inflated_width / 2)) - self._inflated_width / 2)
        dy = max(0, abs(py - (self._inflated_y + self._inflated_height / 2)) - self._inflated_height / 2)
        return math.sqrt(dx ** 2 + dy ** 2) <= self._inflate
    
    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this rectangle on a canvas."""
        if self._inflate > 0:
            # Draw with rounded corners when inflated
            canvas.drawRRect(
                skia.RRect.MakeRectXY(
                    skia.Rect.MakeXYWH(
                        self._inflated_x,
                        self._inflated_y,
                        self._inflated_width,
                        self._inflated_height
                    ),
                    self._inflate,  # x radius
                    self._inflate   # y radius
                ),
                paint
            )
        else:
            # Draw regular rectangle when not inflated
            canvas.drawRect(
                skia.Rect.MakeXYWH(
                    self._inflated_x,
                    self._inflated_y,
                    self._inflated_width,
                    self._inflated_height
                ),
                paint
            )
    
    def inflated(self, amount: float) -> 'Rectangle':
        """Return a new rectangle inflated by the given amount."""
        return Rectangle(self.x, self.y, self.width, self.height, self._inflate + amount)

class Circle:
    def __init__(self, cx: float, cy: float, radius: float, inflate: float = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius  # Original radius
        self._inflated_radius = radius + inflate

    @property
    def inflated(self) -> 'Circle':
        """Return a new Circle instance with the inflated radius."""
        return Circle(self.cx, self.cy, self._inflated_radius)

    def contains(self, px: float, py: float) -> bool:
        return math.sqrt((px - self.cx)**2 + (py - self.cy)**2) <= self._inflated_radius
    
    @property
    def bounds(self) -> Rectangle:
        """Get the bounding rectangle for this circle."""
        return Rectangle(
            self.cx - self._inflated_radius,
            self.cy - self._inflated_radius,
            self._inflated_radius * 2,
            self._inflated_radius * 2
        )
    
    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this circle on a canvas."""
        canvas.drawCircle(self.cx, self.cy, self._inflated_radius, paint)
    
    def inflated(self, amount: float) -> 'Circle':
        """Return a new circle inflated by the given amount."""
        return Circle(self.cx, self.cy, self.radius, self._inflate + amount)
