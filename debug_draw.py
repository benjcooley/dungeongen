"""Debug drawing utilities for visualizing room placement and connections."""

import math
from enum import Enum, auto
import skia
from typing import Tuple, Optional
from graphics.math import Point2D
from constants import CELL_SIZE, DEBUG_FONT_FAMILY, DEBUG_FONT_SIZE

class HatchPattern(Enum):
    """Available hatch patterns for debug visualization."""
    NONE = 0         # No hatching
    DIAGONAL = 1     # 45-degree diagonal lines
    CROSS = 2        # Crossed diagonal lines
    HORIZONTAL = 3   # Horizontal lines
    VERTICAL = 4     # Vertical lines
    GRID = 5         # Grid pattern

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

def _create_pattern_image(pattern: HatchPattern, spacing: float = 4.0) -> skia.Image:
    """Create a bitmap image for the hatch pattern.
    
    Args:
        pattern: Type of hatch pattern to create
        spacing: Spacing between hatch lines
        
    Returns:
        Skia Image containing the pattern
    """
    pattern_size = int(spacing * 4)  # Make pattern tile big enough for clean repeating
    surface = skia.Surface(pattern_size, pattern_size)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color4f(0, 0, 0, 0))  # Transparent background

    paint = skia.Paint(
        Color=skia.Color4f(0, 0, 0, 0.5),  # Semi-transparent black
        StrokeWidth=1,
        Style=skia.Paint.kStroke_Style,
        AntiAlias=True
    )

    if pattern == HatchPattern.DIAGONAL:
        canvas.drawLine(0, 0, pattern_size, pattern_size, paint)
    elif pattern == HatchPattern.CROSS:
        canvas.drawLine(0, 0, pattern_size, pattern_size, paint)
        canvas.drawLine(0, pattern_size, pattern_size, 0, paint)
    elif pattern == HatchPattern.HORIZONTAL:
        for y in range(0, pattern_size, int(spacing)):
            canvas.drawLine(0, y, pattern_size, y, paint)
    elif pattern == HatchPattern.VERTICAL:
        for x in range(0, pattern_size, int(spacing)):
            canvas.drawLine(x, 0, x, pattern_size, paint)
    elif pattern == HatchPattern.GRID:
        for y in range(0, pattern_size, int(spacing)):
            canvas.drawLine(0, y, pattern_size, y, paint)
        for x in range(0, pattern_size, int(spacing)):
            canvas.drawLine(x, 0, x, pattern_size, paint)

    return surface.makeImageSnapshot()

_last_key = None
_last_pattern = None
_hatch_patterns: dict[float, skia.Paint] = {}

def create_hatched_paint(color: int, pattern: HatchPattern = HatchPattern.NONE, spacing: float = 4.0) -> skia.Paint:
    """Create a paint with optional hatch pattern.
    
    Args:
        color: Base color for the paint
        pattern: Hatch pattern to apply (default NONE)
        spacing: Spacing between hatch lines
        
    Returns:
        Configured skia.Paint object
    """
    global _last_key
    global _last_pattern

    key = (color, pattern, spacing)
    if key == _last_key:
        return _last_pattern
    
    key_hash = hash(key)
    if key_hash in _hatch_patterns:
        paint =  _hatch_patterns[key_hash]
        _last_key = key
        _last_pattern = paint
        return paint
    
    paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kFill_Style,
        Color=color
    )

    if pattern == HatchPattern.NONE:
        return paint

    # Create pattern image and shader
    pattern_image = _create_pattern_image(pattern, spacing)
    shader = pattern_image.makeShader(
        skia.TileMode.kRepeat,
        skia.TileMode.kRepeat
    )
    
    # Combine the base color and the pattern shader
    color_shader = skia.Shaders.Color(color)
    composed_shader = skia.Shaders.Blend(skia.BlendMode.kSrcOver, shader, color_shader)
    paint.setShader(composed_shader)

    _last_key = key
    _last_pattern = paint
    _hatch_patterns[key_hash] = paint

    return paint

def debug_draw_grid_cell(x: int, y: int, fill_color: int, outline_color: Optional[int] = None, 
                        blocked: bool = False, hatch_pattern: HatchPattern = HatchPattern.NONE) -> None:
    """Draw a filled grid cell with optional outline and pattern.
    
    Args:
        x: Grid x coordinate
        y: Grid y coordinate
        fill_color: Skia color for cell fill
        outline_color: Optional Skia color for cell outline
        blocked: Whether to draw an X marking the cell as blocked
        hatch_pattern: Optional hatch pattern to apply
    """
    if _debug_canvas is None:
        return
        
    # Convert grid coords to pixels
    px = x * CELL_SIZE
    py = y * CELL_SIZE
    rect = skia.Rect(px, py, px + CELL_SIZE, py + CELL_SIZE)
        
    # Draw pattern if specified
    if hatch_pattern != HatchPattern.NONE:
        pattern_paint = create_hatched_paint(
            fill_color,
            pattern=hatch_pattern,
            spacing=CELL_SIZE/4
        )
        _debug_canvas.drawRect(rect, pattern_paint)
    else:
        base_paint = skia.Paint(
            Color=fill_color,
            Style=skia.Paint.kFill_Style,
            AntiAlias=True
        )
        _debug_canvas.drawRect(rect, base_paint)

    # Draw outline if specified
    if outline_color is not None:
        outline_paint = skia.Paint(
            Color=outline_color,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=2,
            AntiAlias=True
        )
        _debug_canvas.drawRect(rect, outline_paint)
    
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
