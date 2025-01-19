"""Grid-based occupancy tracking for map elements."""

from typing import List, Optional, Set, Tuple, TYPE_CHECKING, NamedTuple
from array import array
from enum import IntFlag, auto, Enum
from dataclasses import dataclass
from dataclasses import dataclass
import skia
from logging_config import logger, LogTags
from graphics.shapes import Rectangle, Circle
from constants import CELL_SIZE
from graphics.conversions import map_to_grid, map_rect_to_grid_points, map_to_grid_rect, grid_to_map
from map._arrange.arrange_enums import RoomDirection
from options import Options
from debug_draw import debug_draw_grid_cell
from debug_config import debug_draw

if TYPE_CHECKING:
    from map.mapelement import MapElement

class ProbeDirection(Enum):
    """Directions for grid navigation probe.
    
    Directions are numbered clockwise from 0-7:
    0 = North
    1 = Northeast
    2 = East
    3 = Southeast
    4 = South
    5 = Southwest
    6 = West
    7 = Northwest
    """
    NORTH = 0
    NORTHEAST = 1
    EAST = 2
    SOUTHEAST = 3
    SOUTH = 4
    SOUTHWEST = 5
    WEST = 6
    NORTHWEST = 7
    
    def turn_left(self) -> 'ProbeDirection':
        """Return the direction 90 degrees to the left."""
        return ProbeDirection((self.value - 2) % 8)
    
    def turn_right(self) -> 'ProbeDirection':
        """Return the direction 90 degrees to the right."""
        return ProbeDirection((self.value + 2) % 8)
    
    def turn_around(self) -> 'ProbeDirection':
        """Return the opposite direction."""
        return ProbeDirection((self.value + 4) % 8)
        
    @staticmethod
    def from_delta(dx: int, dy: int) -> 'ProbeDirection':
        """Convert a delta to a cardinal direction."""
        if dx > 0:
            return ProbeDirection.EAST
        elif dx < 0:
            return ProbeDirection.WEST
        elif dy > 0:
            return ProbeDirection.SOUTH
        else:
            return ProbeDirection.NORTH
    
    def get_offset(self) -> tuple[int, int]:
        """Get the grid coordinate offset for this direction."""
        offsets = {
            ProbeDirection.NORTH: (0, -1),
            ProbeDirection.NORTHEAST: (1, -1),
            ProbeDirection.EAST: (1, 0),
            ProbeDirection.SOUTHEAST: (1, 1),
            ProbeDirection.SOUTH: (0, 1),
            ProbeDirection.SOUTHWEST: (-1, 1),
            ProbeDirection.WEST: (-1, 0),
            ProbeDirection.NORTHWEST: (-1, -1)
        }
        return offsets[self]

@dataclass
class ProbeResult:
    """Results from probing a grid cell."""
    element_type: 'ElementType'
    element_idx: int
    blocked: bool
    
    @property
    def is_empty(self) -> bool:
        """Check if cell is completely empty."""
        return self.element_type == ElementType.NONE and not self.blocked
    
    @property
    def is_blocked(self) -> bool:
        """Check if cell is blocked."""
        return self.blocked
    
    @property
    def is_passage(self) -> bool:
        """Check if cell contains a passage."""
        return self.element_type == ElementType.PASSAGE
    
    @property
    def is_room(self) -> bool:
        """Check if cell contains a room."""
        return self.element_type == ElementType.ROOM
    
    @property
    def is_door(self) -> bool:
        """Check if cell contains a door."""
        return self.element_type == ElementType.DOOR

class GridProbe:
    """Virtual explorer for navigating the occupancy grid.
    
    The probe maintains a position and facing direction, and can:
    - Move forward/backward
    - Turn left/right
    - Check cells in any direction
    - Follow passages
    """
    
    def __init__(self, grid: 'OccupancyGrid', x: int, y: int, 
                 facing: ProbeDirection = ProbeDirection.NORTH):
        self.grid = grid
        self.x = x
        self.y = y
        self._facing = facing
        self._dx, self._dy = facing.get_offset()
        
    @property
    def facing(self) -> ProbeDirection:
        """Get the current facing direction."""
        return self._facing
        
    @facing.setter 
    def facing(self, value: ProbeDirection) -> None:
        """Set the facing direction and update cached offsets."""
        if value != self._facing:
            self._facing = value
            self._dx, self._dy = value.get_offset()
    
    def move_forward(self) -> None:
        """Move one cell in the facing direction."""
        self.x += self._dx
        self.y += self._dy
    
    def move_backward(self) -> None:
        """Move one cell opposite the facing direction."""
        self.x -= self._dx
        self.y -= self._dy
    
    def turn_left(self) -> None:
        """Turn 90 degrees left."""
        self.facing = self.facing.turn_left()
    
    def turn_right(self) -> None:
        """Turn 90 degrees right."""
        self.facing = self.facing.turn_right()
    
    def check_direction(self, direction: ProbeDirection) -> ProbeResult:
        """Check the cell in the given direction without moving."""
        dx, dy = direction.get_offset()
        element_type, element_idx, blocked = self.grid.get_cell_info(
            self.x + dx, self.y + dy
        )
        return ProbeResult(element_type, element_idx, blocked)
    
    def check_forward(self) -> ProbeResult:
        """Check the cell in front without moving."""
        return self.check_direction(self.facing)
    
    def check_backward(self) -> ProbeResult:
        """Check the cell behind without moving."""
        return self.check_direction(self.facing.turn_around())
    
    def check_left(self) -> ProbeResult:
        """Check the cell to the left without moving."""
        return self.check_direction(self.facing.turn_left())
    
    def check_right(self) -> ProbeResult:
        """Check the cell to the right without moving."""
        return self.check_direction(self.facing.turn_right())
        
    def check_forward_left(self) -> ProbeResult:
        """Check the cell diagonally forward-left without moving."""
        return self.check_direction(ProbeDirection((self.facing.value - 1) % 8))
        
    def check_forward_right(self) -> ProbeResult:
        """Check the cell diagonally forward-right without moving."""
        return self.check_direction(ProbeDirection((self.facing.value + 1) % 8))
        
    def check_backward_left(self) -> ProbeResult:
        """Check the cell diagonally backward-left without moving."""
        return self.check_direction(ProbeDirection((self.facing.value - 3) % 8))
        
    def check_backward_right(self) -> ProbeResult:
        """Check the cell diagonally backward-right without moving."""
        return self.check_direction(ProbeDirection((self.facing.value + 3) % 8))

class ElementType(IntFlag):
    """Element types for occupancy grid cells."""
    NONE = 0
    ROOM = 1
    PASSAGE = 2
    DOOR = 3
    STAIRS = 4
    BLOCKED = 5

class OccupancyGrid:
    """Tracks which grid spaces are occupied by map elements using a 2D array.
    
    Each grid cell stores:
    - Element type flags (5 bits)
    - Element index (26 bits)
    - Blocked flag (1 bit)
    """
    
    # Bit layout:
    # [31]     = BLOCKED flag
    # [30-26]  = Element type (5 bits)
    # [25-16]  = Reserved
    # [15-0]   = Element index (16 bits)
    # Note: Index 0 is marked as occupied by setting bit 16
    
    # Bit masks
    BLOCKED_MASK = 0x80000000  # Bit 31
    TYPE_MASK   = 0x7C000000  # Bits 30-26
    OCCUPIED_BIT = 0x00010000  # Bit 16
    INDEX_MASK  = 0x0000FFFF  # Bits 15-0
    
    # Bit shifts
    BLOCKED_SHIFT = 31
    TYPE_SHIFT = 26
    INDEX_SHIFT = 0
    
    # Maximum length of a passage in grid cells
    MAX_PASSAGE_LENGTH = 100
    
    def __init__(self, width: int, height: int) -> None:
        """Initialize an empty occupancy grid with default size."""
        self._grid = array('L', [0] * (width * height))  # Using unsigned long
        self.width = width
        self.height = height
        self._origin_x = width // 2  # Center point
        self._origin_y = height // 2
        
        # Pre-allocate array for passage validation points (x,y,dir as 16-bit ints)
        self._points = array('h', [0] * (self.MAX_PASSAGE_LENGTH * 2 * 3))  # x,y,dir triplets
        self._crossed_passages = []  # List of crossed passage indices
        self._point_count = 0
        
    def _ensure_contains(self, grid_x: int, grid_y: int) -> None:
        """Resize grid if needed to contain the given grid coordinates."""
        min_grid_x = -self._origin_x
        min_grid_y = -self._origin_y
        max_grid_x = self.width - self._origin_x
        max_grid_y = self.height - self._origin_y
        
        needs_resize = False
        new_width = self.width
        new_height = self.height
        
        # Check if we need to expand
        while grid_x < min_grid_x or grid_x >= max_grid_x:
            new_width *= 2
            needs_resize = True
            min_grid_x = -(new_width // 2)
            max_grid_x = new_width - (new_width // 2)
            
        while grid_y < min_grid_y or grid_y >= max_grid_y:
            new_height *= 2
            needs_resize = True
            min_grid_y = -(new_height // 2)
            max_grid_y = new_height - (new_height // 2)
            
        if needs_resize:
            self._resize(new_width, new_height)
            
    def _resize(self, new_grid_width: int, new_grid_height: int) -> None:
        """Resize the grid, preserving existing contents."""
        new_grid = array('L', [0] * (new_grid_width * new_grid_height))
        new_grid_origin_x = new_grid_width // 2
        new_grid_origin_y = new_grid_height // 2
        old_width = self.width
        old_height = self.height
        
        # Copy existing contents
        for grid_y in range(self.height):
            for grid_x in range(self.width):
                old_idx = grid_y * self.width + grid_x
                old_value = self._grid[old_idx]
                
                # Convert array coordinates to grid coordinates and back to new array coordinates
                grid_x_pos = grid_x - self._origin_x  # Convert to grid coordinates
                grid_y_pos = grid_y - self._origin_y
                new_grid_x = grid_x_pos + new_grid_origin_x  # Convert to new array coordinates  
                new_grid_y = grid_y_pos + new_grid_origin_y
                new_idx = new_grid_y * new_grid_width + new_grid_x
                
                if 0 <= new_grid_x < new_grid_width and 0 <= new_grid_y < new_grid_height:
                    new_grid[new_idx] = old_value
                    
        self._grid = new_grid
        self.width = new_grid_width
        self.height = new_grid_height
        self._origin_x = new_grid_origin_x
        self._origin_y = new_grid_origin_y
    
    def _to_grid_index(self, grid_x: int, grid_y: int) -> Optional[int]:
        """Convert grid coordinates to array index."""
        array_x = grid_x + self._origin_x
        array_y = grid_y + self._origin_y
        if 0 <= array_x < self.width and 0 <= array_y < self.height:
            return array_y * self.width + array_x
        return None
    
    def clear(self) -> None:
        """Clear all occupied positions."""
        for i in range(len(self._grid)):
            self._grid[i] = 0
            
    def _encode_cell(self, element_type: ElementType, element_idx: int, blocked: bool = False) -> int:
        """Encode cell information into a single integer."""
        if element_idx < 0 or element_idx > 0xFFFF:
            raise ValueError(f"Element index {element_idx} out of valid range (0-65535)")
            
        value = element_idx & self.INDEX_MASK
        value |= self.OCCUPIED_BIT  # Always set occupied bit
        value |= (element_type.value << self.TYPE_SHIFT) & self.TYPE_MASK
        if blocked:
            value |= self.BLOCKED_MASK
        return value
    
    def _decode_cell(self, value: int) -> Tuple[ElementType, int, bool]:
        """Decode cell information from an integer."""
        if not value & self.OCCUPIED_BIT:
            return ElementType.NONE, -1, False
            
        element_type = ElementType((value & self.TYPE_MASK) >> self.TYPE_SHIFT)
        element_idx = value & self.INDEX_MASK
        blocked = bool(value & self.BLOCKED_MASK)
        return element_type, element_idx, blocked
    
    def mark_cell(self, grid_x: int, grid_y: int, element_type: ElementType, 
                  element_idx: int, blocked: bool = False) -> None:
        """Mark a grid cell with element info."""
        self._ensure_contains(grid_x, grid_y)
        idx = self._to_grid_index(grid_x, grid_y)
        if idx is not None:
            self._grid[idx] = self._encode_cell(element_type, element_idx, blocked)
            
    def get_cell_info(self, grid_x: int, grid_y: int) -> Tuple[ElementType, int, bool]:
        """Get element type, index and blocked status at grid position."""
        idx = self._to_grid_index(grid_x, grid_y)
        if idx is not None:
            return self._decode_cell(self._grid[idx])
        return ElementType.NONE, -1, False
    
    def is_occupied(self, grid_x: int, grid_y: int) -> bool:
        """Check if a grid position is occupied."""
        idx = self._to_grid_index(grid_x, grid_y)
        return idx is not None and bool(self._grid[idx] & self.OCCUPIED_BIT)
    
    def is_blocked(self, grid_x: int, grid_y: int) -> bool:
        """Check if a grid position is blocked (can't place props)."""
        idx = self._to_grid_index(grid_x, grid_y)
        return idx is not None and bool(self._grid[idx] & self.BLOCKED_MASK)
    
    def get_element_type(self, grid_x: int, grid_y: int) -> ElementType:
        """Get the element type at a grid position."""
        element_type, _, _ = self.get_cell_info(grid_x, grid_y)
        return element_type
    
    def get_element_index(self, grid_x: int, grid_y: int) -> int:
        """Get the element index at a grid position."""
        _, element_idx, _ = self.get_cell_info(grid_x, grid_y)
        return element_idx
    
    def mark_rectangle(self, shape: Rectangle | Circle, element_type: ElementType,
                      element_idx: int, clip_rect: Optional[Rectangle] = None) -> None:
        """Mark all grid positions covered by a shape.
        
        Args:
            shape: The shape to rasterize (Rectangle or Circle)
            element_type: Type of element being marked
            element_idx: Index of element being marked
            clip_rect: Optional rectangle to clip rasterization to
        """
        if isinstance(shape, Circle):
            self.mark_circle(shape, element_type, element_idx, clip_rect)
            return
            
        # Convert to grid rectangle
        grid_rect = Rectangle(*map_to_grid_rect(shape))
            
        # Apply clip rect if specified
        if clip_rect:
            grid_rect = grid_rect.intersection(Rectangle(*map_to_grid_rect(clip_rect)))
            
        # Early out if no valid region
        if not grid_rect.is_valid:
            return
            
        # Fill the grid rectangle
        for x in range(int(grid_rect.x), int(grid_rect.x + grid_rect.width)):
            for y in range(int(grid_rect.y), int(grid_rect.y + grid_rect.height)):
                self.mark_cell(x, y, element_type, element_idx)

    def mark_circle(self, circle: Circle, element_type: ElementType,
                   element_idx: int, clip_rect: Optional[Rectangle] = None) -> None:
        """Mark grid cells covered by a circle.
        
        Args:
            circle: The circle to rasterize
            element_type: Type of element being marked
            element_idx: Index of element being marked
            clip_rect: Optional rectangle to clip rasterization to
        """
        # Convert circle bounds to grid coordinates
        grid_rect = Rectangle(*map_to_grid_rect(circle.bounds))
        
        # Apply clip rect if specified
        if clip_rect:
            grid_rect = grid_rect.intersection(Rectangle(*map_to_grid_rect(clip_rect)))
            
        # Early out if no valid region
        if not grid_rect.is_valid:
            return
            
        # Test each cell center against circle
        radius_sq = (circle.radius / CELL_SIZE) * (circle.radius / CELL_SIZE)
        center_x = circle.cx / CELL_SIZE
        center_y = circle.cy / CELL_SIZE
        
        for x in range(int(grid_rect.x), int(grid_rect.x + grid_rect.width)):
            for y in range(int(grid_rect.y), int(grid_rect.y + grid_rect.height)):
                dx = (x + 0.5) - center_x
                dy = (y + 0.5) - center_y
                if dx * dx + dy * dy <= radius_sq:
                    self.mark_cell(x, y, element_type, element_idx)

    def check_rectangle(self, grid_rect: Rectangle, inflate_cells: int = 1) -> bool:
        """Check if a rectangle area is unoccupied.
        
        Args:
            rect: Rectangle to check in map coordinates
            inflate_cells: Number of grid cells to inflate by before checking
            
        Returns:
            True if area is valid (unoccupied), False otherwise
        """
        grid_x1 = int(grid_rect.x) - inflate_cells
        grid_y1 = int(grid_rect.y) - inflate_cells
        grid_x2 = int(grid_rect.x + grid_rect.width) + (inflate_cells * 2)
        grid_y2 = int(grid_rect.y + grid_rect.height) + (inflate_cells * 2)
            
        # Check each cell in grid coordinates
        for grid_x in range(grid_x1, grid_x2):
            for grid_y in range(grid_y1, grid_y2):
                idx = self._to_grid_index(grid_x, grid_y)
                if idx is not None and self._grid[idx] != 0:
                    return False
        return True
        
    def check_circle(self, grid_circle: Circle, inflate_cells: int = 1) -> bool:
        """Check if a circle area is unoccupied.
        
        Args:
            circle: Circle to check in map coordinates
            inflate_cells: Number of grid cells to inflate by before checking
            
        Returns:
            True if area is valid (unoccupied), False otherwise
        """
        # Inflate circle first, then convert bounds to grid coordinates
        grid_rect = grid_circle.bounds
            
        grid_x1 = int(grid_rect.x) - inflate_cells
        grid_y1 = int(grid_rect.y) - inflate_cells
        grid_x2 = int(grid_rect.x + grid_rect.width) + (inflate_cells * 2)
        grid_y2 = int(grid_rect.y + grid_rect.height) + (inflate_cells * 2)

        # Calculate grid-space circle parameters
        inflated_radius = grid_circle.radius + inflate_cells
        grid_radius_sq = inflated_radius * inflated_radius
        grid_center_x = grid_circle.cx
        grid_center_y = grid_circle.cy
        
        # Check each cell in grid coordinates
        for grid_x in range(grid_x1, grid_x2 + 1):
            for grid_y in range(grid_y1, grid_y2 + 1):
                # Test cell center against circle
                dx = (grid_x + 0.5) - grid_center_x
                dy = (grid_y + 0.5) - grid_center_y
                if dx * dx + dy * dy <= grid_radius_sq:
                    idx = self._to_grid_index(grid_x, grid_y)
                    if idx is not None and self._grid[idx] != 0:
                        return False
        return True

    def check_passage(self, points: list[tuple[int, int]], start_direction: RoomDirection, 
                     allow_dead_end: bool = False) -> tuple[bool, list[int]]:
        """Check if a passage can be placed along a series of grid points.
        
        This is a performance-critical method used frequently during dungeon generation.
        It uses a single reused probe and optimized checks to validate passage placement.
        
        The passage validation rules are:
        
        1. Single Point Passage:
           - MUST have room/passage behind (no exceptions)
           - Must have empty spaces on both sides (left/right)
           - Must have room/passage ahead (unless allow_dead_end=True)
        
        2. Multi-Point Passage:
           a) Start Point:
              - MUST have room/passage behind (no exceptions)
              - Must have empty sides (left/right)
              - Direction determined by next point
           
           b) End Point:
              - Must have room/passage ahead (unless allow_dead_end=True)
              - Must have empty sides (left/right)
              - Direction determined by previous point
           
           c) Corner Points (direction changes):
              - Must have ALL 8 surrounding cells empty (no adjacent rooms/passages)
              - If intersecting a passage:
                * Return false but add passage index to crossed_passages list
                * This allows using intersection point as potential connection
           
           d) Passage Crossing Points:
              - Must have 3 empty cells behind and 3 empty cells ahead
              - This spacing automatically enforces:
                * Right angle crossings only
                * No parallel passages
                * Proper passage spacing
           
           e) Regular Points:
              - Direction determined by previous and next points
              - Must have empty sides (left/right)
              - Cannot be blocked
        
        Args:
            points: List of (x,y) grid coordinates for the passage
            start_direction: Initial facing direction (needed for single-point passages)
            
        Returns:
            Tuple of (is_valid, crossed_passage_indices)
            where is_valid is True if path is valid,
            and crossed_passage_indices is a list of unique passage indices crossed,
            even if validation fails
        """
        if not points:
            return False, []
            
        # Reset crossed passages tracking
        cross_count = 0
        
        # Reuse a single probe for all checks
        probe = GridProbe(self, 0, 0, facing=self._room_to_probe_dir(start_direction))
        
        # Handle single point case efficiently 
        if len(points) == 1:
            x, y = points[0]
            return self._check_single_point(x, y, self._room_to_probe_dir(start_direction), 
                                         allow_dead_end), []
            
        # Expand corner points into full grid point sequence
        self._point_count = self._expand_passage_points(points)

        # Process each point
        prev_direction = None
        for i in range(self._point_count):
            idx = i * 3
            probe.x = self._points[idx]
            probe.y = self._points[idx + 1]
            curr_direction = ProbeDirection(self._points[idx + 2])
            probe.facing = curr_direction
            
            # Quick side checks first (most common failure)
            if not probe.check_left().is_empty or not probe.check_right().is_empty:
                return False, self._crossed_passages[:cross_count]
            
            # Check if corner (direction changes from previous point)
            if i > 0 and curr_direction != prev_direction:
                # Calculate turn direction by comparing current to previous
                turn_right = (curr_direction.value - prev_direction.value) % 8 == 2
                    check_dirs = (
                    ProbeDirection.NORTHEAST, 
                    ProbeDirection.SOUTHEAST
                ) if turn_right else (
                    ProbeDirection.NORTHWEST,
                    ProbeDirection.SOUTHWEST
                )
                
                for direction in check_dirs:
                    result = probe.check_direction(direction)
                    if result.is_passage:
                        self._crossed_passages[cross_count] = result.element_idx
                        cross_count += 1
                        return False, self._crossed_passages[:cross_count]
                    if not result.is_empty:
                        return False, self._crossed_passages[:cross_count]
                        
                continue
            
            # Check endpoints
            if i == 0:
                back = probe.check_backward()
                if not (back.is_room or back.is_passage):
                    return False, self._crossed_passages[:cross_count]
            elif i == len(points) - 1 and not allow_dead_end:
                forward = probe.check_forward()
                if not (forward.is_room or forward.is_passage):
                    return False, self._crossed_passages[:cross_count]
            
            # Check current position
            curr = probe.check_forward()
            
            # Track passage crossings
            if curr.is_passage:
                self._crossed_passages[cross_count] = curr.element_idx
                cross_count += 1
                
                # Efficient passage crossing check
                probe.move_backward()
                for _ in range(3):
                    if not probe.check_forward().is_empty:
                        return False, self._crossed_passages[:cross_count]
                    probe.move_backward()
                    
                idx = i * 3
                probe.x, probe.y = self._points[idx], self._points[idx + 1]  # Reset position
                
                for _ in range(3):
                    probe.move_forward()
                    if not probe.check_forward().is_empty:
                        return False, self._crossed_passages[:cross_count]
                        
            elif curr.is_blocked:
                return False, self._crossed_passages[:cross_count]
                    
        return True, self._crossed_passages[:cross_count]
        
    def _expand_passage_points(self, points: list[tuple[int, int]]) -> int:
        """Expand passage corner points into a sequence of grid points with directions.
        
        Handles corners by:
        1. Not duplicating corner points
        2. Setting correct direction for approaching and leaving corner
        """
        if not points:
            return 0
            
        points_count = 0
        
        # Add first point
        self._points[0] = points[0][0]
        self._points[1] = points[0][1]
        # Direction will be set based on next point
        points_count += 1
        
        # Process each segment
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            
            # Calculate direction for this segment
            dx = x2 - x1
            dy = y2 - y1
            direction = (
                ProbeDirection.EAST if dx > 0 else
                ProbeDirection.WEST if dx < 0 else
                ProbeDirection.SOUTH if dy > 0 else
                ProbeDirection.NORTH
            )
            
            # Set direction for previous point (including first point)
            self._points[(points_count-1) * 3 + 2] = direction.value
            
            # Add all points along segment including end point
            if x1 == x2:  # Vertical
                step = 1 if y2 > y1 else -1
                y = y1 + step  # Start after first point
                while y <= y2 if step > 0 else y >= y2:
                    idx = points_count * 3
                    self._points[idx] = x1
                    self._points[idx + 1] = y
                    self._points[idx + 2] = direction.value
                    points_count += 1
                    y += step
            else:  # Horizontal  
                step = 1 if x2 > x1 else -1
                x = x1 + step  # Start after first point
                while x <= x2 if step > 0 else x >= x2:
                    idx = points_count * 3
                    self._points[idx] = x
                    self._points[idx + 1] = y1
                    self._points[idx + 2] = direction.value
                    points_count += 1
                    x += step
        
        # Set direction for last point based on approach direction
        if points_count > 1:
            self._points[(points_count-1) * 3 + 2] = direction.value
            
        return points_count

    def _check_single_point(self, x: int, y: int, direction: ProbeDirection, 
                           allow_dead_end: bool = False) -> bool:
        """Check if a single point passage is valid.
        
        Single point passages must have:
        - Room/passage behind (no exceptions) 
        - Empty spaces on both sides
        - Room/passage ahead (unless allow_dead_end=True)
        """
        probe = GridProbe(self, x, y, facing=direction)
        
        # Quick checks in order of likelihood
        if not probe.check_left().is_empty or not probe.check_right().is_empty:
            return False
            
        back = probe.check_backward()
        if not (back.is_room or back.is_passage):
            return False
            
        if not allow_dead_end:
            forward = probe.check_forward()
            if not (forward.is_room or forward.is_passage):
                return False
                
        return True

    def _room_to_probe_dir(self, direction: RoomDirection) -> ProbeDirection:
        """Convert RoomDirection to ProbeDirection."""
        direction_map = {
            RoomDirection.NORTH: ProbeDirection.NORTH,
            RoomDirection.SOUTH: ProbeDirection.SOUTH,
            RoomDirection.EAST: ProbeDirection.EAST,
            RoomDirection.WEST: ProbeDirection.WEST
        }
        return direction_map[direction]
        
    def _get_direction_between_points(self, x1: int, y1: int, x2: int, y2: int) -> ProbeDirection:
        """Get the ProbeDirection from point 1 to point 2."""
        dx = x2 - x1
        dy = y2 - y1
        if dx > 0:
            return ProbeDirection.EAST
        elif dx < 0:
            return ProbeDirection.WEST
        elif dy > 0:
            return ProbeDirection.SOUTH
        else:
            return ProbeDirection.NORTH
            
    def _get_probe_for_path_point(self, points: list[tuple[int, int]], index: int, 
                                 curr_x: int, curr_y: int, start_direction: RoomDirection) -> GridProbe:
        """Get a properly oriented probe for a point in the path."""
        if index == 0:
            # First point - use direction to next point
            next_x, next_y = points[index + 1]
            dx = next_x - curr_x
            dy = next_y - curr_y
        else:
            # Other points - use direction from previous point
            prev_x, prev_y = points[index - 1]
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            
        # Convert delta to probe direction
        if dx > 0:
            direction = ProbeDirection.EAST
        elif dx < 0:
            direction = ProbeDirection.WEST
        elif dy > 0:
            direction = ProbeDirection.SOUTH
        else:
            direction = ProbeDirection.NORTH
            
        return GridProbe(self, curr_x, curr_y, facing=direction)
       
    def check_door(self, grid_x: int, grid_y: int) -> bool:
        """Check if a door can be placed at the given grid position.
        
        Args:
            grid_x: Grid x coordinate
            grid_y: Grid y coordinate
            
        Returns:
            True if position is unoccupied, False otherwise
        """
        return not self.is_occupied(grid_x, grid_y)
        
    def draw_debug(self, canvas: 'skia.Canvas') -> None:
        """Draw debug visualization of occupied grid cells."""
            
        # Define colors for different element types
        type_colors = list(range(6))
        type_colors[ElementType.NONE] =     skia.Color(0, 0, 0)       # NONE Light red
        type_colors[ElementType.ROOM] =     skia.Color(255, 200, 200) # ROOM Light red
        type_colors[ElementType.PASSAGE] =  skia.Color(200, 255, 200) # PASSAGE Light green
        type_colors[ElementType.DOOR] =     skia.Color(200, 200, 255) # DOOR Light blue
        type_colors[ElementType.STAIRS] =   skia.Color(255, 255, 200) # STAIRS Light yellow
        type_colors[ElementType.BLOCKED] =  skia.Color(255, 0, 0)     # BLOCKED Light yellow
        
        # Draw each occupied cell
        for grid_y in range(-self._origin_y, self.height - self._origin_y):
            for grid_x in range(-self._origin_x, self.width - self._origin_x):
                if self.is_occupied(grid_x, grid_y):
                    # Get cell info
                    element_type, _, blocked = self.get_cell_info(grid_x, grid_y)
                    
                    # Get color based on element type
                    color = type_colors[element_type]
                    
                    # Use darker alpha for blocked cells
                    alpha = 200 if blocked else 128

                    # Draw semi-transparent rectangle
                    debug_draw_grid_cell(grid_x, grid_y, color, alpha=alpha, blocked=blocked)

                        
