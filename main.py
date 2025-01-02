"""
Main entry point for the crosshatch pattern generator.
"""
import skia

from graphics.crosshatch import draw_crosshatches
from algorithms.shapes import Rectangle, ShapeGroup
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Initialize canvas and background
    background_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRect(skia.Rect.MakeWH(options.canvas_width, options.canvas_height), background_paint)

    # Create shape for crosshatching
    shape = Rectangle(100, 100, options.canvas_width - 200, options.canvas_height - 200, inflate=40)

    # Draw crosshatch patterns
    draw_crosshatches(options, shape, canvas)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('crosshatch_output.png', skia.kPNG)
    print("Crosshatch drawing completed and saved to 'crosshatch_output.png'")

if __name__ == "__main__":
    main()
