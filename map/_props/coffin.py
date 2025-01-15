"""Coffin prop implementation."""

import skia
from typing import TYPE_CHECKING
from map._props.prop import Prop, PropType #type: ignore
from graphics.rotation import Rotation
from graphics.conversions import grid_to_map

if TYPE_CHECKING:
    from map.map import Map

COFFIN_PROP_TYPE = PropType(is_decoration=True)

class Coffin(Prop):
    """A coffin-shaped prop with nested polygons."""
    
    def draw(self, canvas: skia.Canvas) -> None:
        canvas.save()
        self._apply_rotation(canvas)  # Apply rotation transform
        """Draw the coffin shape."""
        # Calculate points for outer coffin shape
        x, y = self._bounds.x, self._bounds.y
        w, h = self._bounds.width, self._bounds.height
        
        # Create outer coffin path
        outer_path = skia.Path()
        outer_path.moveTo(x + w/2, y)  # Top point
        outer_path.lineTo(x + w, y + h/6)  # Upper right
        outer_path.lineTo(x + w, y + h*0.75)  # Lower right
        outer_path.lineTo(x + w/2, y + h)  # Bottom point
        outer_path.lineTo(x, y + h*0.75)  # Lower left
        outer_path.lineTo(x, y + h/6)  # Upper left
        outer_path.close()
        
        # Draw outer coffin
        outer_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=2.0,
            Color=0xFF000000  # Black
        )
        canvas.drawPath(outer_path, outer_paint)
        
        # Calculate inset for inner coffin (10% of width/height)
        inset_x = w * 0.1
        inset_y = h * 0.1
        
        # Create inner coffin path
        inner_path = skia.Path()
        inner_path.moveTo(x + w/2, y + inset_y)  # Top point
        inner_path.lineTo(x + w - inset_x, y + h/6 + inset_y)  # Upper right
        inner_path.lineTo(x + w - inset_x, y + h*0.75 - inset_y)  # Lower right
        inner_path.lineTo(x + w/2, y + h - inset_y)  # Bottom point
        inner_path.lineTo(x + inset_x, y + h*0.75 - inset_y)  # Lower left
        inner_path.lineTo(x + inset_x, y + h/6 + inset_y)  # Upper left
        inner_path.close()
        
        # Draw inner coffin
        inner_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=1.0,
            Color=0xFF000000  # Black
        )
        canvas.drawPath(inner_path, inner_paint)
        
        # Restore canvas state after rotation
        canvas.restore()
