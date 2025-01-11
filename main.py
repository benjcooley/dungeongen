"""
Main entry point for dungeon map generation.
"""
import argparse
import random
import skia
from map.map import Map
from options import Options

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate a dungeon map')
    parser.add_argument('--seed', type=int, default=12345,
                      help='Random seed for map generation (default: 12345)')
    args = parser.parse_args()
    
    # Set random seed
    random.seed(args.seed)
    print(f"Using random seed: {args.seed}")
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Fill canvas with white background
    canvas.clear(skia.Color(255, 255, 255))
    
    # Create map
    dungeon_map = Map(options)

    # Generate random dungeon
    dungeon_map.generate()
    
    # Draw the map
    dungeon_map.render(canvas)

    # Save as PNG
    image = surface.makeImageSnapshot()
    image.save('map_output.png', skia.kPNG)
    
    # # Save as PDF
    # stream = skia.FILEWStream('map_output.pdf')
    # with skia.PDF.MakeDocument(stream) as document:
    #     with document.page(options.canvas_width, options.canvas_height) as pdf_canvas:
    #         dungeon_map.render(pdf_canvas)
            
    # # Save as SVG
    # stream = skia.FILEWStream('map_output.svg')
    # svg_canvas = skia.SVGCanvas.Make((options.canvas_width, options.canvas_height), stream)
    # if svg_canvas:
    #     dungeon_map.render(svg_canvas)
    #     del svg_canvas  # Ensure canvas is destroyed before stream
    
    print("Room drawing completed and saved to 'map_output.png'")

if __name__ == "__main__":
    main()
