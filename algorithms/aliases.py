"""Type definitions for the crosshatch pattern generator."""

from typing import Protocol, Tuple, TYPE_CHECKING
import skia

if TYPE_CHECKING:
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
    
    def draw(self, canvas: 'skia.Canvas', paint: 'skia.Paint') -> None:
        """Draw this shape on a canvas with the given paint."""
        ...
    
    def inflated(self, amount: float) -> 'Shape':
        """Return a new shape inflated by the given amount."""
        ...

__all__ = ['Point', 'Line', 'Shape']
