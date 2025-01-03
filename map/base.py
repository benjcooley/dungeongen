"""Base classes for map elements."""

from dataclasses import dataclass
from typing import List

from algorithms.shapes import Rectangle
from algorithms.types import Shape

@dataclass
class MapElement:
    """Base class for all map elements.
    
    Each map element has:
    - A rectangular bounds defining its location and size
    - A shape defining its exact outline (which may differ from bounds)
    """
    bounds: Rectangle
    shape: Shape

class Map:
    """Container for all map elements."""
    
    def __init__(self) -> None:
        self.elements: List[MapElement] = []
    
    def add_element(self, element: MapElement) -> None:
        """Add a map element."""
        self.elements.append(element)
