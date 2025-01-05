"""Stairs prop implementation."""

import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from map.enums import Layers
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from map.map import Map

class Stairs(Prop):
    """A staircase prop with parallel lines indicating steps."""
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT0) -> 'Stairs':
        """Create stairs using grid coordinates."""
        # Stairs are 1x1 grid units
        size = map_.options.cell_size
        x, y = grid_x * size, grid_y * size
        return cls(x, y, size, size, map_, rotation.radians)

    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if position is valid for stairs placement."""
        return container.shape.contains(x, y)

    def draw(self, canvas: skia.Canvas) -> None:
        """Draw the stairs."""
        with canvas.save():
            self._apply_rotation(canvas)
            
            # Draw step lines
            step_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=self._map.options.prop_stroke_width,
                Color=self._map.options.prop_dark_color
            )
            
            # Number of steps
            num_steps = 5
            step_spacing = self.height / (num_steps + 1)
            
            # Draw each step line
            for i in range(num_steps):
                y = self.y + step_spacing * (i + 1)
                canvas.drawLine(
                    self.x + self.width * 0.2,  # Start 20% in
                    y,
                    self.x + self.width * 0.8,  # End 80% across
                    y,
                    step_paint
                )
