"""Passage map element definition."""

from dataclasses import dataclass
from graphics.shapes import Rectangle, Shape, ShapeGroup
from map.mapelement import MapElement
from graphics.conversions import grid_to_map, grid_points_to_map_rect, map_to_grid_rect
from constants import CELL_SIZE
from typing import TYPE_CHECKING, List, Tuple, Optional
from map.occupancy import ElementType, ProbeDirection, OccupancyGrid
from map.enums import RoomDirection

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.occupancy import OccupancyGrid

@dataclass
class PassagePoints:
    points: list[tuple[int, int]]
    manhattan_distances: list[int]
    bend_positions: list[int]
    
    def __len__(self):
        return len(self.points)
        
    def __getitem__(self, idx):
        return self.points[idx]
        
    def __iter__(self):
        return iter(self.points)
        
    def __str__(self):
        return str(self.points)

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are defined by a list of corner points that determine their path.
    Only two points are required to define a passage - the start and end points.
    Additional points can be added to create corners in the passage.
    
    Each grid point represents a 1x1 cell in the map coordinate system.
    The passage shape is composed of rectangles for each straight section between corners.
    """
    
    def __init__(self, grid_points: List[Tuple[int, int]], 
                 start_direction: Optional[RoomDirection] = None,
                 end_direction: Optional[RoomDirection] = None,
                 allow_dead_end: bool = False) -> None:
        """Create a passage from a list of corner points.
        
        Args:
            grid_points: List of (x,y) grid coordinates for passage corners. Only two points
                        are required - the start and end points. Additional points create
                        corners in the passage path.
            start_direction: Direction at start of passage (optional if can be determined from points)
            end_direction: Direction at end of passage (optional if can be determined from points) 
            allow_dead_end: Whether this passage can end without connecting to anything
            min_segment_length: Minimum grid cells between corners
            max_subdivisions: Maximum number of subdivisions per straight run
            
        Raises:
            ValueError: If directions cannot be determined from points and aren't provided
        """
        if not grid_points:
            raise ValueError("Passage must have at least one grid point")
            
        self._grid_points = grid_points
        self._allow_dead_end = allow_dead_end
        
        # For single point passages, both directions must be provided
        if len(grid_points) == 2 and grid_points[0] == grid_points[1]:
            if start_direction is None or end_direction is None:
                raise ValueError("Single point passages must specify both start and end directions")
            self._start_direction = start_direction
            self._end_direction = end_direction
        else:
            # Determine start direction from first two points if not provided
            if start_direction is None:
                x1, y1 = grid_points[0]
                x2, y2 = grid_points[1]
                # For start, use direction FROM first point TO second point
                self._start_direction = RoomDirection.from_delta(x2 - x1, y2 - y1)
            else:
                self._start_direction = start_direction
                
            # Determine end direction from last two points if not provided
            if end_direction is None:
                x1, y1 = grid_points[-1]  # Reversed: start from end point
                x2, y2 = grid_points[-2]  # And look back to previous point
                # For end, compute direction FROM end point looking BACK to previous point
                self._end_direction = RoomDirection.from_delta(x2 - x1, y2 - y1)
            else:
                self._end_direction = end_direction
        
        # Create passage shape
        if len(grid_points) == 2:
            # For straight passages, use a single rectangle
            x1, y1 = grid_points[0]
            x2, y2 = grid_points[1]
            x, y, width, height = grid_points_to_map_rect(x1, y1, x2, y2)
            
            # Validate one dimension is exactly one cell width
            if not (abs(width - CELL_SIZE) < 0.001 or abs(height - CELL_SIZE) < 0.001):
                raise ValueError(f"Passage must be exactly one cell wide. Got {width/CELL_SIZE}x{height/CELL_SIZE} cells")
            
            # Validate dimensions are positive and non-zero
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid passage dimensions: {width}x{height}")
                
            shape = Rectangle(x, y, width, height)
        else:
            # For passages with corners, create shapes for each straight section
            shapes = []
            for i in range(len(grid_points) - 1):
                x1, y1 = grid_points[i]
                x2, y2 = grid_points[i + 1]
                
                # Convert grid line to map rectangle
                x, y, width, height = grid_points_to_map_rect(x1, y1, x2, y2)
                
                # Validate one dimension is exactly one cell width
                if not (abs(width - CELL_SIZE) < 0.001 or abs(height - CELL_SIZE) < 0.001):
                    raise ValueError(f"Passage segment must be exactly one cell wide. Got {width/CELL_SIZE}x{height/CELL_SIZE} cells")
                
                # Validate dimensions are positive and non-zero
                if width <= 0 or height <= 0:
                    raise ValueError(f"Invalid passage dimensions: {width}x{height}")
                    
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
        bend_positions: List[int],
        min_run_length: int = 1
    ) -> PassagePoints:
        """Generate a list of grid points for a passage using specified bend positions.

        The passage is constructed by following the bend positions provided. Each bend position
        represents a distance along the Manhattan path from start to end where a turn occurs.
        
        The number of bends cannot exceed the minimum distance along either axis.
        For example, in an L-shaped passage of 4x2, only 1 bend would be allowed since min(4,2) = 2.

        Args:
            start: Starting grid point (x,y)
            start_direction: Direction to exit start point 
            end: Ending grid point (x,y)
            end_direction: Direction to enter end point
            bend_positions: List of positions along Manhattan path where turns occur
            min_run_length: Minimum length of each straight segment
        
        Args:
            start: Starting grid point (x,y)
            start_direction: Direction to exit start point
            end: Ending grid point (x,y)
            end_direction: Direction to enter end point
            min_segment_length: Minimum grid cells between turns (default 2)
            max_subdivisions: Maximum number of subdivisions per straight run
            
        Returns:
            List of grid points defining passage path, or None if no valid path possible
        """
        # First check if passage is possible
        if not Passage.can_connect(start, start_direction, end, end_direction):
            raise ValueError("Cannot connect points with given directions")

        # Handle single grid case
        sx, sy = start
        ex, ey = end
        if sx == ex and sy == ey:
            return PassagePoints([start], [0], [])

        # Calculate distances along each axis
        dx = abs(ex - sx)
        dy = abs(ey - sy)
        
        # Determine main and secondary axes based on direction alignment
        if start_direction.is_parallel(end_direction):
            # For parallel directions, subtract 2 from main axis for start/end segments
            if start_direction in (RoomDirection.EAST, RoomDirection.WEST):
                main_length = dx - 2
                secondary_length = dy
            else:
                main_length = dy - 2
                secondary_length = dx
        else:
            # For perpendicular directions, subtract 1 from both axes for start/end segments
            main_length = max(dx, dy) - 1
            secondary_length = min(dx, dy) - 1
            
        # Calculate maximum allowed bends based on adjusted lengths
        max_bends_allowed = min(main_length, secondary_length)
        if max_bends_allowed < 0:
            max_bends_allowed = 0
            
        # Validate number of bends
        if len(bend_positions) > max_bends_allowed:
            raise ValueError(f"Number of bends ({len(bend_positions)}) exceeds maximum allowed ({max_bends_allowed})")
            
        # Calculate total Manhattan distance for bend position validation
        D_total = dx + dy
            
        # Sort bend positions in ascending order
        bend_positions = sorted(bend_positions)
        
        # Initialize tracking variables
        points = [start]
        current = start
        current_direction = start_direction
        distance_covered = 0
        
        # Get movement vectors for each axis
        dx = 1 if ex > sx else -1 if ex < sx else 0
        dy = 1 if ey > sy else -1 if ey < sy else 0
        
        # Process each bend position
        for bend_pos in bend_positions:
            # Validate bend position
            if bend_pos <= distance_covered or bend_pos >= D_total:
                raise ValueError(f"Invalid bend position {bend_pos}")
            # Calculate distance to move before turning
            distance = bend_pos - distance_covered
            
            # Move in current direction to create orthogonal segments
            cx, cy = current
                
            # First create a point that shares one coordinate with previous point
            if current_direction in (RoomDirection.EAST, RoomDirection.WEST):
                # Moving horizontally, so keep same y coordinate
                cx += dx * distance
                current = (cx, cy)
                points.append(current)
                    
                # Switch to vertical direction
                current_direction = RoomDirection.SOUTH if ey > cy else RoomDirection.NORTH
                    
                # Then create another point for vertical movement
                cy = ey
                current = (cx, cy)
                points.append(current)
            else:
                # Moving vertically, so keep same x coordinate
                cy += dy * distance
                current = (cx, cy)
                points.append(current)
                    
                # Switch to horizontal direction
                current_direction = RoomDirection.EAST if ex > cx else RoomDirection.WEST
                    
                # Then create another point for horizontal movement
                cx = ex
                current = (cx, cy)
                points.append(current)
                
            distance_covered = bend_pos
            
        # Add final segment to end point if needed
        if current != end:
            points.append(end)
            
        # Calculate Manhattan distances for each point
        manhattan_distances = []
        current_dist = 0
        for i in range(1, len(points)):
            current_dist += abs(points[i][0] - points[i-1][0]) + abs(points[i][1] - points[i-1][1])
            manhattan_distances.append(current_dist)
            
        # Return PassagePoints object with all the data
        return PassagePoints(points, manhattan_distances, bend_positions)

    @staticmethod
    def can_connect(
        start: Tuple[int, int],
        start_direction: RoomDirection,
        end: Tuple[int, int],
        end_direction: RoomDirection
    ) -> bool:
        """Check if two points with given directions can be connected with a valid passage.
        
        Args:
            start: Starting grid point (x,y)
            start_direction: Direction to exit start point
            end: Ending grid point (x,y)
            end_direction: Direction to enter end point
            
        Returns:
            True if points can be connected with a valid passage, False otherwise
        """
        # For single point:
        if start[0] == end[0] and start[1] == end[1]:
            # Must be opposite directions
            return end_direction == start_direction.get_opposite()

        # For all other cases:                  
        return (start_direction.is_valid_direction_for(start, end) and
                end_direction.is_valid_direction_for(end, start))

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
        # For straight passages, mark rectangle between endpoints
        if len(self._grid_points) == 2:
            x1, y1 = self._grid_points[0]
            x2, y2 = self._grid_points[-1]
            x, y, w, h = grid_points_to_map_rect(x1, y1, x2, y2)
            rect = Rectangle(x, y, w, h)
            grid.mark_rectangle(rect, ElementType.PASSAGE, element_idx)
        else:
            # For passages with corners, mark rectangles between each pair of points
            for i in range(len(self._grid_points) - 1):
                x1, y1 = self._grid_points[i]
                x2, y2 = self._grid_points[i + 1]
                x, y, w, h = grid_points_to_map_rect(x1, y1, x2, y2)
                rect = Rectangle(x, y, w, h)
                grid.mark_rectangle(rect, ElementType.PASSAGE, element_idx)
            
        # Mark passage points and adjacent room spaces as blocked
        start_x, start_y = self._grid_points[0]
        end_x, end_y = self._grid_points[-1]
        
        # For single grid passages, block three cells:
        # 1. The passage cell itself
        # 2. The cell in the start room
        # 3. The cell in the end room
        if len(self._grid_points) == 2 and self._grid_points[0] == self._grid_points[1]:
            x, y = start_x, start_y
            
            # Block the passage cell itself
            grid.mark_blocked(x, y)
            
            # Block cell in start room (using opposite of start direction)
            back_dx, back_dy = self._start_direction.get_back()
            grid.mark_blocked(x + back_dx, y + back_dy)
            
            # Block cell in end room (using direction of end)
            dx, dy = self._end_direction.get_back()
            grid.mark_blocked(x + dx, y + dy)

        # For longer passages, block cells at start and end of passage
        else:
            # Block start position and cell just inside start room
            grid.mark_blocked(start_x, start_y)  # Block passage start
            back_dx, back_dy = self._start_direction.get_back()
            grid.mark_blocked(start_x + back_dx, start_y + back_dy)  # Block inside start room
            
            # Block end position and cell just inside end room
            grid.mark_blocked(end_x, end_y)  # Block passage end

            # Only block inside end room if not a dead end
            if not self._allow_dead_end:
                back_dx, back_dy = self._end_direction.get_back()
                grid.mark_blocked(end_x + back_dx, end_y + back_dy)  # Block inside end room
