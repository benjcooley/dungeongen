"""Stairs prop implementation."""

from typing import TYPE_CHECKING
import skia

from graphics.shapes import Rectangle
from graphics.aliases import Point
from constants import CELL_SIZE
from map._props.prop import Prop, PropType
from map.enums import Layers
from graphics.rotation import Rotation

# Stairs occupy a 1x1 cell
STAIRS_PROP_TYPE = PropType(
    is_grid_aligned=True,
    grid_size=(1, 1),
    boundary_shape=Rectangle(-CELL_SIZE/2, -CELL_SIZE/2, CELL_SIZE, CELL_SIZE)
)

class StairsProp(Prop):
    """A staircase prop drawn as horizontal lines showing steps.
    
    Stairs are purely decorative - they draw on top of existing passages
    without affecting the background or borders.
    """
    
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize stairs prop.
        
        Args:
            position: Position in map coordinates (top-left of the cell)
            rotation: Rotation (ROT_0=north, ROT_90=east, ROT_180=south, ROT_270=west)
        """
        super().__init__(STAIRS_PROP_TYPE, position, rotation=rotation)
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers = Layers.PROPS) -> None:
        """Draw the stairs as 6 centered lines decreasing in length."""
        if layer != Layers.PROPS:
            return
        
        # Draw step lines in solid black with border width
        step_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.border_width * 0.5,
            Color=skia.Color(0, 0, 0)  # Solid black
        )
        
        # 6 steps, decreasing in length from top (longest) to bottom (shortest)
        # First line is ON the grid boundary (top edge), others flow down from there
        num_steps = 6
        step_spacing = CELL_SIZE / (num_steps - 1)  # Distribute across full cell height
        
        # Line widths: top line at full passage width, bottom is narrow
        max_width = 1.0   # Full cell width for top line
        min_width = 0.15  # Narrow for bottom line
        
        # Small extension past cell edges to cover grid dots on widest line
        edge_extension = CELL_SIZE * 0.03
        
        # Draw relative to center (0,0) since canvas is already translated
        for i in range(num_steps):
            # Y position: first line at top edge (-CELL_SIZE/2), last at bottom edge (+CELL_SIZE/2)
            y = -CELL_SIZE/2 + step_spacing * i
            
            # Width decreases from top to bottom (perspective effect)
            t = i / (num_steps - 1)  # 0 at top, 1 at bottom
            width_ratio = max_width - t * (max_width - min_width)
            # Only add edge extension to the widest lines
            extension = edge_extension * (1 - t) if t < 0.5 else 0
            half_width = (CELL_SIZE * width_ratio) / 2 + extension
            
            canvas.drawLine(-half_width, y, half_width, y, step_paint)
    
    @classmethod
    def at_grid(cls, grid_x: int, grid_y: int, rotation: Rotation = Rotation.ROT_0) -> 'StairsProp':
        """Create stairs at a grid position.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate  
            rotation: Direction stairs face (ROT_0=north, etc.)
            
        Returns:
            A new StairsProp instance
        """
        # Position is top-left of the cell
        x = grid_x * CELL_SIZE
        y = grid_y * CELL_SIZE
        return cls((x, y), rotation)
