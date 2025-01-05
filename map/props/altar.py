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
        """Get the width and height of this prop type.
        
        Returns:
            Tuple of (width, height) from the prop's shape
        """
        shape = cls.get_prop_shape()
        return (shape.bounds.width, shape.bounds.height)
        
    @classmethod
    def prop_grid_size(cls) -> float:
        """Altars occupy 1x2 grid cells."""
        return 1.0
        
    _shape_instance: ClassVar[Shape] = None
    
    @classmethod
    def get_prop_shape(cls) -> Shape:
        """Get the cached shape instance for this prop type."""
        if cls._shape_instance is None:
            # Start with a 1x1 centered grid rectangle
            base = Rectangle.centered_grid(1, 1)
            # Adjust edges with insets
            right_inset = CELL_SIZE - ALTAR_INSET - ALTAR_WIDTH
            cls._shape_instance = base.adjust(
                left=ALTAR_INSET,
                top=ALTAR_INSET,
                right=-right_inset,
                bottom=ALTAR_INSET
            )
        return cls._shape_instance
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
