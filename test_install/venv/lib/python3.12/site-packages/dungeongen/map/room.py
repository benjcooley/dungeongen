"""Room map element definition."""

from dataclasses import dataclass
from enum import Enum, auto
import math
from typing import List, TYPE_CHECKING, Tuple, Optional
import random
from dungeongen.layout.spatial import Point
import skia
from dungeongen.map.occupancy import ElementType
from dungeongen.logging_config import logger, LogTags
from dungeongen.logging_config import logger, LogTags

from dungeongen.graphics.math import Point2D
from dungeongen.graphics.shapes import Rectangle, Circle, Shape
from dungeongen.graphics.conversions import grid_to_map, map_to_grid_rect
from dungeongen.map.enums import Layers, RoomDirection
from dungeongen.map.mapelement import MapElement
from dungeongen.constants import CELL_SIZE

# Base corner size as fraction of cell size
CORNER_SIZE = 0.35
# How far corners are inset from room edges
CORNER_INSET = 0.12
# Minimum corner length as percentage of base size
MIN_CORNER_LENGTH = 0.5
# Maximum corner length as percentage of base size 
MAX_CORNER_LENGTH = 2.0
# Control point scale for curve (relative to corner size)
CURVE_CONTROL_SCALE = 0.8  # Increased from 0.5 for more concavity

from dungeongen.map.mapelement import MapElement
from dungeongen.graphics.conversions import grid_to_map
from dungeongen.map.enums import Layers

if TYPE_CHECKING:
    from dungeongen.map.map import Map
    from dungeongen.options import Options
    from dungeongen.map._props.prop import Prop
    from dungeongen.map.occupancy import OccupancyGrid

class RoomType(Enum):
    """Types of column props."""
    CIRCULAR = auto()
    RECTANGULAR = auto()

@dataclass
class RoomShape:
    """Defines the shape and dimensions of a self."""
    room_type: RoomType
    breadth: int  # Width relative to forward direction
    depth: int    # Length relative to forward direction
    breadth_offset: float  # Offset for alternating room placement

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, \
                x: float, \
                y: float, \
                width: float = 0, \
                height: float = 0, \
                room_type: RoomType = RoomType.RECTANGULAR, \
                number: int = 0) -> None:
        self._room_type = room_type
        self._number = number  # Room number for display
        if room_type == RoomType.CIRCULAR:
            if width != height:
                raise ValueError("Circular rooms must have equal width and height.")
            logger.debug(LogTags.GENERATION,
                f"\nCreating circular room:\n"
                f"  Input dimensions: x={x}, y={y}, width={width}, height={height}")
            shape = Circle(x + width / 2, y + width / 2, width / 2)
            logger.debug(LogTags.GENERATION,
                f"  Circle params: center=({x + width/2}, {y + width/2}), radius={width/2}")
        else:
            shape = Rectangle(x, y, width, height)
        super().__init__(shape)
        logger.debug(LogTags.GENERATION,
            f"  Final bounds: x={self.bounds.x}, y={self.bounds.y}, w={self.bounds.width}, h={self.bounds.height}")
    
    @property
    def room_type(self) -> RoomType:
        """Get the room type."""
        return self._room_type
    
    @property
    def number(self) -> int:
        """Get the room number for display."""
        return self._number
    
    @number.setter
    def number(self, value: int) -> None:
        """Set the room number for display."""
        self._number = value

    def _draw_corner(self, canvas: skia.Canvas, corner: Point2D, left: Point2D, right: Point2D) -> None:
        """Draw a single corner decoration.
        
        Args:
            canvas: The canvas to draw on
            corner: Corner position
            left: Direction vector parallel to left wall (from corner's perspective)
            right: Direction vector parallel to right wall (from corner's perspective)
        """
        # Calculate base corner size
        base_size = CELL_SIZE * CORNER_SIZE
        
        # Calculate end points with constrained random lengths
        length1 = base_size * (MIN_CORNER_LENGTH + random.random() * (MAX_CORNER_LENGTH - MIN_CORNER_LENGTH))
        length2 = base_size * (MIN_CORNER_LENGTH + random.random() * (MAX_CORNER_LENGTH - MIN_CORNER_LENGTH))
        p1 = corner + left * length1
        p2 = corner + right * length2
        
        # Create and draw the corner path
        path = skia.Path()
        path.moveTo(corner.x, corner.y)
        path.lineTo(p1.x, p1.y)
        
        # Draw curved line between points with smooth inward curve
        # Control points are placed along the straight lines at a fraction of their length
        cp1 = p1 + (corner - p1) * CURVE_CONTROL_SCALE
        cp2 = p2 + (corner - p2) * CURVE_CONTROL_SCALE
        path.cubicTo(cp1.x, cp1.y, cp2.x, cp2.y, p2.x, p2.y)
        
        # Close the path
        path.lineTo(corner.x, corner.y)
        
        # Fill the corner with black
        corner_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=0xFF000000  # Black
        )
        canvas.drawPath(path, corner_paint)

    def draw_corners(self, canvas: skia.Canvas) -> None:
        """Draw corner decorations if this is a rectangular self."""
        if not isinstance(self._shape, Rectangle):
            return
            
        # Calculate corner positions with inset
        inset = CELL_SIZE * CORNER_INSET
        left = self._bounds.x + inset
        right = self._bounds.x + self._bounds.width - inset
        top = self._bounds.y + inset
        bottom = self._bounds.y + self._bounds.height - inset
        
        # Create corner points and wall vectors
        from dungeongen.graphics.math import Point2D
        
        # Corner positions
        tl = Point2D(left, top)
        tr = Point2D(right, top)
        bl = Point2D(left, bottom)
        br = Point2D(right, bottom)
        
        # Wall direction vectors
        right_vec = Point2D(1, 0)
        down_vec = Point2D(0, 1)
        
        # Draw all four corners with appropriate wall vectors
        self._draw_corner(canvas, tl, right_vec, down_vec)      # Top-left
        self._draw_corner(canvas, tr, -right_vec, down_vec)     # Top-right  
        self._draw_corner(canvas, bl, right_vec, -down_vec)     # Bottom-left
        self._draw_corner(canvas, br, -right_vec, -down_vec)    # Bottom-right

    def draw(self, canvas: 'skia.Canvas', layer: Layers = Layers.PROPS) -> None:
        """Draw the room and its props."""
        if layer == Layers.PROPS:
            self.draw_corners(canvas)
        elif layer == Layers.TEXT:
            self._draw_number(canvas)
        super().draw(canvas, layer)
    
    # Class-level font cache
    _number_typeface: 'skia.Typeface' = None
    
    @classmethod
    def _get_number_typeface(cls) -> 'skia.Typeface':
        """Get or load the Roboto Condensed typeface (weight 400)."""
        if cls._number_typeface is None:
            import os
            # Load from fonts directory
            font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fonts')
            font_path = os.path.join(font_dir, 'RobotoCondensed-Regular.ttf')
            
            if not os.path.exists(font_path):
                raise FileNotFoundError(f"Font file not found: {font_path}")
            
            cls._number_typeface = skia.Typeface.MakeFromFile(font_path)
            
            if cls._number_typeface is None:
                raise RuntimeError(f"Failed to load font from: {font_path}")
            
            print(f"[Room] Loaded font: {cls._number_typeface.getFamilyName()} from {font_path}")
        return cls._number_typeface
    
    def _draw_number(self, canvas: 'skia.Canvas') -> None:
        """Draw the room number in the center of the room as a path (for SVG compatibility)."""
        if self._number <= 0:
            return
        
        # Get room center
        center_x = self._bounds.x + self._bounds.width / 2
        center_y = self._bounds.y + self._bounds.height / 2
        
        # Fixed font size of 54pt (2/3 larger than 32)
        font_size = 54
        
        # Create font - Roboto Condensed (loaded from file)
        typeface = self._get_number_typeface()
        font = skia.Font(typeface, font_size)
        
        # Create paint for text path
        text_paint = skia.Paint(
            Color=skia.ColorSetARGB(180, 0, 0, 0),  # Semi-transparent black
            AntiAlias=True,
            Style=skia.Paint.kFill_Style
        )
        
        text = str(self._number)
        
        # Convert text to path for SVG embedding
        path = skia.Path()
        glyphs = font.textToGlyphs(text)
        widths = font.getWidths(glyphs)
        
        # Calculate total width for centering
        total_width = sum(widths)
        x = center_x - total_width / 2
        y = center_y + font_size / 3  # Approximate vertical centering
        
        # Add each glyph path
        current_x = x
        for i, glyph in enumerate(glyphs):
            glyph_path = font.getPath(glyph)
            if glyph_path:
                glyph_path.offset(current_x, y)
                path.addPath(glyph_path)
            current_x += widths[i]
        
        canvas.drawPath(path, text_paint)

    @classmethod
    def from_grid(cls, \
                grid_x: float, \
                grid_y: float, \
                grid_width: float = 0, \
                grid_height: float = 0, \
                room_type: RoomType = RoomType.RECTANGULAR, \
                number: int = 0) -> 'Room':
        """Create a room using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in map units
            grid_height: Height in map units            
            room_type: Type of room (rectangular or circular)
            number: Room number for display
            
        Returns:
            A new room instance
        """
        x, y = grid_to_map(grid_x, grid_y)
        w, h = grid_to_map(grid_width, grid_height)
        return cls(x, y, width=w, height=h, room_type=room_type, number=number)
        
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        grid.mark_rectangle(self._shape, ElementType.ROOM, element_idx) #type: ignore

    def get_exit(self, direction: RoomDirection, wall_pos: float = 0.5, align_to: Optional[Point] = None) -> Tuple[int, int]:
        """Get a grid position for exiting this room in the given direction.
        
        Args:
            direction: Which side of the room to exit from
            wall_pos: Position along the wall to exit from (0.0 to 1.0)
            align_to: Optional coordinate to snap to. For vertical passages (NORTH/SOUTH),
                    uses the x-coordinate. For horizontal passages (EAST/WEST), uses
                    the y-coordinate.
            
        Returns:
            Tuple of (grid_x, grid_y) for the exit point one cell outside the room
        """
        # Get room bounds in grid coordinates
        grid_x = int(self.bounds.x / CELL_SIZE)
        grid_y = int(self.bounds.y / CELL_SIZE)
        grid_width = int(self.bounds.width / CELL_SIZE)
        grid_height = int(self.bounds.height / CELL_SIZE)
        
        logger.debug(LogTags.ARRANGEMENT, 
            f"\nCalculating exit position:\n"
            f"  Room bounds: x={self.bounds.x}, y={self.bounds.y}, w={self.bounds.width}, h={self.bounds.height}\n"
            f"  Grid bounds: x={grid_x}, y={grid_y}, w={grid_width}, h={grid_height}")

        # For circular rooms, always exit from center
        if self.room_type == RoomType.CIRCULAR:
            wall_pos = 0.5

        # Calculate exit point along the wall
        if direction == RoomDirection.NORTH:
            x = grid_x + int((grid_width - 1) * wall_pos)
            y = grid_y - 1
        elif direction == RoomDirection.SOUTH:
            x = grid_x + int((grid_width - 1) * wall_pos)
            y = grid_y + grid_height
        elif direction == RoomDirection.EAST:
            x = grid_x + grid_width
            y = grid_y + int((grid_height - 1) * wall_pos)
        else:  # WEST
            x = grid_x - 1
            y = grid_y + int((grid_height - 1) * wall_pos)

        # If we have an align_to point, snap to its coordinate based on passage direction
        if align_to is not None:
            if direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
                x = align_to[0]  # Vertical passages snap to x coordinate
            else:  # EAST, WEST
                y = align_to[1]  # Horizontal passages snap to y coordinate
                
        return (x, y)