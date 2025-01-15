"""Altar prop implementation."""

from typing import TYPE_CHECKING
import skia

from graphics.shapes import Rectangle
from graphics.aliases import Point
from constants import CELL_SIZE
from map._props.prop import Prop, PropType
from map.enums import Layers
from graphics.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Constants for grid-based positioning
GRID_ORIGIN_X = -0.5  # Grid origin X offset
GRID_ORIGIN_Y = -0.5  # Grid origin Y offset

# Constants for altar dimensions
ALTAR_X = CELL_SIZE * (GRID_ORIGIN_X + 0.15)  # Small margin from left edge
ALTAR_Y = CELL_SIZE * (GRID_ORIGIN_Y + 0.15)  # Small margin from top edge
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface
ALTAR_HEIGHT = CELL_SIZE * 0.7  # Height of altar, leaving equal margins top/bottom

ALTAR_PROP_TYPE = PropType(
    is_grid_aligned=True,
    is_wall_aligned=True,
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
            rotation=rotation
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: 'Layers' = Layers.PROPS) -> None:
        if layer != Layers.PROPS:
            return
            
        # Draw right facing version (this is moved, rotated by draw() method)
        rect = self.prop_type.boundary_shape #type: Rectangle

        # Draw fill
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        rect.draw(canvas, fill_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        rect.draw(canvas, outline_paint)
        
        # Draw candle dots
        dot_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_outline_color
        )
        dot_radius = CELL_SIZE * 0.04
        # Draw dots relative to bounds
        center_x = rect.center[0] 
        center_y = rect.center[1]
        dot_offset = ALTAR_HEIGHT * 0.25  # 25% up from center
        canvas.drawCircle(center_x, center_y - dot_offset, dot_radius, dot_paint)
        canvas.drawCircle(center_x, center_y + dot_offset, dot_radius, dot_paint)

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
    def create(cls, rotation: Rotation = Rotation.ROT_0) -> 'Altar':
        """Create an altar prop at origin with optional rotation."""
        return cls((0, 0), rotation=rotation)
