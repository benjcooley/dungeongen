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
from map.props.rotation import Rotation
from map.props.proptypes import PropType
from map.props.columnarrangement import ColumnArrangement, RowOrientation
from map.props.altar import Altar
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Create map
    dungeon_map = Map(options)
    
    # Add central rectangular room (5x5, centered at 0,0)
    # Since we want grid alignment and center at 0,0, we'll offset by -2,-2
    start_room = dungeon_map.add_rectangular_room(-2, -2, 5, 5)
    
    # Add a test column at room center
    from map.props.column import Column
    center_x = start_room.bounds.x + start_room.bounds.width/2
    center_y = start_room.bounds.y + start_room.bounds.height/2
    test_column = Column.create_round(center_x, center_y)
    start_room.add_prop(test_column)
    
    # Add door to the right of the room (at x=3, centered vertically)
    first_door = Door.from_grid(3, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=True)
    dungeon_map.add_element(first_door)
    
    # Add 5-grid long passage
    passage = Passage.from_grid(4, 0, 5, 1, dungeon_map)
    dungeon_map.add_element(passage)
    
    # Add closed door at the end of the passage
    second_door = Door.from_grid(9, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=False)
    dungeon_map.add_element(second_door)
    
    # Add circular room (5x5 grid units, 11 units right of start room)
    end_room = dungeon_map.add_circular_room(10, -2, 5)
    
    # Connect everything together
    start_room.connect_to(first_door)
    first_door.connect_to(passage)
    passage.connect_to(second_door)
    second_door.connect_to(end_room)
    
    # Add props to rooms and passage
    # Add altars to start room (square room)
    start_room.create_random_props([PropType.ALTAR], min_count=2, max_count=3)
    
    # Add columns in rows
    start_room.create_columns(ColumnArrangement.ROWS, orientation=RowOrientation.HORIZONTAL)
    
    # Add altar and rocks to end room (circular room)
    end_room.create_random_props([PropType.ALTAR], min_count=1, max_count=2)
    
    # Add columns in a circle arrangement
    end_room.create_columns(ColumnArrangement.CIRCLE)
    
    # Add some rocks
    end_room.create_random_props([PropType.MEDIUM_ROCK], min_count=0, max_count=2)
    end_room.create_random_props([PropType.SMALL_ROCK], min_count=0, max_count=2)

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
