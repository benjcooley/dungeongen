"""Base map element type definition."""

from map.base import MapElement
"""Base map element class definition."""

from typing import List, Protocol
from algorithms.shapes import Rectangle

class MapElement:
    """Base class for all map elements.
    
    A map element has:
    - A rectangular bounding box
    - A shape (which may be different from the bounds)
    - Connections to other map elements
    """
    
    def __init__(self, bounds: Rectangle, shape: Rectangle) -> None:
        self._bounds = bounds
        self._shape = shape
        self._connections: List['MapElement'] = []
    
    @property
    def bounds(self) -> Rectangle:
        """Get the rectangular bounding box of this element."""
        return self._bounds
    
    @property
    def shape(self) -> Rectangle:
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
