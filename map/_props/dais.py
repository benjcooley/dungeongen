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
DAIS_HEIGHT = CELL_SIZE * 3

DAIS_PROP_TYPE = PropType(
    is_wall_aligned=True,
    is_grid_aligned=True,
    boundary_shape=Rectangle(-DAIS_WIDTH/2, -DAIS_HEIGHT/2, DAIS_WIDTH, DAIS_HEIGHT),
    grid_size=(2, 3)
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
            
        # Create paints
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )

        # Draw two concentric half circles
        # Center point is at (-CELL_SIZE, 0)
        center_x = -CELL_SIZE
        center_y = 0
        
        # Outer circle radius is 100% of height
        outer_radius = DAIS_HEIGHT
        # Inner circle radius is 80% of outer
        inner_radius = outer_radius * 0.8
        
        # Create paths for the half circles
        outer_path = skia.Path()
        outer_path.arcTo(
            skia.Rect.MakeXYWH(
                center_x - outer_radius,
                center_y - outer_radius,
                outer_radius * 2,
                outer_radius * 2
            ),
            -90,  # Start at top
            180,  # Sweep 180 degrees clockwise
            True  # Include center point
        )
        
        inner_path = skia.Path()
        inner_path.arcTo(
            skia.Rect.MakeXYWH(
                center_x - inner_radius,
                center_y - inner_radius,
                inner_radius * 2,
                inner_radius * 2
            ),
            -90,  # Start at top
            180,  # Sweep 180 degrees clockwise
            True  # Include center point
        )

        # Draw fills
        canvas.drawPath(outer_path, fill_paint)
        
        # Draw outlines
        canvas.drawPath(outer_path, outline_paint)
        canvas.drawPath(inner_path, outline_paint)

    @classmethod
    def create(cls, rotation: Rotation = Rotation.ROT_0) -> 'Dais':
        """Create a dais prop at origin with optional rotation."""
        return cls((0, 0), rotation=rotation)
