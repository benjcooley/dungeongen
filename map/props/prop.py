"""Base class for map props."""

import random
from typing import TYPE_CHECKING, Optional
import skia
from algorithms.shapes import Rectangle, Shape
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
        self._x = x
        self._y = y
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
            
    @classmethod
    def get_valid_position(cls, size: float, container: 'MapElement') -> tuple[float, float] | None:
        """Try to find a valid position for a prop within the container.
        
        Args:
            size: Prop size
            container: The MapElement to place the prop in
            
        Returns:
            Tuple of (x,y) coordinates if valid position found, None otherwise
        """
        bounds = container.bounds
        margin = container._map.options.cell_size * 0.25  # 25% of cell size margin
        
        # Try 30 random positions
        for _ in range(30):
            x = random.uniform(bounds.x + margin, bounds.x + bounds.width - margin)
            y = random.uniform(bounds.y + margin, bounds.y + bounds.height - margin)
            
            test_prop = cls(x, y, size, size, container._map)
            if test_prop._is_valid_position(container.shape):
                return (x, y)
        return None
        
    def _is_valid_position(self, container: Shape) -> bool:
        """Check if the prop's current position is valid within the container shape.
        
        Tests the prop's center point to ensure it fits.
        Subclasses can override to add additional validation.
        """
        center_x = self._bounds.x + self._bounds.width/2
        center_y = self._bounds.y + self._bounds.height/2
        return container.contains(center_x, center_y)
        
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

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Override base MapElement draw to prevent drawing bounds rectangle."""
        # Props should implement their own draw logic
        pass
