"""Grid-based occupancy tracking for map elements."""

from typing import List, Optional, Set, Tuple, TYPE_CHECKING
from array import array
from enum import IntFlag, auto
from algorithms.shapes import Rectangle, Circle
from constants import CELL_SIZE

if TYPE_CHECKING:
    from options import Options
    from map.mapelement import MapElement
from graphics.conversions import map_to_grid

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
    
    def __init__(self, width: int = 32, height: int = 32) -> None:
        """Initialize an empty occupancy grid with default size."""
        self._grid = array('L', [0] * (width * height))  # Using unsigned long
        self.width = width
        self.height = height
        self._origin_x = width // 2  # Center point
        self._origin_y = height // 2
        
    def _ensure_contains(self, x: int, y: int) -> None:
        """Resize grid if needed to contain the given coordinates."""
        min_x = -self._origin_x
        min_y = -self._origin_y
        max_x = self.width - self._origin_x
        max_y = self.height - self._origin_y
        
        needs_resize = False
        new_width = self.width
        new_height = self.height
        
        # Check if we need to expand
        while x < min_x or x >= max_x:
            new_width *= 2
            needs_resize = True
            min_x = -(new_width // 2)
            max_x = new_width - (new_width // 2)
            
        while y < min_y or y >= max_y:
            new_height *= 2
            needs_resize = True
            min_y = -(new_height // 2)
            max_y = new_height - (new_height // 2)
            
        if needs_resize:
            self._resize(new_width, new_height)
            
    def _resize(self, new_width: int, new_height: int) -> None:
        """Resize the grid, preserving existing contents."""
        new_grid = array('L', [0] * (new_width * new_height))
        new_origin_x = new_width // 2
        new_origin_y = new_height // 2
        
        # Copy existing contents
        for y in range(self.height):
            for x in range(self.width):
                old_idx = y * self.width + x
                old_value = self._grid[old_idx]
                
                # Convert to new coordinates
                new_x = x - self._origin_x + new_origin_x
                new_y = y - self._origin_y + new_origin_y
                new_idx = new_y * new_width + new_x
                
                if 0 <= new_x < new_width and 0 <= new_y < new_height:
                    new_grid[new_idx] = old_value
                    
        self._grid = new_grid
        self.width = new_width
        self.height = new_height
        self._origin_x = new_origin_x
        self._origin_y = new_origin_y
    
    def _to_grid_index(self, x: int, y: int) -> Optional[int]:
        """Convert world coordinates to grid array index."""
        grid_x = x + self._origin_x
        grid_y = y + self._origin_y
        if 0 <= grid_x < self.width and 0 <= grid_y < self.height:
            return grid_y * self.width + grid_x
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
    
    def mark_cell(self, x: int, y: int, element_type: ElementType, 
                  element_idx: int, blocked: bool = False) -> None:
        """Mark a grid cell with element info."""
        self._ensure_contains(x, y)
        idx = self._to_grid_index(x, y)
        if idx is not None:
            self._grid[idx] = self._encode_cell(element_type, element_idx, blocked)
            
    def get_cell_info(self, x: int, y: int) -> Tuple[ElementType, int, bool]:
        """Get element type, index and blocked status at grid position."""
        idx = self._to_grid_index(x, y)
        if idx is not None:
            return self._decode_cell(self._grid[idx])
        return ElementType.NONE, -1, False
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied."""
        idx = self._to_grid_index(x, y)
        return idx is not None and bool(self._grid[idx] & self.OCCUPIED_BIT)
    
    def is_blocked(self, x: int, y: int) -> bool:
        """Check if a grid position is blocked (can't place props)."""
        idx = self._to_grid_index(x, y)
        return idx is not None and bool(self._grid[idx] & self.BLOCKED_MASK)
    
    def get_element_type(self, x: int, y: int) -> ElementType:
        """Get the element type at a grid position."""
        element_type, _, _ = self.get_cell_info(x, y)
        return element_type
    
    def get_element_index(self, x: int, y: int) -> int:
        """Get the element index at a grid position."""
        _, element_idx, _ = self.get_cell_info(x, y)
        return element_idx
    
    def mark_rectangle(self, rect: Rectangle, element_type: ElementType,
                      element_idx: int, options: 'Options',
                      clip_rect: Optional[Rectangle] = None) -> None:
        """Mark all grid positions covered by a rectangle."""
        # Convert rectangle bounds to grid coordinates
        start_x, start_y = map_to_grid(rect.x, rect.y)
        end_x, end_y = map_to_grid(rect.x + rect.width, rect.y + rect.height)
        
        # Round to integer grid positions
        grid_start_x = int(start_x)
        grid_start_y = int(start_y)
        grid_end_x = int(end_x + 0.5)  # Round up
        grid_end_y = int(end_y + 0.5)  # Round up
        
        # Apply clipping if specified
        if clip_rect:
            clip_start_x, clip_start_y = map_to_grid(clip_rect.x, clip_rect.y)
            clip_end_x, clip_end_y = map_to_grid(
                clip_rect.x + clip_rect.width,
                clip_rect.y + clip_rect.height
            )
            grid_start_x = max(grid_start_x, int(clip_start_x))
            grid_start_y = max(grid_start_y, int(clip_start_y))
            grid_end_x = min(grid_end_x, int(clip_end_x + 0.5))
            grid_end_y = min(grid_end_y, int(clip_end_y + 0.5))
        
        # Mark all covered grid positions
        for x in range(grid_start_x, grid_end_x):
            for y in range(grid_start_y, grid_end_y):
                self.mark_cell(x, y, element_type, element_idx)
    
    def mark_circle(self, circle: Circle, element_type: ElementType,
                   element_idx: int, options: 'Options',
                   clip_rect: Optional[Rectangle] = None) -> None:
        """Mark all grid positions covered by a circle."""
        # Convert circle to grid coordinates
        center_x, center_y = map_to_grid(circle.cx, circle.cy)
        radius = circle._inflated_radius / CELL_SIZE
        
        # Calculate grid bounds
        grid_start_x = int(center_x - radius - 0.5)
        grid_start_y = int(center_y - radius - 0.5)
        grid_end_x = int(center_x + radius + 1.5)
        grid_end_y = int(center_y + radius + 1.5)
        
        # Apply clipping if specified
        if clip_rect:
            clip_start_x, clip_start_y = map_to_grid(clip_rect.x, clip_rect.y)
            clip_end_x, clip_end_y = map_to_grid(
                clip_rect.x + clip_rect.width,
                clip_rect.y + clip_rect.height
            )
            grid_start_x = max(grid_start_x, int(clip_start_x))
            grid_start_y = max(grid_start_y, int(clip_start_y))
            grid_end_x = min(grid_end_x, int(clip_end_x + 0.5))
            grid_end_y = min(grid_end_y, int(clip_end_y + 0.5))
        
        # Check each cell in the bounding box
        for x in range(grid_start_x, grid_end_x):
            for y in range(grid_start_y, grid_end_y):
                # Check if any corner is inside the circle
                corners = [
                    (x, y),
                    (x + 1, y),
                    (x, y + 1),
                    (x + 1, y + 1)
                ]
                
                for corner_x, corner_y in corners:
                    dx = corner_x - center_x
                    dy = corner_y - center_y
                    if dx * dx + dy * dy <= radius * radius:
                        self.mark_cell(x, y, element_type, element_idx)
                        break
