"""Fountain prop implementation."""

import skia
from map._props.prop import Prop, PropType
from graphics.shapes import Circle, Rectangle
from graphics.aliases import Point
from constants import CELL_SIZE
from graphics.rotation import Rotation
from map.enums import Layers

# Fountain is slightly larger than one tile
FOUNTAIN_RADIUS = CELL_SIZE * 0.7
WATER_RADIUS = FOUNTAIN_RADIUS * 0.82  # Narrower edge rim
CENTER_RADIUS = FOUNTAIN_RADIUS * 0.25  # Smaller center spout

FOUNTAIN_PROP_TYPE = PropType(
    is_decoration=False,
    is_grid_aligned=False,
    boundary_shape=Circle(0, 0, FOUNTAIN_RADIUS),
)


class Fountain(Prop):
    """A fountain prop with concentric circles - edge, water, and center spout."""
    
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize a fountain prop.
        
        Args:
            position: Center position in map units
            rotation: Rotation (not really used for circular fountain)
        """
        super().__init__(
            FOUNTAIN_PROP_TYPE,
            position,
            rotation=rotation,
            boundary_shape=Circle(0, 0, FOUNTAIN_RADIUS)
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers) -> None:
        """Draw the fountain with concentric circles."""
        if layer != Layers.PROPS:
            return
            
        options = self._map.options if self._map else None
        
        # Outer edge (stone rim)
        edge_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=options.prop_fill_color if options else 0xFFFFFFFF
        )
        canvas.drawCircle(0, 0, FOUNTAIN_RADIUS, edge_paint)
        
        # Edge outline
        edge_stroke = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=options.prop_stroke_width if options else 2.0,
            Color=options.prop_outline_color if options else 0xFF000000
        )
        canvas.drawCircle(0, 0, FOUNTAIN_RADIUS, edge_stroke)
        
        # Water circle (slightly gray/blue tinted)
        water_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=0xFFE8EEF2  # Light blue-gray for water
        )
        canvas.drawCircle(0, 0, WATER_RADIUS, water_paint)
        
        # Water outline
        water_stroke = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=(options.prop_stroke_width if options else 2.0) * 0.75,
            Color=options.prop_outline_color if options else 0xFF000000
        )
        canvas.drawCircle(0, 0, WATER_RADIUS, water_stroke)
        
        # Center fountain spout
        center_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=options.prop_fill_color if options else 0xFFFFFFFF
        )
        canvas.drawCircle(0, 0, CENTER_RADIUS, center_paint)
        
        # Center outline
        center_stroke = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=(options.prop_stroke_width if options else 2.0) * 0.5,
            Color=options.prop_outline_color if options else 0xFF000000
        )
        canvas.drawCircle(0, 0, CENTER_RADIUS, center_stroke)
    
    @property
    def is_decoration(self) -> bool:
        """Fountains are not decorative - they're major props."""
        return False
    
    @classmethod
    def create(cls, x: float = 0, y: float = 0) -> 'Fountain':
        """Create a fountain prop at the specified position.
        
        Args:
            x: X position in map units
            y: Y position in map units
        """
        return cls((x, y))

