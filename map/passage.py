"""Passage map element definition."""

from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Passage(MapElement):
    """A passage connecting two map elements.
    
    Passages are rectangular corridors that connect rooms and other passages.
    The passage's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
