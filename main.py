"""
Main entry point for the crosshatch pattern generator.
"""
import skia

from graphics.crosshatch import (
    draw_background,
    create_line_paint,
    draw_crosshatch_with_clusters
)
from algorithms.poisson import PoissonDiskSampler
from algorithms.shapes import Rectangle
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Initialize canvas and background
    draw_background(options, canvas)
    line_paint = create_line_paint(options)

    # Set up the sampler with shapes
    sampler = PoissonDiskSampler(options.canvas_width, options.canvas_height, options.crosshatch_poisson_radius)

    # Add include and exclude shapes
    include_shape = Rectangle(100, 100, options.width - 200, options.height - 200, inflate=40)
    sampler.add_include_shape(include_shape)

    exclude_shape = Rectangle(options.width // 3, options.height // 3, 
                            options.width // 3, options.height // 3)
    sampler.add_exclude_shape(exclude_shape)

    # Sample points
    points = sampler.sample()

    # Calculate center of the include shape
    center_point = (include_shape.x + include_shape.width / 2, 
                   include_shape.y + include_shape.height / 2)

    # Draw crosshatch patterns
    draw_crosshatch_with_clusters(options, points, center_point, _canvas, line_paint)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('crosshatch_output.png', skia.kPNG)
    print("Crosshatch drawing completed and saved to 'crosshatch_output.png'")

if __name__ == "__main__":
    main()
