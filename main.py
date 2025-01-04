"""
Main entry point for drawing a simple room.
"""
import skia

from map.room import Room
from map.map import Map
from options import Options

def main():
    options = Options()
    
    # Initialize Skia canvas
    surface = skia.Surface(options.canvas_width, options.canvas_height)
    canvas = surface.getCanvas()
    
    # Create map and add rooms
    dungeon_map = Map(options)
    
    # Add rectangular room
    rect_room = dungeon_map.add_rectangular_room(-2, -2, 5, 5)
    
    # Add circular room one grid space away
    circle_room = dungeon_map.add_circular_room(4, -2, 2.5)
    
    # Connect the rooms
    rect_room.connect_to(circle_room)

    # Draw the map (which will draw all rooms)
    dungeon_map.render(canvas)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('map_output.png', skia.kPNG)
    print("Room drawing completed and saved to 'map_output.png'")

if __name__ == "__main__":
    main()
