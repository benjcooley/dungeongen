"""Room map element definition."""

from algorithms.shapes import Rectangle, Circle, Shape
from typing import List, TYPE_CHECKING, Tuple
import skia
import math

# Constant to make rooms slightly larger to ensure proper passage connections
ROOM_OVERLAP_OFFSET = 4.0  # pixels
# Corner size as fraction of cell size
CORNER_SIZE = 0.1
# How far corners are inset from room edges
CORNER_INSET = 0.1
# Control point scale factor for bezier curve (higher = more curved)
CORNER_CURVE_FACTOR = 0.6

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
        
        # Start at inner corner
        path.moveTo(x, y)
        
        # Calculate end points of the two straight lines
        dx = size * (1 if flip_x else -1)
        dy = size * (1 if flip_y else -1)
        
        # Add first line
        x1 = x + dx
        path.lineTo(x1, y)
        
        # Add second line
        y1 = y + dy
        path.lineTo(x, y1)
        
        # Calculate control point for bezier curve
        # Move control point inward by scaling both coordinates
        control_x = x + (dx * CORNER_CURVE_FACTOR)
        control_y = y + (dy * CORNER_CURVE_FACTOR)
        
        # Add curved section back to start
        path.quadTo(control_x, control_y, x, y)
        
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
