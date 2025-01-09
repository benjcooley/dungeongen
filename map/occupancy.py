"""Grid-based occupancy tracking for map elements."""

from typing import List, TYPE_CHECKING
from array import array
from algorithms.shapes import Rectangle, Circle
from constants import CELL_SIZE

if TYPE_CHECKING:
    from options import Options
    from map.mapelement import MapElement
from graphics.conversions import map_to_grid

class OccupancyGrid:
    """Tracks which grid spaces are occupied by map elements using a 2D array."""
    
    def __init__(self, width: int, height: int) -> None:
        """Initialize an empty occupancy grid.
        
        Args:
            width: Width of the grid in cells
            height: Height of the grid in cells
        """
        # Initialize grid with -1 (unoccupied)
        self._grid = array('l', [-1] * (width * height))
        self.width = width
        self.height = height
    
    def clear(self) -> None:
        """Clear all occupied positions."""
        for i in range(len(self._grid)):
            self._grid[i] = -1
    
    def mark_occupied(self, x: int, y: int, element_idx: int) -> None:
        """Mark a grid position as occupied by an element.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            element_idx: Index of the occupying element in the map
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self._grid[y * self.width + x] = element_idx
    
    def get_occupant(self, x: int, y: int) -> int:
        """Get the index of the element occupying a grid position.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            
        Returns:
            Index of occupying element, or -1 if unoccupied/out of bounds
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._grid[y * self.width + x]
        return -1
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied."""
        return self.get_occupant(x, y) >= 0
    
    def mark_rectangle(self, rect: Rectangle, element_idx: int, options: 'Options') -> None:
        """Mark all grid positions covered by a rectangle as occupied."""
        # Convert rectangle bounds to grid coordinates
        start_x, start_y = map_to_grid(rect.x, rect.y)
        end_x, end_y = map_to_grid(rect.x + rect.width, rect.y + rect.height)
        
        # Round to integer grid positions
        grid_start_x = int(start_x)
        grid_start_y = int(start_y)
        grid_end_x = int(end_x + 0.5)  # Round up
        grid_end_y = int(end_y + 0.5)  # Round up
        
        # Mark all covered grid positions
        for x in range(grid_start_x, grid_end_x):
            for y in range(grid_start_y, grid_end_y):
                self.mark_occupied(x, y, element_idx)
    
    def mark_circle(self, circle: 'Circle', element_idx: int, options: 'Options') -> None:
        """Mark all grid positions covered by a circle as occupied.
        
        Only marks grid cells where the circle covers a significant portion of the cell.
        """
        # Convert circle to grid coordinates
        center_x, center_y = map_to_grid(circle.cx, circle.cy)
        radius = circle._inflated_radius / CELL_SIZE
        
        # Calculate grid bounds
        grid_start_x = int(center_x - radius - 0.5)
        grid_start_y = int(center_y - radius - 0.5)
        grid_end_x = int(center_x + radius + 1.5)
        grid_end_y = int(center_y + radius + 1.5)
        
        # Check each cell in the bounding box
        for x in range(grid_start_x, grid_end_x):
            for y in range(grid_start_y, grid_end_y):
                # Check each corner directly for better performance
                # Top-left corner
                dx = x - center_x
                dy = y - center_y
                if dx * dx + dy * dy <= radius * radius:
                    self.mark_occupied(x, y, element_idx)
                    continue

                # Top-right corner
                dx = (x + 1) - center_x
                dy = y - center_y
                if dx * dx + dy * dy <= radius * radius:
                    self.mark_occupied(x, y, element_idx)
                    continue

                # Bottom-left corner
                dx = x - center_x
                dy = (y + 1) - center_y
                if dx * dx + dy * dy <= radius * radius:
                    self.mark_occupied(x, y, element_idx)
                    continue

                # Bottom-right corner
                dx = (x + 1) - center_x
                dy = (y + 1) - center_y
                if dx * dx + dy * dy <= radius * radius:
                    self.mark_occupied(x, y, element_idx)
