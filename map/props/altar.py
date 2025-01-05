from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Rectangle, Shape

class Altar(Prop):
    @classmethod
    def get_prop_shape(cls) -> Shape:
        return Rectangle(-0.5, -0.5, 0.25, 1.0)
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
