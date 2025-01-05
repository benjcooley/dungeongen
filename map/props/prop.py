"""Base class for map props."""

import math
import math
import random

# Maximum attempts to find valid random position
MAX_PLACEMENT_ATTEMPTS = 30
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, ClassVar

import skia

from algorithms.shapes import Rectangle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from map.enums import Layers
from map.mapelement import MapElement
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

class Prop(ABC):
    """Base class for decorative map props.
    
    Props are visual elements that can be placed in rooms and passages.
    They have a bounding rectangle and custom drawing logic.
    """
    
    def __init__(self, rect: Rectangle, boundary_shape: Shape, map_: 'Map', rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize a prop with a grid-aligned rectangle and boundary shape.
        
        Props are drawn relative to their center point. The default orientation (0° rotation)
        has the prop facing right. Rotation happens counterclockwise in 90° increments.
        
        Args:
            rect: Rectangle defining the prop's grid-aligned position and size
            boundary_shape: Shape defining the prop's collision boundary
            map_: Parent map instance
            rotation: Rotation angle in 90° increments (default: facing right)
        """
        self._rect = rect
        self._boundary_shape = boundary_shape
        self._bounds = boundary_shape.bounds
        self._x = rect.x
        self._y = rect.y
        self._width = rect.width
        self._height = rect.height
        self._map = map_
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
        """Draw the prop with proper coordinate transformation and styling."""
        with canvas.save():
            # Move to prop center
            center = self._bounds.center()
            canvas.translate(center[0], center[1])
            
            # Apply rotation
            canvas.rotate(self.rotation.radians * (180 / math.pi))
            
            # Create bounds rect centered at origin
            bounds = Rectangle(
                -self._width/2, -self._height/2,
                self._width, self._height
            )
            
            # Draw additional content
            self._draw_content(canvas, bounds)
            
    @property
    def position(self) -> Point:
        """Get the current position of the prop."""
        return (self._x, self._y)
        
    @position.setter 
    def position(self, pos: tuple[float, float]) -> None:
        """Set the position of the prop and update its shape."""
        dx = pos[0] - self._x
        dy = pos[1] - self._y
        self._x, self._y = pos
        # Translate the boundary shape to new position in-place
        self._boundary_shape.translate(dx, dy)
        # Update the bounds
        self._bounds = self._boundary_shape.bounds

    def snap_valid_position(self, x: float, y: float) -> tuple[tuple[float, float], bool]:
        """Snap a position to the nearest valid position for this prop.
        
        For grid-aligned props, snaps to grid intersections.
        For wall-aligned props, snaps to nearest wall in rectangular rooms.
        For other props, returns the original position if valid.
        
        Args:
            x: X coordinate to snap
            y: Y coordinate to snap
            
        Returns:
            Tuple of ((snapped_x, snapped_y), success) where success is True if
            a valid position was found, False otherwise
        """
        if not self.container:
            return ((x, y), False)
            
        # Handle grid-aligned props
        if self.is_grid_aligned():
            # Snap to nearest grid intersection
            grid_x = round(x / CELL_SIZE) * CELL_SIZE
            grid_y = round(y / CELL_SIZE) * CELL_SIZE
            
            # Check if valid
            if self.is_valid_position(grid_x, grid_y, self.rotation, self.container):
                return ((grid_x, grid_y), True)
            return ((x, y), False)
            
        # Handle wall-aligned props
        elif self.is_wall_aligned() and isinstance(self.container._shape, Rectangle):
            room_bounds = self.container._shape.bounds
            prop_bounds = self.shape.bounds
            prop_width = prop_bounds.width
            prop_height = prop_bounds.height
            
            # Find closest wall
            left_dist = abs(x - room_bounds.x)
            right_dist = abs(x - (room_bounds.x + room_bounds.width))
            top_dist = abs(y - room_bounds.y)
            bottom_dist = abs(y - (room_bounds.y + room_bounds.height))
            
            # Try walls in order of closest to furthest
            walls = [(left_dist, 'left'), (right_dist, 'right'), 
                    (top_dist, 'top'), (bottom_dist, 'bottom')]
            walls.sort(key=lambda x: x[0])
            
            for _, wall in walls:
                if wall == 'left':
                    test_x = room_bounds.x
                    test_y = min(max(y, room_bounds.y + prop_height/2), 
                               room_bounds.y + room_bounds.height - prop_height/2)
                elif wall == 'right':
                    test_x = room_bounds.x + room_bounds.width - prop_width
                    test_y = min(max(y, room_bounds.y + prop_height/2),
                               room_bounds.y + room_bounds.height - prop_height/2)
                elif wall == 'top':
                    test_x = min(max(x, room_bounds.x + prop_width/2),
                               room_bounds.x + room_bounds.width - prop_width/2)
                    test_y = room_bounds.y
                else:  # bottom
                    test_x = min(max(x, room_bounds.x + prop_width/2),
                               room_bounds.x + room_bounds.width - prop_width/2)
                    test_y = room_bounds.y + room_bounds.height - prop_height
                
                if self.is_valid_position(test_x, test_y, self.rotation, self.container):
                    return ((test_x, test_y), True)
            
            return ((x, y), False)
            
        # For other props, just check if the original position is valid
        elif self.is_valid_position(x, y, self.rotation, self.container):
            return ((x, y), True)
            
        return ((x, y), False)

    def place_random_position(self, max_attempts: int = MAX_PLACEMENT_ATTEMPTS) -> bool:
        """Try to place this prop at a valid random position within its container.
        
        Args:
            max_attempts: Maximum number of random positions to try
            
        Returns:
            True if a valid position was found, False if all attempts failed
            
        Note: The prop must already be added to a container element.
        """
        if not self.container:
            return False
            
        # Get container bounds
        bounds = self.container.bounds
        
        # Try random positions
        for _ in range(max_attempts):
            # Generate random position within bounds
            x = random.uniform(bounds.x, bounds.x + bounds.width)
            y = random.uniform(bounds.y, bounds.y + bounds.height)
            
            # Try to snap to valid position
            snapped, valid = self.snap_valid_position(x, y)
            if valid:
                self.position = snapped
                return True
                
        return False

    @property
    def grid_position(self) -> Point:
        """Get the prop's position in grid coordinates.
        
        For grid-aligned props, returns the integer grid cell position accounting for rotation.
        For non-grid props, returns the position modulo grid size rounded down.
        
        Returns:
            Tuple of (grid_x, grid_y) integer coordinates
        """
        if not self.is_grid_aligned():
            return (math.floor(self._x / CELL_SIZE), math.floor(self._y / CELL_SIZE))
            
        # For grid-aligned props, calculate based on center and rotation
        center_x = self._x + self._width/2
        center_y = self._y + self._height/2
        
        # Get offset from grid point to center
        offset = self._get_grid_center_offset(self.rotation)
        
        # Subtract offset from center to get grid position, rounding down to integers
        return (
            math.floor(center_x / CELL_SIZE - offset[0]),
            math.floor(center_y / CELL_SIZE - offset[1])
        )
    
    @grid_position.setter
    def grid_position(self, pos: tuple[float, float]) -> None:
        """Set the prop's position using grid coordinates.
        
        For grid-aligned props, positions the prop centered on the grid cell
        accounting for rotation. For non-grid props, simply multiplies by cell size.
        
        Args:
            pos: Tuple of (grid_x, grid_y) coordinates
        """
        if not self.is_grid_aligned():
            self.position = (pos[0] * CELL_SIZE, pos[1] * CELL_SIZE)
            return
            
        # Get offset from grid point to center
        offset = self._get_grid_center_offset(self.rotation)
        
        # Calculate center position by adding offset to grid position
        center_x = (pos[0] + offset[0]) * CELL_SIZE
        center_y = (pos[1] + offset[1]) * CELL_SIZE
        
        # Set position based on calculated center
        self.position = (
            center_x - self._width/2,
            center_y - self._height/2
        )
    
    @property
    def center(self) -> Point:
        """Get the center position of the prop."""
        return (self._x + self._width/2, self._y + self._height/2)
        
    @center.setter
    def center(self, pos: tuple[float, float]) -> None:
        """Set the center position of the prop.
        
        Args:
            pos: Tuple of (x,y) coordinates for the new center position
        """
        # Calculate new top-left position from center
        self._x = pos[0] - self._width/2
        self._y = pos[1] - self._height/2
        # Update the shape's position
        self._boundary_shape = Rectangle(self._x, self._y, self._bounds.width, self._bounds.height)
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
    def grid_offset(cls) -> Point:
        """Get the offset from grid position to prop position.
        
        For grid-aligned props, this returns the offset needed to properly
        position the prop relative to a grid point. For non-grid props,
        returns (0,0).
        
        Returns:
            Tuple of (x,y) offsets in drawing units
        """
        return (0.0, 0.0)

    @classmethod
    def grid_size(cls) -> Point:
        """Get the grid space occupied by this prop.
        
        For grid-aligned props, returns how many grid cells this prop occupies.
        For non-grid props, returns (0,0).
        
        Returns:
            Tuple of (width, height) in grid units
        """
        return (0.0, 0.0)

    @classmethod
    @abstractmethod
    def prop_size(cls) -> Point:
        """Get the actual size of this prop in drawing units.
        
        This defines the prop's tight bounding rectangle size.
        
        Returns:
            Tuple of (width, height) in drawing units
        """
        ...
        
    @classmethod
    def get_prop_boundary_shape(cls) -> Shape | None:
        """Get the boundary shape of this prop type in local coordinates.
        
        Returns a shape centered at (0,0) and oriented to the right (0 degrees),
        or None to use default rectangular boundary.
        This shape is used for collision detection and placement validation.
        The actual visual appearance may differ from this boundary shape.
        """
        return None  # Use default rectangular boundary

    @classmethod
    def get_map_aligned_boundary_shape(cls, center: Point, rotation: Rotation) -> Shape | None:
        """Get the boundary shape aligned to a specific map position and rotation.
        
        Args:
            center: Center point in map space
            rotation: Rotation angle
            
        Returns:
            The boundary shape translated and rotated to the specified position,
            or None to use default rectangular boundary
        """
        # Get base boundary shape (already centered at 0,0)
        base_shape = cls.get_prop_boundary_shape()
        if base_shape is None:
            return None
            
        # Create transformed shape - rotate first, then translate to center point
        return base_shape.rotated(rotation).translated(center[0], center[1])

    @classmethod
    def _get_grid_center_offset(cls, rotation: Rotation) -> Point:
        """Calculate offset from grid point to center based on rotation.
        
        For grid-aligned props, calculates the offset from the upper-left grid point
        to the prop's center point, accounting for rotation.
        
        Args:
            rotation: Prop rotation
            
        Returns:
            Tuple of (offset_x, offset_y) in grid units
            
        Raises:
            ValueError: If prop_grid_size is not defined for grid-aligned props
        """
        grid_size = cls.prop_grid_size()
        if grid_size is None:
            raise ValueError(f"Grid-aligned prop {cls.__name__} must specify prop_grid_size")
            
        width, height = grid_size
        
        # For 90° and 270° rotations, swap width and height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            width, height = height, width
            
        # Calculate center offset based on rotation
        if rotation == Rotation.ROT_0:
            return (width/2, height/2)
        elif rotation == Rotation.ROT_90:
            return (width/2, height/2)
        elif rotation == Rotation.ROT_180:
            return (1 - width/2, 1 - height/2)
        else:  # ROT_270
            return (1 - width/2, 1 - height/2)

    @classmethod
    def center_to_map_position(cls, center: Point, rotation: Rotation) -> Point:
        """Convert a center point to map-aligned position.
        
        For grid-aligned props, converts center point to top-left grid position.
        For non-grid props, returns the center point unchanged.
        
        Args:
            center: Center point in map space
            rotation: Prop rotation
            
        Returns:
            Map position (top-left for grid props, center for non-grid)
        """
        if not cls.is_grid_aligned():
            return center
            
        # For grid props, convert center to top-left position
        grid_size = cls.prop_grid_size()
        if grid_size is None:
            raise ValueError(f"Grid-aligned prop {cls.__name__} must specify prop_grid_size")
        
        width = grid_size[0] * CELL_SIZE
        height = grid_size[1] * CELL_SIZE
        
        # If rotated 90° or 270°, swap width/height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            width, height = height, width
            
        return (
            center[0] - width/2,
            center[1] - height/2
        )

    @classmethod
    def map_position_to_center(cls, pos: Point, rotation: Rotation) -> Point:
        """Convert a map-aligned position to center point.
        
        For grid-aligned props, converts top-left position to center point.
        For non-grid props, returns the position unchanged.
        
        Args:
            pos: Map position (top-left for grid props, center for non-grid)
            rotation: Prop rotation
            
        Returns:
            Center point in map space
        """
        if not cls.is_grid_aligned():
            return pos
            
        # For grid props, convert top-left to center position
        grid_size = cls.prop_grid_size()
        if grid_size is None:
            raise ValueError(f"Grid-aligned prop {cls.__name__} must specify prop_grid_size")
            
        width = grid_size[0] * CELL_SIZE
        height = grid_size[1] * CELL_SIZE
        
        # If rotated 90° or 270°, swap width/height
        if rotation in (Rotation.ROT_90, Rotation.ROT_270):
            width, height = height, width
            
        return (
            pos[0] + width/2,
            pos[1] + height/2
        )

    @property
    def shape(self) -> Shape:
        """Get the boundary shape of this prop."""
        return self._boundary_shape
        
    @property
    def bounds(self) -> Rectangle:
        """Get the bounding rectangle of this prop."""
        return self._bounds
