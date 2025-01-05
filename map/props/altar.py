import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Rectangle, Shape

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
    def prop_size(cls) -> float:
        """Standard altar size is 1/4 cell width."""
        return 0.25
        
    @classmethod
    def prop_grid_size(cls) -> float:
        """Altars occupy 1x2 grid cells."""
        return 1.0
        
    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if position is valid for an altar.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            size: Altar size
            container: The MapElement to place the altar in
            
        Returns:
            True if position is valid, False otherwise
        """
        # Create bounding rectangle for altar
        rect = Rectangle(x - size/2, y - size, size, size * 2)
        return container.contains_rectangle(rect)
    @classmethod
    def get_prop_shape(cls) -> Shape:
        return Rectangle(-0.5, -0.5, 0.25, 1.0)
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
