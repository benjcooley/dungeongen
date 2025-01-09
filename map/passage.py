"""Passage map element definition."""

from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement
from graphics.conversions import grid_to_map
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are rectangular corridors that connect rooms and other passages.
    The passage's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape)
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, grid_width: float, grid_height) -> 'Passage':
        """Create a passage using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in grid units
            grid_height: Height in grid units
            
        Returns:
            A new Passage instance
        """
        x, y = grid_to_map(grid_x, grid_y)
        width, height = grid_to_map(grid_width, grid_height)
        return cls(x, y, width, height)
