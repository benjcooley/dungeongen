"""Passage map element definition."""

from algorithms.shapes import Rectangle
from map.mapelement import MapElement

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are rectangular corridors that connect rooms and other passages.
    The passage's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        bounds = Rectangle(x, y, width, height)
        super().__init__(bounds=bounds, shape=bounds)
