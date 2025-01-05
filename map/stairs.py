"""Stairs map element definition."""

import skia
from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing
from map.enums import Layers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map

class Stairs(MapElement):
    """A staircase connecting different levels.
    
    Stairs occupy a 1x1 grid cell and are drawn with parallel lines
    indicating the steps. They can be rotated in 90-degree increments.
    """
    
    def __init__(self, x: float, y: float, map_: 'Map', rotation: float = 0.0) -> None:
        """Initialize stairs with position and rotation.
        
        Args:
            x: X coordinate in map units
            y: Y coordinate in map units
            map_: Parent map instance
            rotation: Rotation angle in radians
        """
        self._x = x
        self._y = y
        self._rotation = rotation
        size = map_.options.cell_size
        
        # Create shape as simple 1x1 rectangle
        shape = Rectangle(x, y, size, size)
        super().__init__(shape=shape, map_=map_)
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: float = 0.0) -> 'Stairs':
        """Create stairs using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            map_: Parent map instance
            rotation: Rotation angle in radians
            
        Returns:
            A new Stairs instance
        """
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        return cls(x, y, map_, rotation)

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Draw the stairs."""
        if layer == Layers.PROPS:
            with canvas.save():
                # Apply rotation around center
                cx = self._x + self._map.options.cell_size / 2
                cy = self._y + self._map.options.cell_size / 2
                canvas.translate(cx, cy)
                canvas.rotate(self._rotation * 180 / 3.14159)  # Convert radians to degrees
                canvas.translate(-cx, -cy)
                
                # Draw step lines
                step_paint = skia.Paint(
                    AntiAlias=True,
                    Style=skia.Paint.kStroke_Style,
                    StrokeWidth=self._map.options.prop_stroke_width,
                    Color=self._map.options.prop_dark_color
                )
                
                # Number of steps
                num_steps = 5
                step_spacing = self._map.options.cell_size / (num_steps + 1)
                
                # Draw each step line
                for i in range(num_steps):
                    y = self._y + step_spacing * (i + 1)
                    canvas.drawLine(
                        self._x + self._map.options.cell_size * 0.2,  # Start 20% in
                        y,
                        self._x + self._map.options.cell_size * 0.8,  # End 80% across
                        y,
                        step_paint
                    )
