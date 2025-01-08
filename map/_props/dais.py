"""Dais (raised platform) prop implementation."""

from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Rectangle
from algorithms.types import Point
from constants import CELL_SIZE
from map._props.prop import Prop, PropType
from map.enums import Layers
from algorithms.rotation import Rotation

# Constants for dais dimensions (2x2 grid cells)
DAIS_WIDTH = CELL_SIZE * 2
DAIS_HEIGHT = CELL_SIZE * 2

DAIS_PROP_TYPE = PropType(
    is_grid_aligned=True,
    boundary_shape=Rectangle(-DAIS_WIDTH/2, -DAIS_HEIGHT/2, DAIS_WIDTH, DAIS_HEIGHT),
    grid_size=(2, 2)
)

class Dais(Prop):
    """A raised platform prop that appears as a large square with decorative border."""
    
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize a dais prop.
        
        Args:
            position: Position in map coordinates (x, y)
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        super().__init__(
            DAIS_PROP_TYPE,
            position,
            rotation=rotation
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers = Layers.PROPS) -> None:
        if layer != Layers.PROPS:
            return
            
        # Draw main platform
        platform = Rectangle(-DAIS_WIDTH/2, -DAIS_HEIGHT/2, DAIS_WIDTH, DAIS_HEIGHT)
        
        # Draw fill
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        platform.draw(canvas, fill_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        platform.draw(canvas, outline_paint)
        
        # Draw decorative inner border
        border_margin = CELL_SIZE * 0.15
        inner_rect = Rectangle(
            -DAIS_WIDTH/2 + border_margin,
            -DAIS_HEIGHT/2 + border_margin,
            DAIS_WIDTH - 2*border_margin,
            DAIS_HEIGHT - 2*border_margin
        )
        inner_rect.draw(canvas, outline_paint)

    @classmethod
    def create(cls, rotation: Rotation = Rotation.ROT_0) -> 'Dais':
        """Create a dais prop at origin with optional rotation."""
        return cls((0, 0), rotation=rotation)
