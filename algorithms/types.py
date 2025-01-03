"""Type definitions for the crosshatch pattern generator."""

from typing import Protocol, Tuple, Union

# Type aliases
Point = Tuple[float, float]
Line = Tuple[Point, Point]

class Shape(Protocol):
    """Protocol defining the interface for shapes."""
    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this shape."""
        ...
