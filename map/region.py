"""Region class for grouping map elements."""

import skia
from typing import Sequence
from algorithms.shapes import ShapeGroup, Rectangle, Shape
from map.mapelement import MapElement


class Region(Shape):
    """A region of the map containing connected elements.

    A region represents a contiguous area of the map not separated by closed doors.
    It contains both the combined shape of all elements and references to the 
    elements themselves.
    """

    def __init__(self, shape: ShapeGroup, elements: Sequence[MapElement]) -> None:
        """Initialize a region with its shape and contained elements.

        Args:
            shape: The combined shape of all elements in the region
            elements: The map elements contained in this region
        """
        self.shape = shape
        self.elements = list(elements)

    def contains(self, px: float, py: float) -> bool:
        """Check if a point is contained within this region's shape."""
        return self.shape.contains(px, py)

    @property
    def bounds(self) -> Rectangle:
        """Get the bounding rectangle that encompasses this region."""
        return self.shape.bounds

    def draw(self, canvas: skia.Canvas, paint: skia.Paint) -> None:
        """Draw this region on a canvas."""
        self.shape.draw(canvas, paint)

    def to_path(self) -> skia.Path:
        """Convert this region's shape to a Skia path."""
        return self.shape.to_path()

    def inflated(self, amount: float) -> 'Region':
        """Return a new region with its shape inflated by the given amount."""
        return Region(
            shape=self.shape.inflated(amount),
            elements=self.elements
        )

    @property
    def is_valid(self) -> bool:
        """Check if this region is valid (has a valid shape)."""
        return self.shape.is_valid
