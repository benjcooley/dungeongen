"""Base class for map props."""

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, ClassVar
import skia
from algorithms.shapes import Rectangle, Shape
from map.mapelement import MapElement
from map.props.rotation import Rotation
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map

class Prop(MapElement, ABC):
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
        self._x = x
        self._y = y
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
        self.rotation = rotation
        self.container: Optional['MapElement'] = None
    
    def _draw_content(self, canvas: skia.Canvas) -> None:
        """Draw the prop's content without rotation.
        
        This method should be implemented by subclasses to draw their specific content.
        The canvas will already be properly transformed for rotation.
        """
        pass

    def _apply_rotation(self, canvas: skia.Canvas) -> None:
        """Apply rotation transform around prop center."""
        cx = self._bounds.x + self._bounds.width / 2
        cy = self._bounds.y + self._bounds.height / 2
        canvas.translate(cx, cy)
        canvas.rotate(self.rotation.radians * (180 / 3.14159265359))  # Convert radians to degrees for Skia
        canvas.translate(-cx, -cy)
            
    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Draw the prop with proper rotation handling.
        
        The base implementation handles rotation and canvas state management.
        Subclasses should implement _draw_content() instead of overriding this method.
        """
        if layer == Layers.PROPS:
            with canvas.save():
                self._apply_rotation(canvas)
                self._draw_content(canvas)
            
    @property
    def position(self) -> tuple[float, float]:
        """Get the current position of the prop."""
        return (self._x, self._y)
        
    @position.setter 
    def position(self, pos: tuple[float, float]) -> None:
        """Set the position of the prop and update its shape."""
        self._x, self._y = pos
        # Update the shape's position
        self._shape = Rectangle(self._x, self._y, self._bounds.width, self._bounds.height)
        # Update the bounds
        self._bounds = self._shape.bounds

    @classmethod
    @abstractmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if a position is valid for a prop within the container.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            size: Prop size
            container: The MapElement to place the prop in
            
        Returns:
            True if position is valid, False otherwise
        """
        pass


    @property
    def is_decoration(self) -> bool:
        """Whether this prop is a decoration that should be drawn before other props.
        
        Decoration props are small floor items like rocks and cracks that don't
        need to check intersection with other props.
        """
        return False

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Override base MapElement draw to prevent drawing bounds rectangle."""
        # Props should implement their own draw logic
        pass
