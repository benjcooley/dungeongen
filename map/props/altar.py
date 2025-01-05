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
        super().__init__(rect, rect, map_, rotation)
    
    @classmethod
    def is_decoration(cls) -> bool:
        """Altars are not decorative - they're major props."""
        return False
        
    @classmethod
    def is_grid_aligned(cls) -> bool:
        """Altars should be aligned to grid intersections."""
        return True
        
    @classmethod
    def prop_size(cls) -> Point:
        """Get the size of this prop type in drawing units."""
        return (ALTAR_WIDTH, ALTAR_HEIGHT)  # Use altar-specific dimensions
        
    @classmethod
    def prop_grid_size(cls) -> Point:
        """Altars occupy 1x1 grid cells."""
        return (1.0, 1.0)  # Square grid cell
    
    @classmethod
    def grid_offset(cls) -> Point:
        """Get the offset from grid position to altar center."""
        return (ALTAR_GRID_OFFSET_X, ALTAR_GRID_OFFSET_Y)
    
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
        # Convert grid position to center point
        center_x, center_y = cls.map_position_to_center((grid_x * CELL_SIZE, grid_y * CELL_SIZE), rotation)
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
