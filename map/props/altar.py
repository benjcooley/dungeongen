import skia
from typing import ClassVar

from algorithms.shapes import Rectangle, Shape
from constants import CELL_SIZE
from map.enums import Layers
from map.mapelement import MapElement
from map.props.prop import Prop
from map.props.rotation import Rotation

# Constants for altar dimensions
ALTAR_INSET = CELL_SIZE * 0.15  # Inset from cell edges
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface

class Altar(Prop):
    """An altar prop that appears as a small rectangular table with decorative dots."""
    
    @classmethod
    def is_decoration(cls) -> bool:
        """Altars are not decorative - they're major props."""
        return False
        
    @classmethod
    def is_grid_aligned(cls) -> bool:
        """Altars should be aligned to grid intersections."""
        return True
        
    @classmethod
    def prop_size(cls) -> tuple[float, float]:
        """Get the size of this prop type in drawing units."""
        return (CELL_SIZE, CELL_SIZE)  # Altars are square
        
    @classmethod
    def prop_grid_size(cls) -> tuple[float, float]:
        """Altars occupy 1x1 grid cells."""
        return (1.0, 1.0)  # Square grid cell
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
