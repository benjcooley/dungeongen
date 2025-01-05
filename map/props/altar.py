import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Rectangle, Shape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from map.mapelement import MapElement

class Altar(Prop):
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> 'Altar':
        cell_size = map_.options.cell_size
        wall_spacing = cell_size * 0.15
        x = grid_x * cell_size + wall_spacing
        y = grid_y * cell_size + wall_spacing
        altar = cls(x, y, cell_size, cell_size, map_, rotation.radians)
        altar._bounds = Rectangle(x, y, cell_size * 0.25, cell_size - 2*wall_spacing)
        return altar

    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        wall_spacing = container._map.options.cell_size * 0.15
        rect = Rectangle(x + wall_spacing, y + wall_spacing, size - 2*wall_spacing, size - 2*wall_spacing)
        return container.contains_rectangle(rect) and not container.prop_intersects(cls(x, y, size, size, container._map))

    @classmethod
    def get_prop_shape(cls) -> Shape:
        return Rectangle(-0.5, -0.5, 0.25, 1.0)
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        altar_shape = self.get_prop_shape()
        rect_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_light_color)
        altar_shape.draw(canvas, rect_paint)
        
        outline_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, 
                                 StrokeWidth=self._map.options.prop_stroke_width, 
                                 Color=self._map.options.prop_outline_color)
        altar_shape.draw(canvas, outline_paint)
        
        dot_paint = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=self._map.options.prop_outline_color)
        dot_radius = bounds.width * 0.05
        dot_inset = bounds.width * 0.1
        
        canvas.drawCircle(-0.375, -bounds.height/2 + dot_inset, dot_radius, dot_paint)
        canvas.drawCircle(-0.375, bounds.height/2 - dot_inset, dot_radius, dot_paint)
