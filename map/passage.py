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
        min_segment_length: int = 2,
        max_subdivisions: int = 3
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
        
        # First check if passage is possible
        if not Passage.can_connect(start, start_direction, end, end_direction, min_segment_length):
            return None

        # Handle single grid case
        sx, sy = start
        ex, ey = end
        if sx == ex and sy == ey:
            return [start, end]

        # Handle straight passage case
        if sx == ex or sy == ey:
            if start_direction == end_direction:
                return [start, end]
                
        # Handle zig-zag case (parallel but opposite directions)
        if start_direction.is_parallel(end_direction):
            # Calculate offset based on direction
            if start_direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
                # Moving vertically, need horizontal offset
                offset = 2 * min_segment_length
                if start_direction == RoomDirection.EAST:
                    mid_x = min(sx, ex) + offset
                else:  # WEST
                    mid_x = max(sx, ex) - offset
                corner1 = (mid_x, sy)
                corner2 = (mid_x, ey)
            else:
                # Moving horizontally, need vertical offset
                offset = 2 * min_segment_length
                if start_direction == RoomDirection.SOUTH:
                    mid_y = min(sy, ey) + offset
                else:  # NORTH
                    mid_y = max(sy, ey) - offset
                corner1 = (sx, mid_y)
                corner2 = (ex, mid_y)
            return [start, corner1, corner2, end]
            
        # Handle L-shape case (perpendicular directions)
        if start_direction.is_perpendicular(end_direction):
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
            
            # Track number of subdivisions
            subdivisions = 0
            
            # While we can fit at least 2 more segments and haven't hit max subdivisions
            while remaining >= 2 * min_segment_length and subdivisions < max_subdivisions:
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

    @staticmethod
    def can_connect(
        start: Tuple[int, int],
        start_direction: RoomDirection,
        end: Tuple[int, int],
        end_direction: RoomDirection,
        min_segment_length: int = 2
    ) -> bool:
        """Check if two points with given directions can be connected with a valid passage.
        
        Args:
            start: Starting grid point (x,y)
            start_direction: Direction to exit start point
            end: Ending grid point (x,y)
            end_direction: Direction to enter end point
            min_segment_length: Minimum grid cells between turns (default 2)
            
        Returns:
            True if points can be connected with a valid passage, False otherwise
        """
        # Get deltas between points
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy

        # For single point:
        if dx == 0 and dy == 0:
            # Must be opposite directions
            return end_direction == start_direction.get_opposite()
                   
        # For straight lines:
        if sx == ex or sy == ey:
            # Get expected directions based on line
            line_dir = RoomDirection.from_points(start, end)
            if line_dir is None:
                return False
            # Start direction must match line direction
            # End direction must match reversed line direction
            return (start_direction == line_dir and 
                   end_direction == line_dir.get_opposite())

        # For L-shaped paths:
        # - Start direction must match first leg direction
        # - End direction must match second leg direction reversed
        # - Directions can be either perpendicular (L-shape) or parallel (zig-zag)
        if not (start_direction.is_perpendicular(end_direction) or 
                start_direction.is_parallel(end_direction)):
            return False
        # Start direction must match first leg direction
        # End direction must match second leg direction reversed
        if dx > 0:  # Going east
            if start_direction != RoomDirection.EAST: return False
            if dy > 0:  # Then south
                return end_direction == RoomDirection.NORTH
            else:  # Then north
                return end_direction == RoomDirection.SOUTH
        elif dx < 0:  # Going west
            if start_direction != RoomDirection.WEST: return False
            if dy > 0:  # Then south
                return end_direction == RoomDirection.NORTH
            else:  # Then north
                return end_direction == RoomDirection.SOUTH
        elif dy > 0:  # Going south
            if start_direction != RoomDirection.SOUTH: return False
            if dx > 0:  # Then east
                return end_direction == RoomDirection.WEST
            else:  # Then west
                return end_direction == RoomDirection.EAST
        else:  # Going north
            if start_direction != RoomDirection.NORTH: return False
            if dx > 0:  # Then east
                return end_direction == RoomDirection.WEST
            else:  # Then west
                return end_direction == RoomDirection.EAST

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
