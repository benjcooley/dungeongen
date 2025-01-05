from typing import ClassVar
from constants import CELL_SIZE
import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement

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
            # Create a 1x2 grid rectangle centered at origin
            cls._shape_instance = Rectangle.centered_grid(1, 2)
        return cls._shape_instance
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
