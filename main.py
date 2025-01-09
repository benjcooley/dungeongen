"""
Main entry point for drawing a simple room.
"""
import math
import skia

from graphics.conversions import grid_to_map
from map.mapelement import MapElement
from map.room import Room, RoomType
from map.map import Map
from map.door import Door, DoorOrientation
from map.passage import Passage
from algorithms.rotation import Rotation
from constants import CELL_SIZE
from map.props import ColumnType, Altar, Coffin, Dais, Rock
from map.arrange import PropType, arrange_columns, ColumnArrangement, \
    arrange_random_props, arrange_rooms, ArrangeRoomStyle
from options import Options
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

        rooms: List[MapElement] = []

        # Add central rectangular room (5x5, centered at 0,0)
        # Since we want grid alignment and center at 0,0, we'll offset by -2,-2
        start_room0 = dungeon_map.add_element(Room.from_grid(-10, -2, 5, 5))
        rooms.append(start_room0)
        
        # Add dais to left side of room0
        dais = Dais((start_room0.bounds.left, start_room0.bounds.top + CELL_SIZE), Rotation.ROT_0)
        start_room0.add_prop(dais)
        
        # Add 5-grid long passage
        passage0 = dungeon_map.add_element(Passage.from_grid(-5, 0, 5, 1, dungeon_map))
        rooms.append(passage0)

        # Add central rectangular room (5x5, centered at 0,0)
        # Since we want grid alignment and center at 0,0, we'll offset by -2,-2
        start_room = dungeon_map.add_element(Room.from_grid(-2, -2, 5, 5))
        
        # Add door to the right of the room (at x=3, centered vertically)
        first_door = dungeon_map.add_element(Door.from_grid(3, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=True))
        rooms.append(first_door)
        
        # Add 5-grid long passage
        passage = dungeon_map.add_element(Passage.from_grid(4, 0, 5, 1, dungeon_map))
        rooms.append(passage)
        
        # Add closed door at the end of the passage
        second_door = dungeon_map.add_element(Door.from_grid(9, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=False))
        rooms.append(second_door)
        
        # Add circular room (5x5 grid units, 11 units right of start room)
        end_room = dungeon_map.add_element(Room.from_grid(10, -2, diameter=5, room_type=RoomType.CIRCULAR))
        rooms.append(end_room)
        
        # Connect everything together
        start_room0.connect_to(passage0)
        passage0.connect_to(start_room)
        start_room.connect_to(first_door)
        first_door.connect_to(passage)
        passage.connect_to(second_door)
        second_door.connect_to(end_room)
        
        # Add props to rooms and passage
        # Test vertical row layout for columns
        arrange_columns(start_room, ColumnArrangement.VERTICAL_ROWS, column_type=ColumnType.SQUARE)
        
        # Add square columns in a circle arrangement
        arrange_columns(end_room, ColumnArrangement.CIRCLE, column_type=ColumnType.SQUARE)
        
        # Add some rocks
        for room in rooms:
            arrange_random_props(room, [PropType.SMALL_ROCK], min_count=0, max_count=5)
            arrange_random_props(room, [PropType.MEDIUM_ROCK], min_count=0, max_count=5)
    
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
