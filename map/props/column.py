"""Column prop implementation."""

from enum import Enum, auto
from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Circle, Rectangle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from map.props.prop import Prop, PropType
from map.enums import Layers
from map.props.rotation import Rotation

class ColumnType(Enum):
    """Types of column props."""
    ROUND = auto()
    SQUARE = auto()

# Size is 1/4 of a cell
COLUMN_SIZE = CELL_SIZE / 4

# Prop types for each column variant
ROUND_COLUMN_TYPE = PropType(
    boundary_shape=Circle(0, 0, COLUMN_SIZE/2),
    grid_size=(1, 1)
)

SQUARE_COLUMN_TYPE = PropType(
    boundary_shape=Rectangle(-COLUMN_SIZE/2, -COLUMN_SIZE/2, COLUMN_SIZE, COLUMN_SIZE),
    grid_size=(1, 1)
)

class Column(Prop):
    """A column prop that can be either round or square."""
    
    def __init__(self, position: Point, column_type: ColumnType = ColumnType.ROUND) -> None:
        """Initialize a column prop.
        
        Args:
            position: Position in map coordinates (x, y)
            column_type: Type of column (round or square)
        """
        self._column_type = column_type
        prop_type = ROUND_COLUMN_TYPE if column_type == ColumnType.ROUND else SQUARE_COLUMN_TYPE
        super().__init__(prop_type, position)
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers = Layers.PROPS) -> None:
        if layer not in (Layers.PROPS, Layers.SHADOW):
            return
            
        # Get shape based on column type
        if self._column_type == ColumnType.ROUND:
            shape = Circle(0, 0, COLUMN_SIZE/2)
        else:
            shape = Rectangle(-COLUMN_SIZE/2, -COLUMN_SIZE/2, COLUMN_SIZE, COLUMN_SIZE)
            
        if layer == Layers.SHADOW:
            # Draw slightly inflated shadow shape
            shadow_shape = shape.inflated(self._map.options.border_width * 0.5)
            canvas.save()
            canvas.translate(
                self._map.options.room_shadow_offset_x,
                self._map.options.room_shadow_offset_y
            )
            shadow_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.room_shadow_color
            )
            shadow_shape.draw(canvas, shadow_paint)
            canvas.restore()
        else:
            # Draw fill
            fill_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.room_shadow_color  # Use room shadow color for lighter gray
            )
            shape.draw(canvas, fill_paint)
            
            # Draw outline
            outline_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=self._map.options.border_width,
                Color=self._map.options.border_color
            )
            shape.draw(canvas, outline_paint)

    @classmethod
    def create_round(cls) -> 'Column':
        """Create a round column prop at origin."""
        return cls((0, 0), ColumnType.ROUND)
        
    @classmethod
    def create_square(cls) -> 'Column':
        """Create a square column prop at origin."""
        return cls((0, 0), ColumnType.SQUARE)
