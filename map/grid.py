"""Grid drawing styles and utilities."""

import math
import random
import skia
from algorithms.shapes import ShapeGroup
from options import Options
from map.enums import GridStyle

def draw_region_grid(canvas: skia.Canvas, region: ShapeGroup, options: 'Options') -> None:
    """Draw grid dots for a region.
    
    Args:
        canvas: The canvas to draw on
        region: The region to draw grid for
        options: Drawing configuration options
    """
    bounds = region.bounds
    
    # Create base paint for dots
    dot_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        StrokeCap=skia.Paint.kRound_Cap,
        Color=options.grid_color
    )

    # Draw horizontal lines
    for y in range(math.floor(bounds.y / options.cell_size),
                  math.ceil((bounds.y + bounds.height) / options.cell_size) + 1):
        py = y * options.cell_size
        if not any(region.contains(bounds.x + dx, py) for dx in (0, bounds.width/2, bounds.width)):
            continue
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = options.cell_size / options.grid_dots_per_cell
        
        # Start before or on the left edge
        x = bounds.x - dot_spacing * random.random()
        
        while x <= bounds.x + bounds.width:
            if region.contains(x, py):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(x, py, x + dot_length, py, dot_paint)
            x += dot_spacing + random.uniform(-dot_spacing * 0.1, dot_spacing * 0.1)

    # Draw vertical lines
    for x in range(math.floor(bounds.x / options.cell_size),
                  math.ceil((bounds.x + bounds.width) / options.cell_size) + 1):
        px = x * options.cell_size
        if not any(region.contains(px, bounds.y + dy) for dy in (0, bounds.height/2, bounds.height)):
            continue
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = options.cell_size / options.grid_dots_per_cell
        
        # Start before or on the top edge
        y = bounds.y - dot_spacing * random.random()
        
        while y <= bounds.y + bounds.height:
            if region.contains(px, y):
                # Apply length variation as a percentage of base length
                dot_length = options.grid_dot_length * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(options.grid_dot_size)
                
                # Draw a short line with varied length
                canvas.drawLine(px, y, px, y + dot_length, dot_paint)
            y += dot_spacing + random.uniform(-dot_spacing * 0.1, dot_spacing * 0.1)
