"""Debug drawing utilities for visualizing room placement and connections."""

import skia
from typing import Tuple, Optional
from algorithms.math import Point2D

# Predefined colors for debug visualization
DEBUG_COLORS = {
    'red': skia.Color(255, 0, 0),
    'green': skia.Color(0, 255, 0), 
    'blue': skia.Color(0, 0, 255),
    'yellow': skia.Color(255, 255, 0),
    'cyan': skia.Color(0, 255, 255),
    'magenta': skia.Color(255, 0, 255),
    'orange': skia.Color(255, 165, 0),
    'purple': skia.Color(128, 0, 128),
    'brown': skia.Color(165, 42, 42),
    'pink': skia.Color(255, 192, 203)
}

# Global canvas reference
_debug_canvas: Optional[skia.Canvas] = None

def debug_draw_init(canvas: skia.Canvas) -> None:
    """Initialize debug drawing with the given canvas."""
    global _debug_canvas
    _debug_canvas = canvas

def debug_draw_grid_point(x: int, y: int, color: str = 'red', label: str = '') -> None:
    """Draw a point at grid coordinates with optional label."""
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE + CELL_SIZE/2
    py = y * CELL_SIZE + CELL_SIZE/2
    
    # Draw point circle
    paint = skia.Paint(Color=DEBUG_COLORS[color], StrokeWidth=2)
    _debug_canvas.drawCircle(px, py, 3, paint)
    
    # Draw label if provided
    if label:
        paint.setTextSize(10)
        _debug_canvas.drawString(label, px + 5, py + 5, paint)

def debug_draw_grid_line(x1: int, y1: int, x2: int, y2: int, color: str = 'blue', 
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
    paint = skia.Paint(Color=DEBUG_COLORS[color], StrokeWidth=2)
    _debug_canvas.drawLine(px1, py1, px2, py2, paint)
    
    if arrow:
        # Calculate arrow head
        angle = math.atan2(py2 - py1, px2 - px1)
        arrow_size = 10
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

def debug_draw_grid_rect(x: int, y: int, width: int, height: int, color: str = 'green') -> None:
    """Draw a rectangle outline at grid coordinates."""
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    pwidth = width * CELL_SIZE
    pheight = height * CELL_SIZE
    
    # Draw rectangle
    paint = skia.Paint(Color=DEBUG_COLORS[color], Style=skia.Paint.kStroke_Style, StrokeWidth=2)
    _debug_canvas.drawRect(skia.Rect(px, py, px + pwidth, py + pheight), paint)
