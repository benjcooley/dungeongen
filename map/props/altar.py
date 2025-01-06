"""Altar prop implementation."""

from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Rectangle
from algorithms.types import Point
from constants import CELL_SIZE
from map.props.prop import Prop, PropType
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Constants for altar dimensions
ALTAR_X = CELL_SIZE * 0.3  # Align closer to right side of cell
ALTAR_Y = CELL_SIZE * 0.5  # Center vertically in cell
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface
ALTAR_HEIGHT = CELL_SIZE * 0.7  # Height of altar

ALTAR_PROP_TYPE = PropType(
    is_grid_aligned=True,
    boundary_shape=Rectangle(ALTAR_X, ALTAR_Y, ALTAR_WIDTH, ALTAR_HEIGHT),
    grid_size=(1, 1)
    )

class Altar(Prop):
    """An altar prop that appears as a small rectangular table with decorative dots."""
    
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize an altar prop.
        
        Args:
            position: Position in map coordinates (x, y)
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        super().__init__(
            ALTAR_PROP_TYPE,
            position,
            ALTAR_PROP_TYPE.boundary_shape,
            rotation=rotation,
            grid_size=(1, 1)
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:

        # Draw right facing version (this is moved, rotated by draw() method)

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
        
        # Draw candle dots
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

    # Overridable class methods
    
    @classmethod
    def is_grid_aligned(cls) -> bool:
        """Altars are not decorative - they're major props."""
        return False

    @classmethod
    def boundary_shape(cls) -> Rectangle:
        """Get the boundary shape for this prop."""
        return Rectangle(
            ALTAR_X,
            ALTAR_Y,
            ALTAR_WIDTH,
            ALTAR_HEIGHT
        )

    @classmethod
    def grid_size(cls) -> Point:
        """Get the size of this prop in grid units."""
        return Point(1, 1)
    @classmethod
    def create(cls) -> 'Altar':
        """Create an altar prop at origin."""
        return cls((0, 0))
