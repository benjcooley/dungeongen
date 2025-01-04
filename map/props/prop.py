"""Base class for map props."""

from typing import TYPE_CHECKING, Optional
import skia
from algorithms.shapes import Rectangle
from map.mapelement import MapElement
from map.props.rotation import Rotation
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map

class Prop(MapElement):
    """Base class for decorative map props.
    
    Props are visual elements that can be placed in rooms and passages.
    They have a bounding rectangle and custom drawing logic.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize a prop with position and size.
        
        Args:
            x: X coordinate in drawing units
            y: Y coordinate in drawing units
            width: Width in drawing units
            height: Height in drawing units
            map_: Parent map instance
            rotation: Rotation angle (default: no rotation)
        """
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
        self.rotation = rotation
        self.container: Optional['MapElement'] = None
    
    def _apply_rotation(self, canvas: skia.Canvas) -> None:
        """Apply rotation transform around prop center."""
        if self.rotation != Rotation.ROT_0:
            cx = self._bounds.x + self._bounds.width / 2
            cy = self._bounds.y + self._bounds.height / 2
            canvas.translate(cx, cy)
            canvas.rotate(self.rotation.radians * (180 / 3.14159265359))  # Convert radians to degrees for Skia
            canvas.translate(-cx, -cy)
            
    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Override base MapElement draw to prevent drawing bounds rectangle."""
        # Props should implement their own draw logic
        pass
