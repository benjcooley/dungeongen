"""Type definitions for the crosshatch pattern generator."""

from typing import Protocol, Tuple, Union
from algorithms.shapes import Rectangle

# Type aliases
Point = Tuple[float, float]
Line = Tuple[Point, Point]

class Shape(Protocol):
    """Protocol defining the interface for shapes."""
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape."""
        ...
    
    def recalculate_bounds(self) -> 'Rectangle':
        """Calculate the bounding rectangle that encompasses this shape."""
        ...
