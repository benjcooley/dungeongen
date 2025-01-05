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
from constants import CELL_SIZE

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
        """Draw the prop with proper rotation handling."""
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
                
                # Draw shape fill
                fill_paint = skia.Paint(
                    AntiAlias=True,
                    Style=skia.Paint.kFill_Style,
                    Color=self._map.options.prop_light_color
                )
                self.get_prop_boundary_shape().draw(canvas, fill_paint)
                
                # Draw shape outline
                outline_paint = skia.Paint(
                    AntiAlias=True,
                    Style=skia.Paint.kStroke_Style,
                    StrokeWidth=self._map.options.prop_stroke_width,
                    Color=self._map.options.prop_outline_color
                )
                self.get_prop_boundary_shape().draw(canvas, outline_paint)
                
                # Draw additional content
                self._draw_content(canvas, bounds)
            
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
    def is_valid_position(cls, x: float, y: float, rotation: Rotation, container: 'MapElement') -> bool:
        """Check if a position is valid for a prop within the container.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            rotation: Prop rotation
            container: The MapElement to place the prop in
            
        Returns:
            True if position is valid, False otherwise
        """
        # Get prop's boundary shape transformed to test position once
        shape = cls.get_map_aligned_boundary_shape(x, y, rotation)
        bounds = shape.bounds
        
        # For grid-aligned props, ensure the shape's top-left corner aligns to grid
        if cls.is_grid_aligned():
            # Check if top-left corner aligns to grid
            if (bounds.x % CELL_SIZE != 0) or (bounds.y % CELL_SIZE != 0):
                return False

        # Check if shape is contained within container
        if not container.shape.contains_shape(shape):
            return False
            
        # For non-decorative props, check intersection with other props
        if not cls.is_decoration():
            for prop in container._props:
                if not prop.is_decoration() and prop.shape.intersects(shape):
                    return False
                    
        return True


    @classmethod
    @abstractmethod
    def is_decoration(cls) -> bool:
        """Whether this prop is a decoration that should be drawn before other props.
        
        Decoration props are small floor items like rocks and cracks that don't
        need to check intersection with other props.
        """
        ...

    @classmethod
    @abstractmethod
    def is_grid_aligned(cls) -> bool:
        """Whether this prop should be aligned to the grid.
        
        Props that return True should be positioned at grid intersections.
        """
        ...

    @classmethod
    @abstractmethod
    def prop_size(cls) -> tuple[float, float]:
        """Get the standard size of this prop type in drawing units.
        
        Returns:
            Tuple of (width, height) in drawing units
        """
        ...

    @classmethod
    @classmethod
    def prop_grid_size(cls) -> tuple[float, float] | None:
        """Get the standard size of this prop type in grid units.
        
        Returns:
            Tuple of (width, height) in grid units, or None if no standard grid size.
            Base implementation returns None since not all props are grid-aligned.
        """
        return None
        
    @classmethod
    def get_prop_boundary_shape(cls) -> Shape:
        """Get the boundary shape of this prop type in local coordinates.
        
        Returns a shape centered at (0,0) and oriented to the right (0 degrees).
        This shape is used for collision detection and placement validation.
        The actual visual appearance may differ from this boundary shape.
        """
        # Create a centered rectangle based on prop size
        size = cls.prop_size()
        return Rectangle(-size/2, -size/2, size, size)

    @classmethod
    def get_map_aligned_boundary_shape(cls, center_x: float, center_y: float, rotation: Rotation) -> Shape:
        """Get the boundary shape aligned to a specific map position and rotation.
        
        Args:
            center_x: Center X coordinate in map space
            center_y: Center Y coordinate in map space
            rotation: Rotation angle
            
        Returns:
            The boundary shape translated and rotated to the specified position
        """
        # Get base boundary shape (centered at origin)
        base_shape = cls.get_prop_boundary_shape()
        bounds = base_shape.bounds
        
        # Calculate translation to move shape to center point
        dx = center_x - bounds.x - bounds.width/2
        dy = center_y - bounds.y - bounds.height/2
        
        # Create transformed shape
        # Note: This assumes the Shape classes implement proper translation and rotation
        return base_shape.translated(dx, dy).rotated(rotation.radians)

    @classmethod
    def get_map_aligned_bounds(cls, center_x: float, center_y: float, rotation: Rotation) -> Rectangle:
        """Get the bounds of this prop type aligned to a map position and rotation.
        
        Args:
            center_x: Center X coordinate in map space
            center_y: Center Y coordinate in map space
            rotation: Prop rotation
            
        Returns:
            A Rectangle representing the prop's bounds in map coordinates
        """
        # Get size based on alignment type
        if cls.is_grid_aligned():
            grid_size = cls.prop_grid_size()
            if grid_size is None:
                raise ValueError(f"Grid-aligned prop {cls.__name__} must specify prop_grid_size")
            width = grid_size[0] * CELL_SIZE
            height = grid_size[1] * CELL_SIZE
        else:
            width, height = cls.prop_size()
            
        # Create centered rectangle
        rect = Rectangle(-width/2, -height/2, width, height)
        
        # Apply rotation then translation
        return rect.rotated(rotation).translated(center_x, center_y)

    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Override base MapElement draw to prevent drawing bounds rectangle."""
        # Props should implement their own draw logic
        pass
