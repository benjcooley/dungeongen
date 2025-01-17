"""Grid-based occupancy tracking for map elements."""

from typing import List, Optional, Set, Tuple, TYPE_CHECKING
from array import array
from enum import IntFlag, auto
import skia
from logging_config import logger, LogTags
from graphics.shapes import Rectangle, Circle
from constants import CELL_SIZE
from graphics.conversions import map_to_grid, map_rect_to_grid_points, map_to_grid_rect, grid_to_map
from map._arrange.arrange_enums import RoomDirection
from options import Options
from debug_config import debug_draw, HatchPattern

if TYPE_CHECKING:
    from map.mapelement import MapElement

class ElementType(IntFlag):
    """Bit flags for element types in occupancy grid."""
    NONE = 0
    ROOM = auto()
    PASSAGE = auto()
    DOOR = auto()
    STAIRS = auto()
    BLOCKED = auto()  # For doorway areas that can't have props

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
    
    def __init__(self, width: int, height: int) -> None:
        """Initialize an empty occupancy grid with default size."""
        self._grid = array('L', [0] * (width * height))  # Using unsigned long
        self.width = width
        self.height = height
        self._origin_x = width // 2  # Center point
        self._origin_y = height // 2
        
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

    def check_passage(self, grid_rect: Rectangle, direction: RoomDirection, allow_crossing: bool = True) -> tuple[bool, list[int]]:
        """Check if a passage can be placed, allowing crossing other passages.
        
        The check area is inflated by 1 grid cell perpendicular to the passage direction
        to ensure proper spacing between parallel passages.
        
        Args:
            rect: Rectangle defining passage bounds in map coordinates
            direction: Direction of passage growth
            allow_crossing: True to allow crossing other passages
            
        Returns:
            Tuple of (is_valid, crossed_passage_indices)
            where is_valid is True if area is clear of rooms and blocked cells,
            and crossed_passage_indices is a list of indices of crossed passages
        """
        # Check the grid points at each end of the passage first
        p1: Tuple[int, int]
        p2: Tuple[int, int]
        if direction == RoomDirection.NORTH or direction == RoomDirection.SOUTH:
            p1 = (grid_rect.x, int(grid_rect.y - 1))
            p2 = (grid_rect.x, int(grid_rect.y + grid_rect.height))
        else:
            p1 = (int(grid_rect.x - 1), grid_rect.y)
            p2 = (int(grid_rect.x + grid_rect.width), grid_rect.y)
            
        # Check both end points connect to rooms/passages
        for p in (p1, p2):
            idx = self._to_grid_index(p[0], p[1])
            if idx is None:
                return False, []
            element_type, _, blocked = self._decode_cell(self._grid[idx])
            if blocked or (element_type != ElementType.NONE and element_type != ElementType.ROOM and element_type != ElementType.PASSAGE):
                return False, []
        
        # Manually inflate perpendicular to direction
        if direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
            # Inflate horizontally by 1 grid cell on each side
            grid_rect = Rectangle(
                grid_rect.x - 1,  # Move left edge out
                grid_rect.y,      # Keep top edge
                grid_rect.width + 2,  # Add 2 to width (1 each side)
                grid_rect.height  # Keep height
            )
        else:
            # Inflate vertically by 1 grid cell on each side
            grid_rect = Rectangle(
                grid_rect.x,      # Keep left edge
                grid_rect.y - 1,  # Move top edge up
                grid_rect.width,  # Keep width
                grid_rect.height + 2  # Add 2 to height (1 each side)
            )
            
        crossed_passages = []
        
        # Check each cell in inflated grid coordinates
        for grid_x in range(int(grid_rect.x), int(grid_rect.x + grid_rect.width)):
            for grid_y in range(int(grid_rect.y), int(grid_rect.y + grid_rect.height)):
                idx = self._to_grid_index(grid_x, grid_y)
                if idx is not None:
                    element_type, element_idx, blocked = self._decode_cell(self._grid[idx])
                    if blocked:
                        return False, []
                    if element_type != ElementType.NONE:
                        if not allow_crossing or element_type != ElementType.PASSAGE:
                            return False, []
                    if element_type == ElementType.PASSAGE and element_idx not in crossed_passages:
                        crossed_passages.append(element_idx)
                        
        return True, crossed_passages

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
        type_colors = list(range(5))
        type_colors[ElementType.NONE] =     skia.Color(0, 0, 0)       # NONE Light red
        type_colors[ElementType.ROOM] =     skia.Color(255, 200, 200) # ROOM Light red
        type_colors[ElementType.PASSAGE] =  skia.Color(200, 255, 200) # PASSAGE Light green
        type_colors[ElementType.DOOR] =     skia.Color(200, 200, 255) # DOOR Light blue
        type_colors[ElementType.STAIRS] =   skia.Color(255, 255, 200) # STAIRS Light yellow
        type_colors[ElementType.BLOCKED] =  skia.Color(255, 0, 0),    # BLOCKED Light yellow
        
        # Save current pattern and set to CROSS for blocked cells
        saved_pattern = debug_draw.hatch_pattern
        
        # Draw each occupied cell
        for grid_y in range(-self._origin_y, self.height - self._origin_y):
            for grid_x in range(-self._origin_x, self.width - self._origin_x):
                if self.is_occupied(grid_x, grid_y):
                    # Get cell info
                    element_type, _, blocked = self.get_cell_info(grid_x, grid_y)
                    
                    # Get color based on element type
                    color = type_colors.get(element_type, skia.Color(120, 120, 120))
                    
                    # Use cross pattern for blocked cells
                    if blocked:
                        hatch_pattern = HatchPattern.CROSS
                    else:
                        hatch_pattern = HatchPattern.DIAGONAL

                    # Draw hatched rectangle
                    debug_draw.debug_draw_grid_cell(grid_x, grid_y, color, hatch_pattern=hatch_pattern)
        
        # Restore original pattern
        debug_draw.hatch_pattern = saved_pattern
                        
