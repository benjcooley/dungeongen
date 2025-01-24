"""Helper functions for debug visualization in tests."""

import skia
from typing import Tuple, Optional

from constants import CELL_SIZE
from graphics.conversions import grid_to_map
from debug_config import debug_draw, DebugDrawFlags
from debug_draw import debug_draw_grid_cell, debug_draw_passage_check

def draw_test_info(canvas: skia.Canvas, test_name: str, test_desc: str) -> None:
    """Draw test case information on the canvas."""
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setAntiAlias(True)
    paint.setTextSize(24)
    
    canvas.drawString(test_name, 20, 40, paint)
    
    paint.setTextSize(16)
    canvas.drawString(test_desc, 20, 70, paint)

def draw_test_label(text: str, position: Tuple[float, float]) -> None:
    """Draw a text label at the given grid position."""
    if not debug_draw.is_enabled(DebugDrawFlags.LABELS):
        return
        
    x, y = grid_to_map(*position)
    
    paint = skia.Paint(Color=skia.ColorBLACK)
    paint.setAntiAlias(True)
    paint.setTextSize(12)
    
    debug_draw.submit_debug_draw(
        lambda canvas: canvas.drawString(text, x, y - CELL_SIZE/2, paint),
        layer=1
    )
