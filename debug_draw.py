"""Debug drawing utilities for visualizing room placement and connections."""

import math
import skia
from typing import Tuple, Optional
from algorithms.math import Point2D
from constants import CELL_SIZE, DEBUG_FONT_FAMILY, DEBUG_FONT_SIZE

# Predefined colors for debug visualization with good contrast on white
DEBUG_COLORS = {
    'RED': skia.Color(200, 0, 0),
    'GREEN': skia.Color(0, 100, 0),
    'BLUE': skia.Color(0, 0, 200),
    'MAGENTA': skia.Color(200, 0, 200),
    'PURPLE': skia.Color(128, 0, 128),
    'BROWN': skia.Color(139, 69, 19),
    'NAVY': skia.Color(0, 0, 128),
    'DARK_GREEN': skia.Color(0, 100, 0),
    'DARK_RED': skia.Color(139, 0, 0),
    'DARK_BLUE': skia.Color(0, 0, 139)
}

# Global canvas reference
_debug_canvas: Optional[skia.Canvas] = None

def debug_draw_init(canvas: skia.Canvas) -> None:
    """Initialize debug drawing with the given canvas."""
    global _debug_canvas
    _debug_canvas = canvas

def debug_draw_grid_point(x: int, y: int, color: str = 'RED', label: str = '') -> None:
    """Draw a point at grid coordinates with optional label."""
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE + CELL_SIZE/2
    py = y * CELL_SIZE + CELL_SIZE/2
    
    # Draw point circle
    paint = skia.Paint(Color=DEBUG_COLORS[color], StrokeWidth=4)
    _debug_canvas.drawCircle(px, py, 6, paint)
    
    # Draw label if provided
    if label:
        font = skia.Font(skia.Typeface(DEBUG_FONT_FAMILY), DEBUG_FONT_SIZE)
        _debug_canvas.drawString(label, px + 15, py, font, paint)

def debug_draw_grid_line(x1: int, y1: int, x2: int, y2: int, color: str = 'BLUE',
                        arrow: bool = False) -> None:
    """Draw a line between grid points with optional arrow."""
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px1 = x1 * CELL_SIZE + CELL_SIZE/2
    py1 = y1 * CELL_SIZE + CELL_SIZE/2
    px2 = x2 * CELL_SIZE + CELL_SIZE/2
    py2 = y2 * CELL_SIZE + CELL_SIZE/2
    
    # Draw line
    paint = skia.Paint(Color=DEBUG_COLORS[color], StrokeWidth=4)
    _debug_canvas.drawLine(px1, py1, px2, py2, paint)
    
    if arrow:
        # Calculate arrow head
        angle = math.atan2(py2 - py1, px2 - px1)
        arrow_size = 20
        arrow1_x = px2 - arrow_size * math.cos(angle + math.pi/6)
        arrow1_y = py2 - arrow_size * math.sin(angle + math.pi/6)
        arrow2_x = px2 - arrow_size * math.cos(angle - math.pi/6)
        arrow2_y = py2 - arrow_size * math.sin(angle - math.pi/6)
        
        # Draw arrow head
        path = skia.Path()
        path.moveTo(px2, py2)
        path.lineTo(arrow1_x, arrow1_y)
        path.lineTo(arrow2_x, arrow2_y)
        path.close()
        _debug_canvas.drawPath(path, paint)

def debug_draw_grid_rect(x: int, y: int, width: int, height: int, color: str = 'DARK_GREEN') -> None:
    """Draw a rectangle outline at grid coordinates."""
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    pwidth = width * CELL_SIZE
    pheight = height * CELL_SIZE
    
    # Draw rectangle
    paint = skia.Paint(Color=DEBUG_COLORS[color], Style=skia.Paint.kStroke_Style, StrokeWidth=4)
    _debug_canvas.drawRect(skia.Rect(px, py, px + pwidth, py + pheight), paint)

def debug_draw_grid_label(x: int, y: int, text: str, color: str = 'DARK_BLUE') -> None:
    """Draw text label above a grid point."""
    if _debug_canvas is None:
        return

def debug_draw_grid_cell(x: int, y: int, fill_color: int, outline_color: Optional[int] = None, blocked: bool = False) -> None:
    """Draw a filled grid cell with optional outline and blocked marker.
    
    Args:
        x: Grid x coordinate
        y: Grid y coordinate
        fill_color: Skia color for cell fill
        outline_color: Optional Skia color for cell outline
        blocked: Whether to draw an X marking the cell as blocked
    """
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    
    # Draw filled cell
    fill_paint = skia.Paint(Color=fill_color, Style=skia.Paint.kFill_Style)
    _debug_canvas.drawRect(skia.Rect(px, py, px + CELL_SIZE, py + CELL_SIZE), fill_paint)
    
    # Draw outline if specified
    if outline_color is not None:
        outline_paint = skia.Paint(
            Color=outline_color,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=2
        )
        _debug_canvas.drawRect(skia.Rect(px, py, px + CELL_SIZE, py + CELL_SIZE), outline_paint)
    
    # Draw X if blocked
    if blocked:
        x_paint = skia.Paint(
            Color=skia.Color(255, 0, 0),  # Red
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=2,
            AntiAlias=True
        )
        # Draw X from corner to corner
        _debug_canvas.drawLine(px + 4, py + 4, px + CELL_SIZE - 4, py + CELL_SIZE - 4, x_paint)
        _debug_canvas.drawLine(px + CELL_SIZE - 4, py + 4, px + 4, py + CELL_SIZE - 4, x_paint)

def debug_draw_map_label(x: float, y: float, text: str, color: str = 'DARK_BLUE') -> None:
    """Draw text label at map coordinates."""
    if _debug_canvas is None:
        return
        
    # Draw text
    paint = skia.Paint(Color=DEBUG_COLORS[color], AntiAlias=True)
    font = skia.Font(skia.Typeface(DEBUG_FONT_FAMILY), DEBUG_FONT_SIZE)
    font.setEdging(skia.Font.Edging.kAntiAlias)
    _debug_canvas.drawString(text, x, y - 5, font, paint)  # Offset up slightly
