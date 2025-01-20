"""
Main entry point for dungeon map generation.
"""
import os
import random
import skia
from map.map import Map
from options import Options
from tags import Tags
from logging_config import logger, LogTags
from debug_config import debug_draw, DebugDrawFlags
from debug_draw import debug_draw_init
from tests.test_passages import TestPassages
from tests.test_tags import TestTags

# Set to True to run tests instead of normal map generation
RUN_TESTS = True

def main():
    if RUN_TESTS:
        from tests.test_runner import get_runner
        # Get singleton test runner and run specific test
        runner = get_runner()
        runner.setup(tags={TestTags.BASIC})
        runner.run_tests() # run_tests(test_names=["test_one_grid_passages"])
        return

    # Enable debug visualization and logging
    debug_draw.enable(DebugDrawFlags.OCCUPANCY, DebugDrawFlags.ELEMENT_NUMBERS)
    logger.enable_tags(LogTags.GENERATION, LogTags.ARRANGEMENT, LogTags.OCCUPANCY)
    logger.set_level(7)
    logger.debug_enabled = True
    logger.log_to_console = True  # Ensure console output is enabled

    # Get seed from environment variable or use default
    # seed = random.randint(1, 400000) 
    # int(os.getenv('SEED', '44444'))
    seed = 2314
    logger.log(LogTags.GENERATION, f"Using random seed: {seed}")
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
    
    # Calculate transform once
    transform = dungeon_map._calculate_default_transform(options.canvas_width, options.canvas_height)
    
    # Draw the map with transform
    dungeon_map.render(canvas, transform)
    
    # Debug draw the occupancy grid with same transform
    if debug_draw.is_enabled(DebugDrawFlags.OCCUPANCY):
        debug_draw_init(canvas)
        canvas.save()
        canvas.concat(transform)
        dungeon_map.occupancy.draw_debug(canvas)
        canvas.restore()

    # Save as PNG with size tag in filename
    size_tag = next((tag for tag in options.tags if tag in ('small', 'medium', 'large')), 'medium')
    image = surface.makeImageSnapshot()
    image.save('test_output.png', skia.kPNG)
    
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
    
    logger.log(LogTags.GENERATION, "Room drawing completed and saved to 'map_output.png'")

if __name__ == "__main__":
    main()
