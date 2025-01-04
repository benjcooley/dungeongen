"""
Main entry point for drawing a simple room.
"""
import skia

from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.room import Room
from map.map import Map
from map.door import Door, DoorOrientation
from map.passage import Passage
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
    
    # Add door to the right of the room (at x=2, centered vertically)
    first_door = Door.from_grid(2, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=True)
    dungeon_map.add_element(first_door)
    
    # Add 5-grid long passage
    passage = Passage.from_grid(3, 0, 5, 1, dungeon_map)
    dungeon_map.add_element(passage)
    
    # Add closed door at the end of the passage
    second_door = Door.from_grid(8, 0, DoorOrientation.HORIZONTAL, dungeon_map, open=False)
    dungeon_map.add_element(second_door)
    
    # Add circular room (5x5 grid units, aligned with first room)
    end_room = dungeon_map.add_circular_room(11, -2, 2.5)
    
    # Connect everything together
    start_room.connect_to(first_door)
    first_door.connect_to(passage)
    passage.connect_to(second_door)
    second_door.connect_to(end_room)

    # Draw the map (which will draw all rooms)
    dungeon_map.render(canvas)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('map_output.png', skia.kPNG)
    print("Room drawing completed and saved to 'map_output.png'")

if __name__ == "__main__":
    main()
