"""Altar prop implementation."""

import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from map.enums import Layers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map

class Altar(Prop):
    """An altar prop with a rectangular base and two dots."""
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT0) -> 'Altar':
        """Create an altar using grid coordinates."""
        # Altar is 1x1 grid units
        size = map_.options.cell_size
        x, y = grid_x * size, grid_y * size
        return cls(x, y, size, size, map_, rotation.radians)

    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if position is valid for altar placement."""
        return container.shape.contains(x, y)

    def draw(self, canvas: skia.Canvas) -> None:
        """Draw the altar."""
        with canvas.save():
            self._apply_rotation(canvas)
            
            # Draw main rectangle
            rect_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.prop_dark_color
            )
            
            # Main rectangle is 80% of prop size
            rect_size = self.width * 0.8
            x = self.x + (self.width - rect_size) / 2
            y = self.y + (self.height - rect_size) / 2
            
            canvas.drawRect(skia.Rect.MakeXYWH(x, y, rect_size, rect_size), rect_paint)
            
            # Draw two dots
            dot_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.prop_light_color
            )
            
            dot_radius = self.width * 0.1
            dot_offset = self.width * 0.2
            
            # Left dot
            canvas.drawCircle(
                self.x + self.width/2 - dot_offset,
                self.y + self.height/2,
                dot_radius,
                dot_paint
            )
            
            # Right dot
            canvas.drawCircle(
                self.x + self.width/2 + dot_offset,
                self.y + self.height/2,
                dot_radius,
                dot_paint
            )
