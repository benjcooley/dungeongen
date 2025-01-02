"""
Main entry point for the crosshatch pattern generator.
"""
import skia

from graphics.crosshatch import (
    draw_background,
    create_line_paint,
    draw_crosshatch_with_clusters,
    PoissonDiskSampler,
    Rectangle,
    _surface,
    _canvas
)
from options import (
    WIDTH, HEIGHT, POISSON_RADIUS
)

def main():
    # Initialize canvas and background
    draw_background(_canvas)
    line_paint = create_line_paint()

    # Set up the sampler with shapes
    sampler = PoissonDiskSampler(WIDTH, HEIGHT, POISSON_RADIUS)

    # Add include and exclude shapes
    include_shape = Rectangle(100, 100, WIDTH - 200, HEIGHT - 200, inflate=40)
    sampler.add_include_shape(include_shape)

    exclude_shape = Rectangle(WIDTH // 3, HEIGHT // 3, WIDTH // 3, HEIGHT // 3)
    sampler.add_exclude_shape(exclude_shape)

    # Sample points
    points = sampler.sample()

    # Calculate center of the include shape
    center_point = (include_shape.x + include_shape.width / 2, 
                   include_shape.y + include_shape.height / 2)

    # Draw crosshatch patterns
    draw_crosshatch_with_clusters(points, sampler, center_point, _canvas, line_paint)

    # Save the result
    image = _surface.makeImageSnapshot()
    image.save('crosshatch_output.png', skia.kPNG)
    print("Crosshatch drawing completed and saved to 'crosshatch_output.png'")

if __name__ == "__main__":
    main()
