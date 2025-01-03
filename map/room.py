"""Room map element definition."""

from algorithms.shapes import Rectangle
from map.mapelement import MapElement
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map', options: 'Options') -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_, options=options)
