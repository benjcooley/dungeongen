"""Grid drawing styles and utilities."""

import math
import random
import skia
from dungeongen.graphics.shapes import ShapeGroup, Rectangle
from dungeongen.options import Options
from dungeongen.map.enums import GridStyle
from dungeongen.map.region import Region
from dungeongen.constants import CELL_SIZE

def draw_region_grid(canvas: skia.Canvas, region: Region, options: 'Options') -> None:
    """Draw grid dots for a region.
    
    Args:
        canvas: The canvas to draw on
        region: The region to draw grid for
        options: Drawing configuration options
    """
    bounds = region.shape.bounds
    
    # Calculate grid-aligned bounds, ensuring we start before the shape bounds
    min_x = math.floor(bounds.x / CELL_SIZE)
    min_y = math.floor(bounds.y / CELL_SIZE)
    max_x = math.ceil((bounds.x + bounds.width) / CELL_SIZE) 
    max_y = math.ceil((bounds.y + bounds.height) / CELL_SIZE)
    
    # Create base paint for dots
    dot_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeCap=skia.Paint.kRound_Cap,
        Color=options.grid_color
    )

    # Draw horizontal lines (include one line before min_y to ensure outer bounds)
    for y in range(min_y - 1, max_y + 1):
        py = y * CELL_SIZE
        # Don't skip horizontal lines - we want to draw all grid lines within bounds
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = CELL_SIZE / options.grid_dots_per_cell
        
        # Start at random position up to one dot spacing before edge
        x = bounds.x - dot_spacing * random.random()
        
        # Draw for bounds width plus two dot spacings
        while x <= bounds.x + bounds.width + 2 * dot_spacing:
            x += dot_spacing
            if region.shape.contains(x, py):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(x, py, x + dot_length, py, dot_paint)

    # Draw vertical lines (include one line before min_x to ensure outer bounds)
    for x in range(min_x - 1, max_x + 1):
        px = x * CELL_SIZE
        # Don't skip vertical lines - we want to draw all grid lines within bounds
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = CELL_SIZE / options.grid_dots_per_cell
        
        # Start at random position up to one dot spacing before edge
        y = bounds.y - dot_spacing * random.random()
        
        # Draw for bounds height plus two dot spacings
        while y <= bounds.y + bounds.height + 2 * dot_spacing:
            y += dot_spacing
            if region.shape.contains(px, y):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(px, y, px, y + dot_length, dot_paint)
