"""
Main entry point for drawing a simple room.
"""
import math
import skia

from graphics.conversions import grid_to_map
from map.mapelement import MapElement
from map.room import Room, RoomType
from map.map import Map
from map.door import Door, DoorOrientation, DoorType
from map.passage import Passage
from algorithms.rotation import Rotation
from constants import CELL_SIZE
from map.props import ColumnType, Altar, Coffin, Dais, Rock
from map.arrange import PropType, arrange_columns, ColumnArrangement, \
    arrange_random_props, arrange_rooms, ArrangeRoomStyle
from options import Options
from map.enums import Direction
from typing import List

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Create map
    dungeon_map = Map(options)

    DEMO = True

    if DEMO:
        # Create first rectangular room
        start_room0 = dungeon_map.create_rectangular_room(-10, -2, 5, 5)
        
        # Add dais to left side of room0
        dais = Dais((start_room0.bounds.left, start_room0.bounds.top + CELL_SIZE), Rotation.ROT_0)
        start_room0.add_prop(dais)

        # Create second rectangular room connected to first
        start_room, _, passage0, _ = dungeon_map.create_connected_room(
            start_room0, direction=Direction.EAST, passage_length=3, grid_width=5, grid_height=5,
            room_type=RoomType.RECTANGULAR
        )

        # Create circular end room connected to second room
        end_room, first_door, passage, second_door = dungeon_map.create_connected_room(
            start_room, direction=Direction.EAST, passage_length=5, grid_width=5, grid_height=5,
            room_type=RoomType.CIRCULAR,
            start_door_type=DoorType.DEFAULT,
            end_door_type=DoorType.NONE
        )
        
        # Add props to rooms and passage
        # Test vertical row layout for columns
        arrange_columns(start_room, ColumnArrangement.VERTICAL_ROWS, column_type=ColumnType.SQUARE)
        
        # Add square columns in a circle arrangement
        arrange_columns(end_room, ColumnArrangement.CIRCLE, column_type=ColumnType.SQUARE)
        
        # Add some rocks to all elements
        for element in dungeon_map.elements:
            if isinstance(element, Room):
                arrange_random_props(element, [PropType.SMALL_ROCK], min_count=0, max_count=5)
                arrange_random_props(element, [PropType.MEDIUM_ROCK], min_count=0, max_count=5)
    
    else:
        arrange_rooms(dungeon_map, ArrangeRoomStyle.LINEAR, min_rooms=5, max_rooms=7, min_size=3, max_size=7)

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
