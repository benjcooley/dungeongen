"""Altar prop implementation."""

import skia
from map.props.prop import Prop
from map.props.rotation import Rotation
from map.enums import Layers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from map.mapelement import MapElement

class Altar(Prop):
    """An altar prop with a rectangular base and two dots."""
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> 'Altar':
        """Create an altar using grid coordinates.
        
        Args:
            grid_x: Grid x-coordinate
            grid_y: Grid y-coordinate
            map_: Parent map instance
            rotation: Altar orientation (0, 90, 180, or 270 degrees)
            
        Returns:
            New Altar instance positioned on grid with proper wall spacing
        """
        cell_size = map_.options.cell_size
        wall_spacing = cell_size * 0.15  # 15% of cell size spacing from walls
        
        # Base position at grid point
        x = grid_x * cell_size
        y = grid_y * cell_size
        
        # Adjust position based on rotation to maintain wall spacing
        if rotation == Rotation.ROT_0:  # Facing right
            x += wall_spacing
        elif rotation == Rotation.ROT_90:  # Facing down
            y += wall_spacing
        elif rotation == Rotation.ROT_180:  # Facing left
            x += wall_spacing
        elif rotation == Rotation.ROT_270:  # Facing up
            y += wall_spacing
            
        # Size is reduced to account for wall spacing
        size = cell_size - (2 * wall_spacing)
        
        return cls(x, y, size, size, map_, rotation.radians)

    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if position is valid for altar placement.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            size: Size of the altar
            container: MapElement to check placement within
            
        Returns:
            True if position is valid for altar placement
        """
        from algorithms.shapes import Rectangle
        
        # Create rectangle with wall spacing
        wall_spacing = container._map.options.cell_size * 0.15
        rect = Rectangle(x + wall_spacing, y + wall_spacing, 
                        size - 2*wall_spacing, size - 2*wall_spacing)
        
        # Check container bounds and prop intersection
        return (container.contains_rectangle(rect) and 
                not container.prop_intersects(cls(x, y, size, size, container._map)))

    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        """Draw the altar's content in local coordinates."""
        # Draw main rectangle with light fill
        rect_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_light_color
        )
        
        # Rectangle is 1/4 width of cell, inset from left
        rect_width = bounds.width * 0.25
        rect_height = bounds.height * 0.7  # 70% of height
        rect_x = -bounds.width/2 + bounds.width * 0.15  # 15% inset from left
        rect_y = -rect_height/2  # Center vertically
        
        canvas.drawRect(skia.Rect.MakeXYWH(rect_x, rect_y, rect_width, rect_height), rect_paint)
        
        # Draw outline
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color
        )
        canvas.drawRect(skia.Rect.MakeXYWH(rect_x, rect_y, rect_width, rect_height), outline_paint)
        
        # Draw two dots (candles)
        dot_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_outline_color
        )
        
        dot_radius = bounds.width * 0.05
        dot_y_offset = rect_height/2 * 0.8  # Place dots near top/bottom edges
        
        # Top dot
        canvas.drawCircle(
            rect_x + rect_width/2,  # Center of rectangle
            rect_y - dot_y_offset,  # Above rectangle
            dot_radius,
            dot_paint
        )
        
        # Bottom dot
        canvas.drawCircle(
            rect_x + rect_width/2,  # Center of rectangle
            rect_y + rect_height + dot_y_offset,  # Below rectangle
            dot_radius,
            dot_paint
        )
