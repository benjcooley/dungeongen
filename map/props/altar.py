"""Altar prop implementation."""

from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Rectangle
from algorithms.types import Point
from constants import CELL_SIZE
from graphics.conversions import grid_to_drawing
from map.props.prop import Prop
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Constants for altar dimensions
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface
ALTAR_HEIGHT = CELL_SIZE * 0.7  # Height of altar
ALTAR_INSET = (CELL_SIZE - ALTAR_HEIGHT) / 2  # Calculated inset from cell edges

# Alter position relative to top left of grid cell
ALTAR_GRID_OFFSET_X = 0.3  # Align closer to right side of cell
ALTAR_GRID_OFFSET_Y = 0.5  # Center vertically in cell

class Altar(Prop):
    """An altar prop that appears as a small rectangular table with decorative dots."""
    
    def __init__(self,
                 grid_x: float,
                 grid_y: float,
                 rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize an altar prop.
        
        Args:
            center_x: Center X coordinate in drawing units
            center_y: Center Y coordinate in drawing units
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        position = grid_to_drawing((grid_x, grid_y), self._map.options)
        boundary_shape = Rectangle(
            ALTAR_GRID_OFFSET_X,
            ALTAR_GRID_OFFSET_Y,
            ALTAR_WIDTH,
            ALTAR_HEIGHT
        )
        super().__init__(position, boundary_shape, rotation, grid_size=(1, 1))
    
    @classmethod
    def is_decoration(cls) -> bool:
        """Altars are not decorative - they're major props."""
        return False
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        # Draw fill
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        self.shape.draw(canvas, fill_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        self.shape.draw(canvas, outline_paint)
        
        # Draw decorative dots
        dot_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_outline_color
        )
        dot_radius = CELL_SIZE * 0.05
        center_x = self.bounds.center[0]
        top_y = self.bounds.center[1] - 0.3
        bottom_y = self.bounds.center[1] + 0.3
        canvas.drawCircle(center_x, top_y, dot_radius, dot_paint)
        canvas.drawCircle(center_x, bottom_y, dot_radius, dot_paint)
