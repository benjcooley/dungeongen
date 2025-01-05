"""Base class for map props."""

import random
import math
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
        
        Props are drawn relative to their center point. The default orientation (0° rotation)
        has the prop facing right. Rotation happens counterclockwise in 90° increments.
        
        Args:
            x: Left edge X coordinate in drawing units
            y: Top edge Y coordinate in drawing units 
            width: Width in drawing units
            height: Height in drawing units
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        shape = Rectangle(x, y, width, height)
        super().__init__(shape=shape, map_=map_)
        self.rotation = rotation
        self.container: Optional['MapElement'] = None
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle) -> None:
        """Draw the prop's content in local coordinates.
        
        This method should be implemented by subclasses to draw their specific content.
        The coordinate system is set up so that:
        - Origin (0,0) is at the center of the prop
        - Prop is facing right (rotation 0)
        - bounds.width and bounds.height define the prop size
        - bounds.x and bounds.y are -width/2 and -height/2 respectively
        """
        pass

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Draw the prop with proper coordinate transformation."""
        if layer == Layers.PROPS:
            with canvas.save():
                # Move to prop center
                cx = self._x + self._width / 2
                cy = self._y + self._height / 2
                canvas.translate(cx, cy)
                
                # Apply rotation
                canvas.rotate(self.rotation.radians * (180 / math.pi))
                
                # Create bounds rect centered at origin
                bounds = Rectangle(
                    -self._width/2, -self._height/2,
                    self._width, self._height
                )
                
                # Draw in local coordinates
                self._draw_content(canvas, bounds)
            
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

    @classmethod
    @abstractmethod
    def is_grid_aligned(cls) -> bool:
        """Whether this prop should be aligned to the grid.
        
        Props that return True should be positioned at grid intersections.
        """
        ...

    @classmethod
    @abstractmethod
    def prop_size(cls) -> float:
        """Get the standard size of this prop type in drawing units."""
        ...

    @classmethod
    @abstractmethod
    def prop_grid_size(cls) -> float | None:
        """Get the standard size of this prop type in grid units.
        
        Returns None if the prop type doesn't have a standard grid size.
        """
        ...
        
    @classmethod
    @abstractmethod
    def get_prop_shape(cls) -> Shape:
        """Get the shape of this prop type in local coordinates.
        
        Returns a shape centered at (0,0) and oriented to the right (0 degrees).
        This shape will be transformed based on the prop's position and rotation.
        """
        ...

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Override base MapElement draw to prevent drawing bounds rectangle."""
        # Props should implement their own draw logic
        pass
