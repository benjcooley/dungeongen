"""
Main entry point for dungeon map generation.
"""
import os
import random
import skia
from map.map import Map
from options import Options
from tags import Tags

def main():
    # Get seed from environment variable or use default
    # seed = random.randint(1, 400000) 
    # int(os.getenv('SEED', '44444'))
    seed = 122652
    print(f"Using random seed: {seed}")
    random.seed(seed)

    options = Options()
    options.tags.add(str(Tags.SMALL))  # Generate small-sized dungeons
    
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

    # Save as PNG with size tag in filename
    size_tag = next((tag for tag in options.tags if tag in ('small', 'medium', 'large')), 'medium')
    image = surface.makeImageSnapshot()
    image.save(f'{size_tag}_map.png', skia.kPNG)
    
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
