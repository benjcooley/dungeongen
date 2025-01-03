"""Base map element type definition."""

from map.base import MapElement
"""Base map element class definition."""

from typing import List
from algorithms.shapes import Rectangle, ShapeGroup
from algorithms.types import Shape

class MapElement:
    """Base class for all map elements.
    
    A map element has:
    - A shape (which defines its geometry)
    - A calculated bounding box based on the shape
    - Connections to other map elements
    """
    
    def __init__(self, shape: Shape) -> None:
        self._shape = shape
        self._connections: List['MapElement'] = []
    
    def recalculate_bounds(self) -> Rectangle:
        """Calculate the bounding rectangle that encompasses the shape."""
        return self._shape.recalculate_bounds()
    
    @property
    def bounds(self) -> Rectangle:
        """Get the rectangular bounding box of this element."""
        return self.recalculate_bounds()
    
    @property
    def shape(self) -> Shape:
        """Get the shape of this element."""
        return self._shape
    
    @property
    def connections(self) -> List['MapElement']:
        """Get all map elements connected to this one."""
        return self._connections.copy()
    
    def connect_to(self, other: 'MapElement') -> None:
        """Connect this element to another map element.
        
        The connection is bidirectional - both elements will be connected
        to each other.
        """
        if other not in self._connections:
            self._connections.append(other)
            other.connect_to(self)
    
    def disconnect_from(self, other: 'MapElement') -> None:
        """Remove connection to another map element.
        
        The disconnection is bidirectional - both elements will be
        disconnected from each other.
        """
        if other in self._connections:
            self._connections.remove(other)
            other.disconnect_from(self)
