"""Room map element definition."""

from algorithms.shapes import Rectangle, Circle, Shape
from typing import List, TYPE_CHECKING

# Constant to make rooms slightly larger to ensure proper passage connections
ROOM_OVERLAP_OFFSET = 4.0  # pixels
from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.props.prop import Prop

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        # Create slightly larger rectangle to ensure proper passage connections
        shape = Rectangle(
            x - ROOM_OVERLAP_OFFSET/2,
            y - ROOM_OVERLAP_OFFSET/2,
            width + ROOM_OVERLAP_OFFSET,
            height + ROOM_OVERLAP_OFFSET
        )
        super().__init__(shape=shape, map_=map_)
        self._props: List['Prop'] = []
    
    def add_prop(self, prop: 'Prop') -> None:
        """Add a prop to this room.
        
        The prop must be contained within the room's bounds.
        """
        if not self._shape.contains(prop.bounds.x + prop.bounds.width/2, 
                                  prop.bounds.y + prop.bounds.height/2):
            raise ValueError("Prop must be contained within room bounds")
        self._props.append(prop)
        
    def remove_prop(self, prop: 'Prop') -> None:
        """Remove a prop from this room."""
        if prop in self._props:
            self._props.remove(prop)
            
    def draw(self, canvas: 'skia.Canvas', layer: Layers = Layers.PROPS) -> None:
        """Draw the room and its props."""
        super().draw(canvas, layer)
        # Draw props on the props layer
        if layer == Layers.PROPS:
            for prop in self._props:
                prop.draw(canvas, layer)
