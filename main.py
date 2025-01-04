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
    
    # Initialize canvas and background
    background_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRect(skia.Rect.MakeWH(options.canvas_width, options.canvas_height), background_paint)

    # Create map and add a 5x5 room
    dungeon_map = Map(options)
    room = Room(10, 10, 5, 5, dungeon_map)

    # Set up the canvas transform to see the room properly
    transform = dungeon_map._calculate_default_transform(options.canvas_width, options.canvas_height)
    canvas.setMatrix(transform)

    # Draw the room
    room.draw(canvas)

    # Save the result
    image = surface.makeImageSnapshot()
    image.save('room_output.png', skia.kPNG)
    print("Room drawing completed and saved to 'room_output.png'")

if __name__ == "__main__":
    main()
