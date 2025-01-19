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
                 start_direction: Optional[RoomDirection] = None,
                 end_direction: Optional[RoomDirection] = None,
                 allow_dead_end: bool = False) -> None:
        """Create a passage from a list of grid points.
        
        Args:
            grid_points: List of (x,y) grid coordinates defining the passage path
            start_direction: Direction at start of passage (optional if can be determined from points)
            end_direction: Direction at end of passage (optional if can be determined from points)
            allow_dead_end: Whether this passage can end without connecting to anything
            
        Raises:
            ValueError: If directions cannot be determined from points and aren't provided
        """
        if not grid_points:
            raise ValueError("Passage must have at least one grid point")
            
        self._grid_points = grid_points
        self._allow_dead_end = allow_dead_end
        
        # For single point passages, both directions must be provided
        if len(grid_points) == 1:
            if start_direction is None or end_direction is None:
                raise ValueError("Single point passages must specify both start and end directions")
            self._start_direction = start_direction
            self._end_direction = end_direction
        else:
            # Determine start direction from first two points if not provided
            if start_direction is None:
                x1, y1 = grid_points[0]
                x2, y2 = grid_points[1]
                direction = OccupancyGrid.get_direction_between_points(x1, y1, x2, y2)
                if direction is None:
                    raise ValueError("Cannot determine start direction from zero-length line")
                self._start_direction = direction
            else:
                self._start_direction = start_direction
                
            # Determine end direction from last two points if not provided
            if end_direction is None:
                x1, y1 = grid_points[-2]
                x2, y2 = grid_points[-1]
                direction = OccupancyGrid.get_direction_between_points(x1, y1, x2, y2)
                if direction is None:
                    raise ValueError("Cannot determine end direction from zero-length line")
                self._end_direction = direction
            else:
                self._end_direction = end_direction
        
        # Create shapes for each straight section
        shapes = []
        for i in range(len(grid_points) - 1):
            x1, y1 = grid_points[i]
            x2, y2 = grid_points[i + 1]
            
            # Convert grid line to map rectangle
            x, y, width, height = grid_points_to_map_rect(x1, y1, x2, y2)
                
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
    
    @staticmethod
    def generate_passage_points(
        start: Tuple[int, int],
        start_direction: RoomDirection,
        end: Tuple[int, int],
        end_direction: RoomDirection,
        min_segment_length: int = 2
    ) -> Optional[List[Tuple[int, int]]]:
        """Generate a list of grid points for a passage with optional random turns.
        
        The passage will:
        - Start in the specified start_direction for at least min_segment_length
        - End in the specified end_direction for at least min_segment_length
        - Have random turns if direct path isn't possible/desired
        - Never double back (segments always make forward progress)
        - Have segments at least min_segment_length long
        
        Args:
            start: Starting grid point (x,y)
            start_direction: Direction to exit start point
            end: Ending grid point (x,y)
            end_direction: Direction to enter end point
            min_segment_length: Minimum grid cells between turns (default 2)
            
        Returns:
            List of grid points defining passage path, or None if no valid path possible
        """
        import random
        
        # Get deltas between points
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy
        
        # Handle single grid case first - points must be same and directions opposite
        if abs(dx) == 0 and abs(dy) == 0:
            # Check if directions are opposite
            if (start_direction == RoomDirection.NORTH and end_direction == RoomDirection.SOUTH) or \
               (start_direction == RoomDirection.SOUTH and end_direction == RoomDirection.NORTH) or \
               (start_direction == RoomDirection.EAST and end_direction == RoomDirection.WEST) or \
               (start_direction == RoomDirection.WEST and end_direction == RoomDirection.EAST):
                return [start, end]
            return None
            
        # Helper to check if direction is valid for delta
        def is_valid_direction(direction: RoomDirection, dx: int, dy: int) -> bool:
            if direction == RoomDirection.NORTH and dy > 0: return False
            if direction == RoomDirection.SOUTH and dy < 0: return False
            if direction == RoomDirection.EAST and dx < 0: return False
            if direction == RoomDirection.WEST and dx > 0: return False
            return True
            
        # Check start direction is valid
        if not is_valid_direction(start_direction, dx, dy):
            return None
            
        # Check end direction is valid
        if not is_valid_direction(end_direction, -dx, -dy):
            return None
            
        # Try straight line if directions align and either x or y matches
        if start_direction == end_direction and (sx == ex or sy == ey):
            return [start, end]
            
        # Find corner point for L-shape
        corner_x, corner_y = sx, sy
        if start_direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
            corner_y = ey
        else:
            corner_x = ex
            
        # Helper function to subdivide a run
        def subdivide_run(start_pt: tuple[int, int], end_pt: tuple[int, int]) -> list[tuple[int, int]]:
            x1, y1 = start_pt
            x2, y2 = end_pt
            
            # Calculate run length
            run_length = abs(x2 - x1) if x1 != x2 else abs(y2 - y1)
            
            # Get unit direction vector
            dx = 1 if x2 > x1 else -1 if x2 < x1 else 0
            dy = 1 if y2 > y1 else -1 if y2 < y1 else 0
            
            points = [start_pt]
            curr_x, curr_y = x1, y1
            remaining = run_length
            
            # While we can fit at least 2 more segments
            while remaining >= 2 * min_segment_length:
                # Choose random length for this segment
                d = random.randint(min_segment_length, remaining - min_segment_length)
                
                # Move in current direction
                curr_x += dx * d
                curr_y += dy * d
                points.append((curr_x, curr_y))
                
                remaining -= d
                
            # Add final segment if any length remains
            if remaining > 0:
                curr_x += dx * remaining
                curr_y += dy * remaining
                points.append((curr_x, curr_y))
                
            return points
            
        # Subdivide first run (start to corner)
        points = subdivide_run(start, (corner_x, corner_y))
        
        # Subdivide second run (corner to end)
        points.extend(subdivide_run((corner_x, corner_y), end)[1:])  # Skip first point as it's already added
                
        return None

    @classmethod
    def from_grid_path(cls, grid_points: List[Tuple[int, int]], 
                      start_direction: Optional[RoomDirection] = None,
                      end_direction: Optional[RoomDirection] = None,
                      allow_dead_end: bool = False) -> 'Passage':
        """Create a passage from a list of grid points.
        
        Args:
            grid_points: List of (x,y) grid coordinates defining the passage path
            start_direction: Direction at start of passage (optional if can be determined from points)
            end_direction: Direction at end of passage (optional if can be determined from points)
            allow_dead_end: Whether this passage can end without connecting to anything
            
        Returns:
            A new Passage instance
            
        Raises:
            ValueError: If directions cannot be determined from points and aren't provided
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
