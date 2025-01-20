"""Passage map element definition."""

import random
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
                 allow_dead_end: bool = False,
                 min_segment_length: int = 2,
                 max_subdivisions: int = 3) -> None:
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
        
        # Create passage shape
        if len(grid_points) == 2:
            # For straight passages, use a single rectangle
            x1, y1 = grid_points[0]
            x2, y2 = grid_points[1]
            print(f"Grid points: ({x1},{y1}) to ({x2},{y2})")
            x, y, width, height = grid_points_to_map_rect(x1, y1, x2, y2)
            print(f"Map rect: x={x}, y={y}, w={width}, h={height}")
            print(f"Creating Rectangle with: x={x}, y={y}, width={width}, height={height}")
            shape = Rectangle(x, y, width, height)
            print(f"Created shape: {shape}")
        else:
            # For passages with corners, create shapes for each straight section
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
        min_segment_length: int = 2,
        max_subdivisions: int = 3
    ) -> Optional[List[Tuple[int, int]]]:
        """Generate a list of grid points for a passage with optional random turns.
        
        Following the segment-and-turn algorithm:
        1. Identify the straight runs needed to connect the points
        2. For each run longer than 2*min_segment_length:
           - Subdivide into random length pieces (at least min_segment_length each)
           - Add turns between pieces
        3. Connect the runs together
        
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
            return None

        # Handle single grid case
        sx, sy = start
        ex, ey = end
        if sx == ex and sy == ey:
            return [start]

        def subdivide_run(start_pt: tuple[int, int], end_pt: tuple[int, int]) -> list[tuple[int, int]]:
            """Subdivide a straight run into smaller segments."""
            x1, y1 = start_pt
            x2, y2 = end_pt
            
            # Calculate run length
            run_length = abs(x2 - x1) if x1 != x2 else abs(y2 - y1)
            
            # If run is too short for subdivision, return endpoints
            if run_length < 2 * min_segment_length:
                return [start_pt, end_pt]
            
            # Get unit direction vector
            dx = 1 if x2 > x1 else -1 if x2 < x1 else 0
            dy = 1 if y2 > y1 else -1 if y2 < y1 else 0
            
            points = [start_pt]
            curr_x, curr_y = x1, y1
            remaining = run_length
            subdivisions = 0
            
            while remaining >= 2 * min_segment_length and subdivisions < max_subdivisions:
                # Choose random length for this segment
                d = random.randint(min_segment_length, remaining - min_segment_length)
                
                # Move in current direction
                curr_x += dx * d
                curr_y += dy * d
                points.append((curr_x, curr_y))
                
                remaining -= d
                subdivisions += 1
            
            # Add final point if not at end
            if (curr_x, curr_y) != end_pt:
                points.append(end_pt)
                
            return points

        # Determine intermediate points based on directions
        corner_points = []
        
        # For parallel but opposite directions (zig-zag)
        if start_direction.is_parallel(end_direction):
            # Calculate offset for middle section
            offset = 2 * min_segment_length
            
            # Add two corners to create zig-zag
            if start_direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
                mid_x = min(sx, ex) + offset if start_direction == RoomDirection.EAST else max(sx, ex) - offset
                corner_points = [(mid_x, sy), (mid_x, ey)]
            else:
                mid_y = min(sy, ey) + offset if start_direction == RoomDirection.SOUTH else max(sy, ey) - offset
                corner_points = [(sx, mid_y), (ex, mid_y)]
                
        # For perpendicular directions (L-shape)
        elif start_direction.is_perpendicular(end_direction):
            # Add single corner point
            corner_x, corner_y = sx, sy
            if start_direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
                corner_y = ey
            else:
                corner_x = ex
            corner_points = [(corner_x, corner_y)]
            
        # Subdivide each straight run
        points = []
        prev_point = start
        
        # Process each segment including final run to end point
        for corner in corner_points + [end]:
            segment = subdivide_run(prev_point, corner)
            points.extend(segment[:-1])  # Don't add corner yet
            prev_point = corner
            
        # Add final point
        points.append(end)
        
        return points

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
            
        # Mark start and end points as blocked unless dead end
        if not self._allow_dead_end:
            # Get the cell just inside each room by using the opposite of passage direction
            start_x, start_y = self._grid_points[0]
            end_x, end_y = self._grid_points[-1]
            
            # For start point, use opposite of start direction to get cell inside room
            back_dx, back_dy = self._start_direction.get_back()
            grid.mark_blocked(start_x + back_dx, start_y + back_dy)
            
            # For end point, use opposite of end direction to get cell inside room  
            back_dx, back_dy = self._end_direction.get_back()
            grid.mark_blocked(end_x + back_dx, end_y + back_dy)
