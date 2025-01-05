"""Room map element definition."""

from algorithms.shapes import Rectangle, Circle, Shape
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
    
    def _draw_corner(self, canvas: skia.Canvas, x: float, y: float, flip_x: bool, flip_y: bool) -> None:
        """Draw a single corner decoration.
        
        Args:
            canvas: The canvas to draw on
            x: Corner x position
            y: Corner y position
            flip_x: Whether to flip horizontally
            flip_y: Whether to flip vertically
        """
        # Calculate corner size based on cell size
        size = self._map.options.cell_size * CORNER_SIZE
        
        # Create corner path
        path = skia.Path()
        
        # Calculate direction multipliers
        dx = 1 if flip_x else -1
        dy = 1 if flip_y else -1
        
        # Start at outer corner
        path.moveTo(x + (size * dx), y + (size * dy))
        
        # Draw the L shape going inward
        path.lineTo(x + (size * dx), y)  # Vertical line to top
        path.lineTo(x + (size * 0.3 * dx), y)  # Short horizontal to inner
        path.lineTo(x, y + (size * 0.3 * dy))  # Short vertical to inner
        path.lineTo(x, y + (size * dy))  # Horizontal line to side
        
        # Calculate control points for the curved outer section
        cp1x = x + (size * 0.3 * dx)
        cp1y = y + (size * dy)
        cp2x = x + (size * dx)
        cp2y = y + (size * 0.3 * dy)
        
        # Add curved section back to start
        path.cubicTo(cp1x, cp1y, cp2x, cp2y, x + (size * dx), y + (size * dy))
        
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
        
        # Draw all four corners
        self._draw_corner(canvas, left, top, False, False)      # Top-left
        self._draw_corner(canvas, right, top, True, False)      # Top-right
        self._draw_corner(canvas, left, bottom, False, True)    # Bottom-left
        self._draw_corner(canvas, right, bottom, True, True)    # Bottom-right

    def draw(self, canvas: 'skia.Canvas', layer: Layers = Layers.PROPS) -> None:
        """Draw the room and its props."""
        if layer == Layers.PROPS:
            self.draw_corners(canvas)
        super().draw(canvas, layer)
