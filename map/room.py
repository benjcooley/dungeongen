"""Room map element definition."""

from algorithms.shapes import Rectangle
from map.mapelement import MapElement

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        bounds = Rectangle(x, y, width, height)
        super().__init__(bounds=bounds, shape=bounds)
