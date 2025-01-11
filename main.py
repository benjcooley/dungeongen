"""
Main entry point for dungeon map generation.
"""
import skia
from map.map import Map
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Create map
    dungeon_map = Map(options)

    # Initialize debug drawing
    from debug_draw import debug_draw_init, debug_draw_grid_point, debug_draw_grid_line
    from debug_draw import debug_draw_grid_rect, debug_draw_grid_label, debug_draw_map_label
    
    debug_draw_init(canvas)
    
    # Test grid points
    debug_draw_grid_point(0, 0, 'RED', 'Origin')
    debug_draw_grid_point(2, 2, 'BLUE', 'Point A')
    debug_draw_grid_point(5, 2, 'GREEN', 'Point B')
    
    # Test grid lines and arrows
    debug_draw_grid_line(2, 2, 5, 2, 'BLUE', arrow=True)
    debug_draw_grid_line(2, 2, 2, 5, 'RED', arrow=True)
    
    # Test rectangles
    debug_draw_grid_rect(1, 1, 3, 3, 'DARK_GREEN')
    debug_draw_grid_rect(4, 4, 2, 2, 'PURPLE')
    
    # Test labels
    debug_draw_grid_label(3, 3, "Grid Label")
    debug_draw_map_label(200, 200, "Map Label")
    
    # # Draw the map (empty for now)
    # dungeon_map.render(canvas)

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
