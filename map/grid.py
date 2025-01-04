"""Grid drawing styles and utilities."""

import math
import random
import skia
from algorithms.shapes import ShapeGroup, Rectangle
from options import Options
from map.enums import GridStyle

def _get_grid_bounds(bounds: 'Rectangle', cell_size: float) -> tuple[int, int, int, int]:
    """Calculate the grid rectangle that fully encompasses the bounds.
    
    Args:
        bounds: The bounds to encompass
        cell_size: The size of each grid cell
        
    Returns:
        Tuple of (min_x, min_y, max_x, max_y) grid coordinates
    """
    min_x = math.floor(bounds.x / cell_size)
    min_y = math.floor(bounds.y / cell_size)
    max_x = math.ceil((bounds.x + bounds.width) / cell_size)
    max_y = math.ceil((bounds.y + bounds.height) / cell_size)
    return min_x, min_y, max_x, max_y

def draw_region_grid(canvas: skia.Canvas, region: ShapeGroup, options: 'Options') -> None:
    """Draw grid dots for a region.
    
    Args:
        canvas: The canvas to draw on
        region: The region to draw grid for
        options: Drawing configuration options
    """
    bounds = region.bounds
    
    # Get grid bounds that encompass the region
    min_x, min_y, max_x, max_y = _get_grid_bounds(bounds, options.cell_size)
    
    # Draw grid bounds rectangle for debugging
    debug_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeWidth=2,
        Color=skia.ColorGREEN
    )
    # Get grid-aligned bounds using the calculated grid coordinates
    min_x, min_y, max_x, max_y = _get_grid_bounds(bounds, options.cell_size)
    grid_bounds = Rectangle(
        min_x * options.cell_size,
        min_y * options.cell_size,
        (max_x - min_x) * options.cell_size,
        (max_y - min_y) * options.cell_size
    )
    grid_bounds.draw(canvas, debug_paint)
    
    # Create base paint for dots
    dot_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeCap=skia.Paint.kRound_Cap,
        Color=options.grid_color
    )

    # Draw horizontal lines
    for y in range(min_y, max_y + 1):
        py = y * options.cell_size
        if not any(region.contains(bounds.x + dx, py) for dx in (0, bounds.width/2, bounds.width)):
            continue
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = options.cell_size / options.grid_dots_per_cell
        
        # Start at random position up to one dot spacing before edge
        x = bounds.x - dot_spacing * random.random()
        
        # Draw for bounds width plus two dot spacings
        while x <= bounds.x + bounds.width + 2 * dot_spacing:
            x += dot_spacing
            if region.contains(x, py):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(x, py, x + dot_length, py, dot_paint)

    # Draw vertical lines
    for x in range(min_x, max_x + 1):
        px = x * options.cell_size
        if not any(region.contains(px, bounds.y + dy) for dy in (0, bounds.height/2, bounds.height)):
            continue
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = options.cell_size / options.grid_dots_per_cell
        
        # Start at random position up to one dot spacing before edge
        y = bounds.y - dot_spacing * random.random()
        
        # Draw for bounds height plus two dot spacings
        while y <= bounds.y + bounds.height + 2 * dot_spacing:
            y += dot_spacing
            if region.contains(px, y):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(px, y, px, y + dot_length, dot_paint)
