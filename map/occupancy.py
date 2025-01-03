"""Grid-based occupancy tracking for map elements."""

from typing import Set, Tuple, TYPE_CHECKING
from algorithms.shapes import Rectangle

if TYPE_CHECKING:
    from options import Options
from graphics.conversions import drawing_to_grid

GridPosition = Tuple[int, int]

class OccupancyGrid:
    """Tracks which grid spaces are occupied by map elements."""
    
    def __init__(self) -> None:
        self._occupied: Set[GridPosition] = set()
    
    def clear(self) -> None:
        """Clear all occupied positions."""
        self._occupied.clear()
    
    def mark_occupied(self, x: int, y: int) -> None:
        """Mark a grid position as occupied."""
        self._occupied.add((x, y))
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied."""
        return (x, y) in self._occupied
    
    def mark_rectangle(self, rect: Rectangle, options: 'Options') -> None:
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
