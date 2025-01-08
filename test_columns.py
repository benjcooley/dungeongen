import skia
from map.room import Room
from map.map import Map
from options import Options
from map.props.columnarrangement import ColumnArrangement, RowOrientation
from map.props.column import ColumnType

def main():
    # Create basic options
    options = Options()
    
    # Create map and room
    map_ = Map(options)
    room = Room(100, 100, 300, 200, map_)
    map_.add_element(room)
    
    # Test different column arrangements
    room.create_columns(ColumnArrangement.GRID, column_type=ColumnType.ROUND)
    
    # Create surface and canvas
    surface = skia.Surface(800, 600)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color(255, 255, 255))
    
    # Draw the map
    map_.render(canvas)
    
    # Save the result
    image = surface.makeImageSnapshot()
    image.save('test_columns.png', skia.kPNG)

if __name__ == '__main__':
    main()
