"""Passage map element definition."""

from graphics.shapes import Rectangle, Shape
from map.mapelement import MapElement
from graphics.conversions import grid_to_map, grid_points_to_map_rect, map_to_grid_rect
from constants import CELL_SIZE
from typing import TYPE_CHECKING
from map.occupancy import ElementType

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.occupancy import OccupancyGrid

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
        will be either horizontal or vertical based on which coordinates match.
        Points will be ordered so the passage is always drawn in a positive direction.
        
        Args:
            start_x: Starting X coordinate in grid units
            start_y: Starting Y coordinate in grid units 
            end_x: Ending X coordinate in grid units
            end_y: Ending Y coordinate in grid units
            
        Returns:
            A new Passage instance
        """
        # Determine if passage is horizontal or vertical
        is_horizontal = abs(end_x - start_x) > abs(end_y - start_y)
        
        if is_horizontal:
            # For horizontal passages, use min/max x and average y
            grid_x = min(start_x, end_x)
            grid_width = max(start_x, end_x) - grid_x + 1
            grid_y = (start_y + end_y) / 2
            grid_height = 1
        else:
            # For vertical passages, use min/max y and average x
            grid_y = min(start_y, end_y)
            grid_height = max(start_y, end_y) - grid_y + 1
            grid_x = (start_x + end_x) / 2
            grid_width = 1
        
        # Create passage using grid rectangle
        return cls.from_grid(grid_x, grid_y, grid_width, grid_height)
        
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape and blocked areas into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        # Mark the passage itself
        grid.mark_rectangle(self._shape, ElementType.PASSAGE, element_idx)
        
        # Get grid coordinates of passage ends
        grid_x, grid_y, grid_width, grid_height = map_to_grid_rect(self._bounds)
        
        # Mark blocked cells at passage ends
        if grid_width > grid_height:  # Horizontal passage
            # Mark cells at each end of the passage
            grid.mark_cell(grid_x - 1, grid_y, ElementType.BLOCKED, element_idx, blocked=True)
            grid.mark_cell(grid_x + grid_width - 1, grid_y, ElementType.BLOCKED, element_idx, blocked=True)
        else:  # Vertical passage
            # Mark cells at each end of the passage
            grid.mark_cell(grid_x, grid_y - 1, ElementType.BLOCKED, element_idx, blocked=True)
            grid.mark_cell(grid_x, grid_y + grid_height - 1, ElementType.BLOCKED, element_idx, blocked=True)
