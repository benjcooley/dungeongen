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
    
    # Create map and add a 4x4 room centered at origin
    dungeon_map = Map(options)
    room = dungeon_map.add_rectangular_room(-2, -2, 4, 4)

    # Draw the map (which will draw all elements including our room)
    dungeon_map.render(canvas)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('map_output.png', skia.kPNG)
    print("Room drawing completed and saved to 'map_output.png'")

if __name__ == "__main__":
    main()
