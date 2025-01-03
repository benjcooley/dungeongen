"""Base map element type definition."""

from map.base import MapElement
"""Base map element class definition."""

from typing import List, Protocol
from algorithms.shapes import Rectangle, ShapeGroup

class MapElement:
    """Base class for all map elements.
    
    A map element has:
    - A shape (which defines its geometry)
    - A calculated bounding box based on the shape
    - Connections to other map elements
    """
    
    def __init__(self, shape: Rectangle | ShapeGroup) -> None:
        self._shape = shape
        self._connections: List['MapElement'] = []
    
    def recalculate_bounds(self) -> Rectangle:
        """Calculate the bounding rectangle that encompasses the shape.
        
        For simple rectangles, this returns the rectangle itself.
        For shape groups, it calculates the minimum bounding box that
        contains all included shapes.
        """
        if isinstance(self._shape, Rectangle):
            return self._shape
        elif isinstance(self._shape, ShapeGroup):
            # Get bounds of all included shapes
            includes = self._shape.includes
            if not includes:
                raise ValueError("Shape group must have at least one included shape")
            
            # Start with the first shape's bounds
            bounds = includes[0]
            
            # Expand bounds to include all other shapes
            for shape in includes[1:]:
                bounds = Rectangle(
                    min(bounds.x, shape.x),
                    min(bounds.y, shape.y),
                    max(bounds.x + bounds.width, shape.x + shape.width) - min(bounds.x, shape.x),
                    max(bounds.y + bounds.height, shape.y + shape.height) - min(bounds.y, shape.y)
                )
            
            return bounds
        else:
            raise TypeError(f"Unsupported shape type: {type(self._shape)}")
    
    @property
    def bounds(self) -> Rectangle:
        """Get the rectangular bounding box of this element."""
        return self.recalculate_bounds()
    
    @property
    def shape(self) -> Rectangle | ShapeGroup:
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
