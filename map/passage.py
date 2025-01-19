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
        
        # Validate directions relative to start/end points
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy
        
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
            
        # Handle single grid case
        if abs(dx) <= 1 and abs(dy) <= 1:
            if start_direction == end_direction:
                return [start, end]
            return None
            
        # Try straight line if directions align
        if start_direction == end_direction:
            return [start, end]
            
        # Try L-shaped path if enough space
        if abs(dx) >= min_segment_length * 2 and abs(dy) >= min_segment_length * 2:
            points = [start]
            
            # Add corner point based on start direction
            if start_direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
                points.append((sx, ey))
            else:
                points.append((ex, sy))
                
            points.append(end)
            return points
            
        # For more complex paths, add random turns
        max_turns = min(3, max(abs(dx), abs(dy)) // min_segment_length)
        if max_turns < 1:
            return None
            
        # Try a few times with random turns
        for _ in range(10):
            points = [start]
            curr_x, curr_y = sx, sy
            curr_dir = start_direction
            turns_left = random.randint(1, max_turns)
            
            while turns_left >= 0:
                # Calculate remaining delta
                rem_dx = ex - curr_x
                rem_dy = ey - curr_y
                
                # Determine segment length
                if turns_left == 0:
                    # Final segment must reach end point
                    if curr_dir in (RoomDirection.NORTH, RoomDirection.SOUTH):
                        length = abs(ey - curr_y)
                    else:
                        length = abs(ex - curr_x)
                else:
                    # Random length but at least minimum
                    if curr_dir in (RoomDirection.NORTH, RoomDirection.SOUTH):
                        max_len = abs(rem_dy)
                    else:
                        max_len = abs(rem_dx)
                    length = random.randint(min_segment_length, max(min_segment_length, max_len-min_segment_length))
                
                # Add segment end point
                if curr_dir == RoomDirection.NORTH:
                    curr_y -= length
                elif curr_dir == RoomDirection.SOUTH:
                    curr_y += length
                elif curr_dir == RoomDirection.EAST:
                    curr_x += length
                else:  # WEST
                    curr_x -= length
                points.append((curr_x, curr_y))
                
                if turns_left == 0:
                    break
                    
                # Choose new direction
                if curr_dir in (RoomDirection.NORTH, RoomDirection.SOUTH):
                    curr_dir = RoomDirection.EAST if rem_dx > 0 else RoomDirection.WEST
                else:
                    curr_dir = RoomDirection.SOUTH if rem_dy > 0 else RoomDirection.NORTH
                    
                turns_left -= 1
                
            # Validate final direction matches required end direction
            if curr_dir == end_direction:
                return points
                
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
