"""Door map element definition."""

from algorithms.shapes import Rectangle
from map.mapelement import MapElement

class Door(MapElement):
    """A door connecting two map elements.
    
    Doors are small rectangular areas that mark connections between rooms and passages.
    The door's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        bounds = Rectangle(x, y, width, height)
        super().__init__(bounds=bounds, shape=bounds)
