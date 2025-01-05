"""Altar prop implementation."""

from typing import TYPE_CHECKING
import skia

from algorithms.shapes import Rectangle
from algorithms.types import Point
from constants import CELL_SIZE
from graphics.conversions import grid_to_drawing
from map.props.prop import Prop
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Constants for altar dimensions
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface
ALTAR_HEIGHT = CELL_SIZE * 0.7  # Height of altar
ALTAR_INSET = (CELL_SIZE - ALTAR_HEIGHT) / 2  # Calculated inset from cell edges

# Grid offset from cell corner to altar center
ALTAR_GRID_OFFSET_X = 0.3  # Align closer to right side of cell
ALTAR_GRID_OFFSET_Y = 0.5  # Center vertically in cell

class Altar(Prop):
    """An altar prop that appears as a small rectangular table with decorative dots."""
    
    def __init__(self, center_x: float, center_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize an altar prop.
        
        Args:
            center_x: Center X coordinate in drawing units
            center_y: Center Y coordinate in drawing units
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        # Create rotated rectangle centered on point
        rect = Rectangle.rotated_rect(
            center_x,
            center_y,
            ALTAR_WIDTH,
            ALTAR_HEIGHT,
            rotation
        )
        # Create grid offset point and bounds rectangle
        grid_offset = (ALTAR_GRID_OFFSET_X, ALTAR_GRID_OFFSET_Y)
        grid_bounds = Rectangle(0, 0, 1.0, 1.0)
        super().__init__(rect, rect, map_, rotation,
                        grid_offset=grid_offset,
                        grid_bounds=grid_bounds)
    
    @classmethod
    def is_decoration(cls) -> bool:
        """Altars are not decorative - they're major props."""
        return False
        
        
    @classmethod
    def prop_size(cls) -> Point:
        """Get the size of this prop type in drawing units."""
        return (ALTAR_WIDTH, ALTAR_HEIGHT)  # Use altar-specific dimensions
        
    @classmethod
    def prop_grid_size(cls) -> Point:
        """Altars occupy 1x1 grid cells."""
        return (1.0, 1.0)  # Square grid cell
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> 'Altar':
        """Create an altar at a grid position.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
            
        Returns:
            A new Altar instance positioned at the grid coordinates
        """
        # Calculate center point from grid position and offset
        center_x = (grid_x + ALTAR_GRID_OFFSET_X) * CELL_SIZE
        center_y = (grid_y + ALTAR_GRID_OFFSET_Y) * CELL_SIZE
        return cls(center_x, center_y, map_, rotation)
        
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        # Get prop shape once and cast to Rectangle since we know it's always a rectangle
        rect_shape = self.get_prop_boundary_shape()  # type: Rectangle
        
        # Draw fill
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        rect_shape.draw(canvas, fill_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        rect_shape.draw(canvas, outline_paint)
        
        # Draw decorative dots
        dot_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_outline_color
        )
        dot_radius = CELL_SIZE * 0.05
        dot_offset = ALTAR_HEIGHT * 0.3  # Offset from center
        center_x = rect_shape.center()[0]
        canvas.drawCircle(center_x, -dot_offset, dot_radius, dot_paint)
        canvas.drawCircle(center_x, dot_offset, dot_radius, dot_paint)
