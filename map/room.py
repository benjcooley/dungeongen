"""Room map element definition."""

from enum import Enum, auto
import math
from typing import List, TYPE_CHECKING, Tuple, Optional
import random
import skia
from map.occupancy import ElementType

from algorithms.math import Point2D
from algorithms.shapes import Rectangle, Circle, Shape
from graphics.conversions import grid_to_map
from map.enums import Layers
from map.mapelement import MapElement
from constants import CELL_SIZE

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

from map.mapelement import MapElement
from graphics.conversions import grid_to_map
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map._props.prop import Prop
    from map.occupancy import OccupancyGrid

class RoomType(Enum):
    """Types of column props."""
    CIRCULAR = auto()
    RECTANGULAR = auto()

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
                room_type: RoomType = RoomType.RECTANGULAR) -> None:
        self._room_type = room_type
        if room_type == RoomType.CIRCULAR:
            if width != height:
                raise ValueError("Circular rooms must have equal width and height.")
            print(f"\nCreating circular room:")
            print(f"  Input dimensions: x={x}, y={y}, width={width}, height={height}")
            shape = Circle(x + width / 2, y + width / 2, width / 2)
            print(f"  Circle params: center=({x + width/2}, {y + width/2}), radius={width/2}")
        else:
            shape = Rectangle(x, y, width, height)
        super().__init__(shape)
        print(f"  Final bounds: x={self.bounds.x}, y={self.bounds.y}, w={self.bounds.width}, h={self.bounds.height}")
    
    @property
    def room_type(self) -> RoomType:
        """Get the room type."""
        return self._room_type

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
        """Draw corner decorations if this is a rectangular room."""
        if not isinstance(self._shape, Rectangle):
            return
            
        # Calculate corner positions with inset
        inset = CELL_SIZE * CORNER_INSET
        left = self._bounds.x + inset
        right = self._bounds.x + self._bounds.width - inset
        top = self._bounds.y + inset
        bottom = self._bounds.y + self._bounds.height - inset
        
        # Create corner points and wall vectors
        from algorithms.math import Point2D
        
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
        super().draw(canvas, layer)

    @classmethod
    def from_grid(cls, \
                grid_x: float, \
                grid_y: float, \
                grid_width: float = 0, \
                grid_height: float = 0, \
                room_type: RoomType = RoomType.RECTANGULAR) -> 'Room':
        """Create a room using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in map units
            grid_height: Height in map units            
            grid_diameter: Diameter in map units
            
        Returns:
            A new circular room instance
        """
        x, y = grid_to_map(grid_x, grid_y)
        w, h = grid_to_map(grid_width, grid_height)
        return cls(x, y, width=w, height=h, room_type=room_type)
        
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        # Always use bounds for grid marking since it's always rectangular
        grid.mark_rectangle(self._bounds, ElementType.ROOM, element_idx, self._options)
