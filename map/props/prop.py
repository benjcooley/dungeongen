"""Base class for map props."""

from typing import TYPE_CHECKING
import skia
from algorithms.shapes import Rectangle
from map.mapelement import MapElement

if TYPE_CHECKING:
    from map.map import Map

class Prop(MapElement):
    """Base class for decorative map props.
    
    Props are visual elements that can be placed in rooms and passages.
    They have a bounding rectangle and custom drawing logic.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        """Initialize a prop with position and size.
        
        Args:
            x: X coordinate in drawing units
            y: Y coordinate in drawing units
            width: Width in drawing units
            height: Height in drawing units
            map_: Parent map instance
        """
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
