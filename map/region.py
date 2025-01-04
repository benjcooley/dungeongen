"""Region class for grouping map elements."""

from typing import List, Sequence
from algorithms.shapes import ShapeGroup, Shape
from map.mapelement import MapElement

class Region:
    """A region of the map containing connected elements.
    
    A region represents a contiguous area of the map not separated by closed doors.
    It contains both the combined shape of all elements and references to the elements
    themselves.
    """
    
    def __init__(self, shape: ShapeGroup, elements: Sequence[MapElement]) -> None:
        """Initialize a region with its shape and contained elements.
        
        Args:
            shape: The combined shape of all elements in the region
            elements: The map elements contained in this region
        """
        self.shape = shape
        self.elements = list(elements)
    
    def inflated(self, amount: float) -> 'Region':
        """Return a new region with its shape inflated by the given amount."""
        return Region(
            shape=self.shape.inflated(amount),
            elements=self.elements
        )
    
    def to_path(self) -> 'skia.Path':
        """Convert this region's shape to a Skia path."""
        return self.shape.to_path()
