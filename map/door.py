"""Door map element definition."""

from algorithms.shapes import Rectangle
from map.mapelement import MapElement
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Door(MapElement):
    """A door connecting two map elements.
    
    Doors are small rectangular areas that mark connections between rooms and passages.
    The door's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map', open: bool = False) -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
        self._open = open
        self._bounds = shape.recalculate_bounds()
    
    def get_side_shape(self, connected: 'MapElement') -> Rectangle:
        """Get the shape for the door's side that connects to the given element.
        
        Returns a Rectangle representing half of the door's area on the side
        that connects to the given element.
        """
        if connected not in self.connections:
            raise ValueError("Element is not connected to this door")
            
        # Get center point of connected element
        conn_bounds = connected.bounds
        conn_cx = conn_bounds.x + conn_bounds.width / 2
        conn_cy = conn_bounds.y + conn_bounds.height / 2
        
        # Get door center
        door_cx = self._bounds.x + self._bounds.width / 2
        door_cy = self._bounds.y + self._bounds.height / 2
        
        # If door is more wide than tall, split horizontally
        if self._bounds.width > self._bounds.height:
            if conn_cx < door_cx:
                return Rectangle(self._bounds.x, self._bounds.y, 
                               self._bounds.width / 2, self._bounds.height)
            else:
                return Rectangle(door_cx, self._bounds.y,
                               self._bounds.width / 2, self._bounds.height)
        # Otherwise split vertically
        else:
            if conn_cy < door_cy:
                return Rectangle(self._bounds.x, self._bounds.y,
                               self._bounds.width, self._bounds.height / 2)
            else:
                return Rectangle(self._bounds.x, door_cy,
                               self._bounds.width, self._bounds.height / 2)
    
    @property
    def open(self) -> bool:
        """Whether this door is open (can be passed through)."""
        return self._open
    
    @open.setter
    def open(self, value: bool) -> None:
        self._open = value
