"""Grid-based occupancy tracking for map elements."""

from typing import List, Optional, Set, Tuple, TYPE_CHECKING
from array import array
from enum import IntFlag, auto
import math
import skia
from algorithms.shapes import Rectangle, Circle
from constants import CELL_SIZE

if TYPE_CHECKING:
    from options import Options
    from map.mapelement import MapElement
from graphics.conversions import map_to_grid, map_rect_to_grid_points

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
            
        # Convert rectangle bounds to grid coordinates
        p1, p2 = map_rect_to_grid_points(shape.x, shape.y, shape.width, shape.height)
        
        # Create rectangles for bounds checking
        grid_rect = Rectangle(p1[0], p1[1], p2[0] - p1[0] + 1, p2[1] - p1[1] + 1)
        bounds_rect = Rectangle(-self._origin_x, -self._origin_y, 
                             self.width - self._origin_x, self.height - self._origin_y)
        
        # Get clipped rectangle
        clipped_rect = grid_rect.intersection(bounds_rect)
        if clip_rect:
            # Convert clip rect to grid coordinates
            clip_grid_x1, clip_grid_y1 = map_to_grid(clip_rect.x, clip_rect.y)
            clip_grid_x2, clip_grid_y2 = map_to_grid(clip_rect.x + clip_rect.width - 0.001, 
                                                    clip_rect.y + clip_rect.height - 0.001)
            clip_rect = Rectangle(clip_grid_x1, clip_grid_y1,
                                clip_grid_x2 - clip_grid_x1 + 1,
                                clip_grid_y2 - clip_grid_y1 + 1)
            clipped_rect = clipped_rect.intersection(clip_rect)

        # Early out if no valid intersection
        if not clipped_rect.is_valid:
            return

        # Fill the clipped rectangle
        x1 = int(clipped_rect.x)
        y1 = int(clipped_rect.y)
        x2 = int(clipped_rect.x + clipped_rect.width)
        y2 = int(clipped_rect.y + clipped_rect.height)
        
        for x in range(x1, x2):
            for y in range(y1, y2):
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
        # Get circle bounds in grid coordinates
        grid_x1 = math.floor((circle.cx - circle.radius) / CELL_SIZE)
        grid_y1 = math.floor((circle.cy - circle.radius) / CELL_SIZE)
        grid_x2 = math.ceil((circle.cx + circle.radius) / CELL_SIZE)
        grid_y2 = math.ceil((circle.cy + circle.radius) / CELL_SIZE)
        
        # Clip to grid bounds
        grid_x1 = max(grid_x1, -self._origin_x)
        grid_y1 = max(grid_y1, -self._origin_y)
        grid_x2 = min(grid_x2, self.width - self._origin_x)
        grid_y2 = min(grid_y2, self.height - self._origin_y)
        
        # Apply clip rect if specified
        if clip_rect:
            clip_x1 = math.floor(clip_rect.x / CELL_SIZE)
            clip_y1 = math.floor(clip_rect.y / CELL_SIZE)
            clip_x2 = math.ceil((clip_rect.x + clip_rect.width) / CELL_SIZE)
            clip_y2 = math.ceil((clip_rect.y + clip_rect.height) / CELL_SIZE)
            
            grid_x1 = max(grid_x1, clip_x1)
            grid_y1 = max(grid_y1, clip_y1)
            grid_x2 = min(grid_x2, clip_x2)
            grid_y2 = min(grid_y2, clip_y2)
            
        # Early out if no valid region
        if grid_x2 <= grid_x1 or grid_y2 <= grid_y1:
            return
            
        # Test each cell center against circle
        radius_sq = (circle.radius / CELL_SIZE) * (circle.radius / CELL_SIZE)
        center_x = circle.cx / CELL_SIZE
        center_y = circle.cy / CELL_SIZE
        
        for x in range(grid_x1, grid_x2):
            for y in range(grid_y1, grid_y2):
                dx = (x + 0.5) - center_x
                dy = (y + 0.5) - center_y
                if dx * dx + dy * dy <= radius_sq:
                    self.mark_cell(x, y, element_type, element_idx)
        
    def draw_debug(self, canvas: 'skia.Canvas') -> None:
        """Draw debug visualization of occupied grid cells."""
        import skia
        from debug_draw import debug_draw_init, debug_draw_grid_cell
        
        # Initialize debug drawing
        debug_draw_init(canvas)
        
        # Define colors for different element types
        type_colors = {
            ElementType.ROOM: skia.Color(255, 200, 200),     # Light red
            ElementType.PASSAGE: skia.Color(200, 255, 200),  # Light green
            ElementType.DOOR: skia.Color(200, 200, 255),     # Light blue
            ElementType.STAIRS: skia.Color(255, 255, 200),   # Light yellow
        }
        
        # Draw each occupied cell
        for grid_y in range(-self._origin_y, self.height - self._origin_y):
            for grid_x in range(-self._origin_x, self.width - self._origin_x):
                if self.is_occupied(grid_x, grid_y):
                    # Get cell info
                    element_type, _, blocked = self.get_cell_info(grid_x, grid_y)
                    
                    # Get fill color based on element type
                    fill_color = type_colors.get(element_type, skia.Color(220, 220, 220))
                    
                    # Draw cell with red outline if blocked
                    outline_color = skia.Color(255, 0, 0) if blocked else None
                    debug_draw_grid_cell(grid_x, grid_y, fill_color, outline_color, blocked)
