"""Passage map element definition."""

from graphics.shapes import Rectangle, Shape, ShapeGroup
from map.mapelement import MapElement
from graphics.conversions import grid_to_map, grid_points_to_map_rect, map_to_grid_rect
from constants import CELL_SIZE
from typing import TYPE_CHECKING, List, Tuple, Optional
from map.occupancy import ElementType, ProbeDirection
from map._arrange.arrange_enums import RoomDirection

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.occupancy import OccupancyGrid

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are grid-based paths that can include corners and straight sections.
    Each grid point represents a 1x1 cell in the map coordinate system.
    The passage shape is composed of rectangles for each straight section.
    """
    
    def __init__(self, grid_points: List[Tuple[int, int]], 
                 start_direction: RoomDirection,
                 end_direction: RoomDirection,
                 allow_dead_end: bool = False) -> None:
        """Create a passage from a list of grid points.
        
        Args:
            grid_points: List of (x,y) grid coordinates defining the passage path
            start_direction: Direction at start of passage
            end_direction: Direction at end of passage
            allow_dead_end: Whether this passage can end without connecting to anything
        """
        self._grid_points = grid_points
        self._start_direction = start_direction
        self._end_direction = end_direction
        self._allow_dead_end = allow_dead_end
        
        # Create shapes for each straight section
        shapes = []
        for i in range(len(grid_points) - 1):
            x1, y1 = grid_points[i]
            x2, y2 = grid_points[i + 1]
            
            # Convert grid coordinates to map coordinates
            map_x1, map_y1 = grid_to_map(x1, y1)
            map_x2, map_y2 = grid_to_map(x2, y2)
            
            # Create rectangle for this section
            if x1 == x2:  # Vertical section
                x = map_x1
                y = min(map_y1, map_y2)
                width = CELL_SIZE
                height = abs(map_y2 - map_y1) + CELL_SIZE
            else:  # Horizontal section
                x = min(map_x1, map_x2)
                y = map_y1
                width = abs(map_x2 - map_x1) + CELL_SIZE
                height = CELL_SIZE
                
            shapes.append(Rectangle(x, y, width, height))
            
        # Combine shapes into a single shape group
        shape = ShapeGroup.combine(shapes)
        super().__init__(shape=shape)
        
    @property
    def grid_points(self) -> List[Tuple[int, int]]:
        """Get the grid points defining this passage."""
        return self._grid_points
        
    @property
    def start_direction(self) -> RoomDirection:
        """Get the direction at the start of the passage."""
        return self._start_direction
        
    @property
    def end_direction(self) -> RoomDirection:
        """Get the direction at the end of the passage."""
        return self._end_direction
        
    @property
    def allow_dead_end(self) -> bool:
        """Whether this passage can end without connecting to anything."""
        return self._allow_dead_end
    
    @classmethod
    def from_grid_path(cls, grid_points: List[Tuple[int, int]], 
                      start_direction: RoomDirection,
                      end_direction: RoomDirection,
                      allow_dead_end: bool = False) -> 'Passage':
        """Create a passage from a list of grid points.
        
        Args:
            grid_points: List of (x,y) grid coordinates defining the passage path
            start_direction: Direction at start of passage
            end_direction: Direction at end of passage
            allow_dead_end: Whether this passage can end without connecting to anything
            
        Returns:
            A new Passage instance
        """
        return cls(grid_points, start_direction, end_direction, allow_dead_end)
        
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape and blocked areas into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        # Mark each grid point as passage
        for x, y in self._grid_points:
            grid.mark_cell(x, y, ElementType.PASSAGE, element_idx)
            
        # Mark start and end points as blocked unless dead end
        if not self._allow_dead_end:
            grid.mark_cell(self._grid_points[0][0], self._grid_points[0][1], 
                         ElementType.BLOCKED, element_idx, blocked=True)
            grid.mark_cell(self._grid_points[-1][0], self._grid_points[-1][1],
                         ElementType.BLOCKED, element_idx, blocked=True)
