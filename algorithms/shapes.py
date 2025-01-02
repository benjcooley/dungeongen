"""Shape definitions for the crosshatch pattern generator."""

import math
from typing import List, Sequence, Protocol
from algorithms.types import Point

class Shape(Protocol):
    """Protocol defining the interface for shapes."""
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape."""
        ...

class ShapeGroup(Shape):
    """A group of shapes that can be combined to create complex shapes."""
    
    def __init__(self, includes: Sequence[Shape], excludes: Sequence[Shape]) -> None:
        self.includes = list(includes)
        self.excludes = list(excludes)
    
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape group."""
        return (
            any(shape.contains(px, py) for shape in self.includes) and
            not any(shape.contains(px, py) for shape in self.excludes)
        )

class Rectangle:
    """A rectangle that can be inflated to create a rounded rectangle effect.
    
    When inflated, the rectangle's corners become rounded with radius equal to
    the inflation amount, effectively creating a rounded rectangle shape.
    """
    
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
