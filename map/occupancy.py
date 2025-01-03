"""Grid-based occupancy tracking for map elements."""

from typing import Dict, Tuple, TYPE_CHECKING, Optional
from algorithms.shapes import Rectangle

if TYPE_CHECKING:
    from options import Options
    from map.mapelement import MapElement
from graphics.conversions import drawing_to_grid

GridPosition = Tuple[int, int]

class OccupancyGrid:
    """Tracks which grid spaces are occupied by map elements."""
    
    def __init__(self) -> None:
        # Maps grid positions to element indices (-1 means unoccupied)
        self._occupied: Dict[GridPosition, int] = {}
    
    def clear(self) -> None:
        """Clear all occupied positions."""
        self._occupied.clear()
    
    def mark_occupied(self, x: int, y: int, element_idx: int) -> None:
        """Mark a grid position as occupied by an element.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            element_idx: Index of the occupying element in the map
        """
        self._occupied[(x, y)] = element_idx
    
    def get_occupant(self, x: int, y: int) -> int:
        """Get the index of the element occupying a grid position.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            
        Returns:
            Index of occupying element, or -1 if unoccupied
        """
        return self._occupied.get((x, y), -1)
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied."""
        return self.get_occupant(x, y) >= 0
    
    def mark_rectangle(self, rect: Rectangle, element_idx: int, options: 'Options') -> None:
        """Mark all grid positions covered by a rectangle as occupied."""
        # Convert rectangle bounds to grid coordinates
        start_x, start_y = drawing_to_grid(rect.x, rect.y, options)
        end_x, end_y = drawing_to_grid(
            rect.x + rect.width,
            rect.y + rect.height,
            options
        )
        
        # Round to integer grid positions
        grid_start_x = int(start_x)
        grid_start_y = int(start_y)
        grid_end_x = int(end_x + 0.5)  # Round up
        grid_end_y = int(end_y + 0.5)  # Round up
        
        # Mark all covered grid positions
        for x in range(grid_start_x, grid_end_x):
            for y in range(grid_start_y, grid_end_y):
                self.mark_occupied(x, y)
