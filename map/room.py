"""Room map element definition."""

import math
from typing import List, TYPE_CHECKING, Tuple

import random
import skia

from algorithms.math import Point
from algorithms.shapes import Rectangle, Circle, Shape
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.enums import Layers
from map.mapelement import MapElement

# Constant to make rooms slightly larger to ensure proper passage connections
ROOM_OVERLAP_OFFSET = 4.0  # pixels
# Base corner size as fraction of cell size
CORNER_SIZE = 0.25
# How far corners are inset from room edges
CORNER_INSET = 0.20
# How much to vary the line lengths by (as fraction of base size)
CORNER_LENGTH_VARIATION = 0.3
# Control point scale for curve (relative to corner size)
CURVE_CONTROL_SCALE = 0.5

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
    
    def _draw_corner(self, canvas: skia.Canvas, corner: Point, left: Point, right: Point) -> None:
        """Draw a single corner decoration.
        
        Args:
            canvas: The canvas to draw on
            corner: Corner position
            left: Direction vector parallel to left wall (from corner's perspective)
            right: Direction vector parallel to right wall (from corner's perspective)
        """
        # Calculate base corner size
        base_size = self._map.options.cell_size * CORNER_SIZE
        
        # Calculate random variations for line lengths
        variation_left = 1.0 + (random.random() * CORNER_LENGTH_VARIATION)
        variation_right = 1.0 + (random.random() * CORNER_LENGTH_VARIATION)
        
        # Scale the normalized vectors by the varied sizes
        left_norm = left * (base_size * variation_left)
        right_norm = right * (base_size * variation_right)
        
        # Create corner path
        path = skia.Path()
        path.moveTo(corner.x, corner.y)
        
        # Draw first straight line along left wall
        p1 = corner + left_norm
        path.lineTo(p1.x, p1.y)
        
        # Draw curved line to point along right wall
        p2 = corner + right_norm
        cp1 = p1 + right_norm * CURVE_CONTROL_SCALE
        cp2 = p2 + left_norm * CURVE_CONTROL_SCALE
        path.cubicTo(cp1.x, cp1.y, cp2.x, cp2.y, p2.x, p2.y)
        
        # Draw straight line back to corner
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
