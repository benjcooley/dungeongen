from typing import ClassVar, TYPE_CHECKING

import skia

from algorithms.shapes import Rectangle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from map.enums import Layers
from map.mapelement import MapElement
from map.props.prop import Prop
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Constants for altar dimensions
ALTAR_WIDTH = CELL_SIZE * 0.3   # Width of altar surface
ALTAR_HEIGHT = CELL_SIZE * 0.7  # Height of altar
ALTAR_INSET = (CELL_SIZE - ALTAR_HEIGHT) / 2  # Calculated inset from cell edges

class Altar(Prop):
    """An altar prop that appears as a small rectangular table with decorative dots."""
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> 'Altar':
        """Create an altar at grid coordinates.
        
        Args:
            grid_x: Grid X coordinate (top-left)
            grid_y: Grid Y coordinate (top-left)
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
            
        Returns:
            New Altar instance
        """
        from graphics.conversions import grid_to_drawing
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        return cls(x, y, map_, rotation)
        
    def __init__(self, x: float, y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize an altar prop.
        
        Note: Use from_grid() to create altars at grid coordinates.
        
        Args:
            x: X coordinate in drawing units
            y: Y coordinate in drawing units
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        # Create grid-aligned rectangle and boundary shape
        rect = Rectangle(x, y, CELL_SIZE, CELL_SIZE)  # Full grid cell
        boundary = Rectangle(
            x + (CELL_SIZE - ALTAR_WIDTH) / 2,  # Center in cell
            y + (CELL_SIZE - ALTAR_HEIGHT) / 2,
            ALTAR_WIDTH,
            ALTAR_HEIGHT
        )
        super().__init__(rect, boundary, map_, rotation)
    
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
        
    # Cache for boundary shape
    _boundary_shape: ClassVar[Shape | None] = None
    
    @classmethod
    def get_prop_boundary_shape(cls) -> Shape:
        """Get a slightly inset rectangle for better collision detection."""
        if cls._boundary_shape is None:
            cls._boundary_shape = Rectangle(
                -CELL_SIZE/2 + ALTAR_INSET,
                -CELL_SIZE/2 + ALTAR_INSET,
                ALTAR_WIDTH,
                ALTAR_HEIGHT
            )
        return cls._boundary_shape
        
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
