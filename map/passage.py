"""Passage map element definition."""

from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are rectangular corridors that connect rooms and other passages.
    The passage's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, grid_width: float, grid_height: float, map_: 'Map') -> 'Passage':
        """Create a passage using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in grid units
            grid_height: Height in grid units
            map_: Parent map instance
            
        Returns:
            A new Passage instance
        """
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        width, height = grid_to_drawing_size(grid_width, grid_height, map_.options)
        return cls(x, y, width, height, map_)
