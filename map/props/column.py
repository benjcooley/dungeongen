"""Column prop implementation."""

from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Circle, Rectangle
from algorithms.types import Point
from constants import CELL_SIZE
from map.props.prop import Prop, PropType
from map.enums import Layers
from map.props.rotation import Rotation

COLUMN_RADIUS = CELL_SIZE * 0.3
COLUMN_PROP_TYPE = PropType(
    is_grid_aligned=True,
    boundary_shape=Circle(0, 0, COLUMN_RADIUS),
    grid_size=(1, 1)
)

class Column(Prop):
    """A circular column prop."""
    
    def __init__(self, position: Point) -> None:
        """Initialize a column prop.
        
        Args:
            position: Position in map coordinates (x, y)
        """
        super().__init__(
            COLUMN_PROP_TYPE,
            position
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers = Layers.PROPS) -> None:
        if layer != Layers.PROPS:
            return
            
        circle = Circle(0, 0, COLUMN_RADIUS)
        
        # Draw fill
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        circle.draw(canvas, fill_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        circle.draw(canvas, outline_paint)

    @classmethod
    def create(cls) -> 'Column':
        """Create a column prop at origin."""
        return cls((0, 0))
