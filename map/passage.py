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
    def from_grid(cls, grid_x: float, grid_y: float, grid_width: float, grid_height: float) -> 'Passage':
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

    @classmethod
    def from_grid_points(cls, start_x: float, start_y: float, end_x: float, end_y: float) -> 'Passage':
        """Create a passage between two grid points.
        
        Creates a passage that connects two points in grid coordinates. The passage
        will be either horizontal or vertical based on which dimension has the larger
        difference between points.
        
        Args:
            start_x: Starting X coordinate in grid units
            start_y: Starting Y coordinate in grid units 
            end_x: Ending X coordinate in grid units
            end_y: Ending Y coordinate in grid units
            
        Returns:
            A new Passage instance
        """
        # Convert both points to map coordinates
        x1, y1 = grid_to_map(start_x, start_y)
        x2, y2 = grid_to_map(end_x, end_y)
        
        # Determine if horizontal or vertical based on largest difference
        if abs(x2 - x1) > abs(y2 - y1):
            # Horizontal passage
            x = min(x1, x2)
            y = (y1 + y2) / 2
            width = abs(x2 - x1)
            height = CELL_SIZE  # One grid unit high
        else:
            # Vertical passage
            x = (x1 + x2) / 2
            y = min(y1, y2)
            width = CELL_SIZE   # One grid unit wide
            height = abs(y2 - y1)
            
        return cls(x, y, width, height)
