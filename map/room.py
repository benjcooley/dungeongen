"""Room map element definition."""

from algorithms.shapes import Rectangle, Circle, Shape
from algorithms.math import Point
from typing import List, TYPE_CHECKING, Tuple
import skia
import math

# Constant to make rooms slightly larger to ensure proper passage connections
ROOM_OVERLAP_OFFSET = 4.0  # pixels
# Corner size as fraction of cell size
CORNER_SIZE = 0.25  # Increased size for more prominent corners
# How far corners are inset from room edges
CORNER_INSET = 0.20  # Increased inset to match example

from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.props.prop import Prop

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        # Create slightly larger rectangle to ensure proper passage connections
        shape = Rectangle(
            x - ROOM_OVERLAP_OFFSET/2,
            y - ROOM_OVERLAP_OFFSET/2,
            width + ROOM_OVERLAP_OFFSET,
            height + ROOM_OVERLAP_OFFSET
        )
        super().__init__(shape=shape, map_=map_)
    
    def _draw_corner(self, canvas: skia.Canvas, corner: Point, wall1: Point, wall2: Point) -> None:
        """Draw a single corner decoration.
        
        Args:
            canvas: The canvas to draw on
            corner: Corner position
            wall1: First wall direction vector
            wall2: Second wall direction vector
        """
        # Calculate corner size based on cell size with variation
        base_size = self._map.options.cell_size * CORNER_SIZE
        var_size = base_size * (1 + (0.1 * (math.sin(corner.x * corner.y) * 0.5 + 0.5)))
        
        # Normalize wall vectors and scale to size
        wall1_norm = wall1.normalized() * var_size
        wall2_norm = wall2.normalized() * var_size
        
        # Create corner path
        path = skia.Path()
        path.moveTo(corner.x, corner.y)
        
        # Draw straight edges along walls
        p1 = corner + wall1_norm
        p2 = p1 + wall2_norm
        
        path.lineTo(p1.x, p1.y)
        path.lineTo(p2.x, p2.y)
        path.lineTo(corner.x + wall2_norm.x, corner.y + wall2_norm.y)
        
        # Calculate control points for curved inset
        cp1 = corner + wall1_norm * 0.8 + wall2_norm * 0.2
        cp2 = corner + wall1_norm * 0.2 + wall2_norm * 0.8
        
        # Add curved section back to start
        path.cubicTo(cp1.x, cp1.y, cp2.x, cp2.y, corner.x, corner.y)
        
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
        inset = self._map.options.cell_size * CORNER_INSET
        left = self._bounds.x + inset
        right = self._bounds.x + self._bounds.width - inset
        top = self._bounds.y + inset
        bottom = self._bounds.y + self._bounds.height - inset
        
        # Create corner points and wall vectors
        from algorithms.math import Point
        
        # Corner positions
        tl = Point(left, top)
        tr = Point(right, top)
        bl = Point(left, bottom)
        br = Point(right, bottom)
        
        # Wall direction vectors
        right_vec = Point(1, 0)
        down_vec = Point(0, 1)
        
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
