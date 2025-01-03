"""Room map element definition."""

from algorithms.shapes import Rectangle, Circle
from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
    
    @classmethod
    def rectangular_room(cls, grid_x: float, grid_y: float, grid_width: float, grid_height: float, 
                        map_: 'Map') -> 'Room':
        """Create a rectangular room using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in grid units
            grid_height: Height in grid units
            map_: Parent map instance
            
        Returns:
            A new rectangular Room instance
        """
        x, y = grid_to_drawing(grid_x, grid_y, map_._options)
        width, height = grid_to_drawing_size(grid_width, grid_height, map_._options)
        return cls(x, y, width, height, map_)
    
    @classmethod
    def circular_room(cls, grid_cx: float, grid_cy: float, grid_radius: float,
                     map_: 'Map') -> 'Room':
        """Create a circular room using grid coordinates.
        
        Args:
            grid_cx: Center X coordinate in grid units
            grid_cy: Center Y coordinate in grid units
            grid_radius: Radius in grid units
            map_: Parent map instance
            
        Returns:
            A new Room instance with a circular shape
        """
        cx, cy = grid_to_drawing(grid_cx, grid_cy, map_._options)
        radius, _ = grid_to_drawing_size(grid_radius, 0, map_._options)
        
        # Create a Room with a Circle shape
        room = cls.__new__(cls)  # Create instance without calling __init__
        shape = Circle(cx, cy, radius)
        MapElement.__init__(room, shape=shape, map_=map_)
        return room
