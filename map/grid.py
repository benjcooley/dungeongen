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
        
        # Start at a random position within one spacing interval
        x = bounds.x + random.uniform(0, dot_spacing)
        
        while x < bounds.x + bounds.width:
            if region.contains(x, py):
                # Apply size variation as a percentage of base size
                dot_size = options.grid_dot_size * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(dot_size)
                
                # Draw a very short line that looks like a dot
                canvas.drawLine(x, py, x + 0.1, py, dot_paint)
            x += dot_spacing

    # Draw vertical lines
    for x in range(math.floor(bounds.x / options.cell_size),
                  math.ceil((bounds.x + bounds.width) / options.cell_size) + 1):
        px = x * options.cell_size
        if not any(region.contains(px, bounds.y + dy) for dy in (0, bounds.height/2, bounds.height)):
            continue
            
        # Calculate dot spacing based on cell size and dots per cell
        dot_spacing = options.cell_size / options.grid_dots_per_cell
        
        # Start at a random position within one spacing interval
        y = bounds.y + random.uniform(0, dot_spacing)
        
        while y < bounds.y + bounds.height:
            if region.contains(px, y):
                # Apply size variation as a percentage of base size
                dot_size = options.grid_dot_size * (1 + random.uniform(
                    -options.grid_dot_variation,
                    options.grid_dot_variation
                ))
                dot_paint.setStrokeWidth(dot_size)
                
                # Draw a very short line that looks like a dot
                canvas.drawLine(px, y, px, y + 0.1, dot_paint)
            y += dot_spacing
