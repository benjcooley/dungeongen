"""
Main entry point for drawing a simple room.
"""
import math
import skia

from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.room import Room
from map.map import Map
from map.door import Door, DoorOrientation
from map.passage import Passage
from algorithms.rotation import Rotation
from map.props import ColumnType, Altar, Coffin, Dais, Rock
from map.arrange import PropType, arrange_columns, ColumnArrangement, arrange_random_props, arrange_prop, arrange_rooms, ArrangeRoomStyle
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Create map
    dungeon_map = Map(options)
    
    print("\nStarting room generation...")
    rooms = arrange_rooms(dungeon_map, ArrangeRoomStyle.LINEAR, min_rooms=2, max_rooms=4)
    print(f"\nGenerated {len(rooms)} rooms total")
    
    # Add some decorations to the first and last rooms
    if rooms:
        arrange_columns(rooms[0], ColumnArrangement.VERTICAL_ROWS, column_type=ColumnType.SQUARE)
        arrange_columns(rooms[-1], ColumnArrangement.CIRCLE, column_type=ColumnType.SQUARE)
        arrange_random_props(rooms[-1], [PropType.MEDIUM_ROCK, PropType.SMALL_ROCK], min_count=2, max_count=4)

    # Draw the map (which will draw all rooms)
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
