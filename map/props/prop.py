"""Base class for map props."""

import math
import math
import random

# Maximum attempts to find valid random position
MAX_PLACEMENT_ATTEMPTS = 30
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, ClassVar, Union, Protocol

import skia

from algorithms.shapes import Rectangle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from map.enums import Layers
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.mapelement import MapElement

if TYPE_CHECKING:
    from map.map import Map

class Prop(ABC):
    """Base class for decorative map props.
    
    Props are visual elements that can be placed in rooms and passages.
    They have a bounding shape, and optional grid bounds (in map units) and custom 
    drawing logic.
    """
    
    def __init__(self, 
                 position: Point,
                 boundary_shape: Shape, 
                 rotation: Rotation = Rotation.ROT_0,
                 grid_size: Point | None = None) -> None:
        """
        Props are drawn relative to their center point. The default orientation (0° rotation)
        has the prop facing right. Rotation happens counterclockwise in 90° increments.
        
        Args:
            position: Position to place prop in map units
            boundary_shape: Shape defining the prop's collision boundary, centered at (0,0) at rotation 0
            rotation: Rotation angle in 90° increments (default: facing right)
            grid_size: Optional size in grid units prop occupies if prop is grid aligned
        """
        self._boundary_shape = boundary_shape.make_rotated(rotation)
        if (grid_size is not None):
            if rotation == Rotation.ROT_90 or rotation == Rotation.ROT_270:
                self._boundary_shape.translate(grid_size[1] * CELL_SIZE / 2, grid_size[0] * CELL_SIZE / 2)
            else:
                self._boundary_shape.translate(grid_size[0] * CELL_SIZE / 2, grid_size[1] * CELL_SIZE / 2)
            self._boundary_shape.translate(position[0], position[1])
            if rotation == Rotation.ROT_90 or rotation == Rotation.ROT_270:
                self._grid_size = (grid_size[1], grid_size[0])
                self._grid_bounds = Rectangle(position[0], position[1], grid_size[1] * CELL_SIZE, grid_size[0] * CELL_SIZE)
            else:
                self._grid_size = (grid_size[0], grid_size[1])
                self._grid_bounds = Rectangle(position[0], position[1], grid_size[0] * CELL_SIZE, grid_size[1] * CELL_SIZE)
        else:            
            self._boundary_shape.translate(position[0], position[1])
            self._grid_bounds = None
            self._grid_size = None
        self._bounds = boundary_shape.bounds
        self._rotation = rotation
        self._map: Optional['Map'] = None
        self._container: Optional['MapElement'] = None
    
    @property
    def shape(self) -> Shape:
        """Get the boundary shape of this prop."""
        return self._boundary_shape

    @property
    def bounds(self) -> Rectangle:
        """Get the bounding rectangle of this prop."""
        return self._bounds

    @classmethod
    def grid_size(self) -> Point | None:
        """Get the size in grid units of this prop.
        
        Returns:
            Point with integer grid unit size of the prop or None if not grid aligned
        """
        return self._grid_size

    @property
    def grid_bounds(self) -> Rectangle | None:
        """Get the grid space occupied by this prop.
        
        For grid-aligned props, returns how map space size grid size prop occupies.
        For non-grid props, just returns bounds.
        
        Returns:
            Bounding grid rectangle in map units or None if not grid aligned
        """
        return self._grid_bounds

    @property
    def container(self) -> Optional['MapElement']:
        """Get the container element for this prop."""
        return self._container
    
    @property
    def rotation(self) -> Rotation:
        """Get the rotation of this prop."""
        return self._rotation
    
    @property
    def map(self) -> Union['Map', None]:
        """Get the map this prop belongs to."""
        return self._map

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
            draw_bounds = self._grid_bounds if self._grid_bounds is not None else self._bounds
            center = draw_bounds.center()
            canvas.translate(center[0], center[1])
            
            # Apply rotation (skia uses degrees, Rotation gives radians)
            canvas.rotate(-self.rotation.radians * (180 / math.pi))
            
            # Draw additional content in local coordinates centered at 0,0
            self._draw_content(canvas, Rectangle(-draw_bounds.width/2, -draw_bounds.height/2, draw_bounds.width, draw_bounds.height))
            
    @property
    def position(self) -> Point:
        """Get the current position of the prop."""
        return self._grid_bounds.p1 if self._grid_bounds is not None else self._bounds.p1
        
    @position.setter 
    def position(self, pos: tuple[float, float]) -> None:
        """Set the position of the prop and update its shape."""
        old_pos = self.position
        dx = pos[0] - old_pos._x
        dy = pos[1] - old_pos._y
        # Translate the boundary shape to new position in-place
        self._boundary_shape.translate(dx, dy)
        # Update the bounds
        self._bounds = self._boundary_shape.bounds
        # Update grid bounds if set
        if self._grid_bounds is not None:
            self._grid_bounds.translate(dx, dy)

    def snap_valid_position(self, x: float, y: float) -> Point | None:
        """Snap a position to the nearest valid position for this prop.
        
        For grid-aligned props, snaps to grid intersections.
        For wall-aligned props, snaps to nearest wall in rectangular rooms.
        For other props, returns the original position if valid.
        
        Args:
            x: X coordinate to snap
            y: Y coordinate to snap
            
        Returns:
            Point tuple if valid position found, None otherwise
        """
        if not self.container:
            return None
            
        # Handle wall-aligned props
        if self.is_wall_aligned() and isinstance(self.container._shape, Rectangle):
            room_bounds = self.container._shape.bounds
            prop_bounds = self.shape.bounds
            prop_width = prop_bounds.width
            prop_height = prop_bounds.height
            
            # Find closest wall
            left_dist = abs(x - room_bounds.left)
            right_dist = abs(x - room_bounds.right)
            top_dist = abs(y - room_bounds.top)
            bottom_dist = abs(y - room_bounds.bottom)
            
            # Try walls in order of closest to furthest
            walls = [(left_dist, 'left'), (right_dist, 'right'), 
                    (top_dist, 'top'), (bottom_dist, 'bottom')]
            walls.sort(key=lambda x: x[0])
            
            for _, wall in walls:
                if wall == 'left':
                    test_x = room_bounds.left
                    test_y = min(max(y, room_bounds.top + prop_height/2), 
                               room_bounds.bottom - prop_height/2)
                elif wall == 'right':
                    test_x = room_bounds.right - prop_width
                    test_y = min(max(y, room_bounds.top + prop_height/2),
                               room_bounds.bottom - prop_height/2)
                elif wall == 'top':
                    test_x = min(max(x, room_bounds.left + prop_width/2),
                               room_bounds.right - prop_width/2)
                    test_y = room_bounds.top
                else:  # bottom
                    test_x = min(max(x, room_bounds.left + prop_width/2),
                               room_bounds.right - prop_width/2)
                    test_y = room_bounds.bottom - prop_height
                
                if self.is_valid_position(test_x, test_y, self.rotation, self.container):
                    return (test_x, test_y)
            
            return None
            
        # Handle grid-aligned props
        if self.is_grid_aligned():
            # Snap to nearest grid intersection
            grid_x = round(x / CELL_SIZE) * CELL_SIZE
            grid_y = round(y / CELL_SIZE) * CELL_SIZE
            
            # Check if valid
            if self.is_valid_position(grid_x, grid_y, self.rotation, self.container):
                return (grid_x, grid_y)
            return None
            
        # For other props, just check if the original position is valid
        if self.is_valid_position(x, y):
            return (x, y)
            
        return None

    def place_random_position(self, max_attempts: int = MAX_PLACEMENT_ATTEMPTS) -> Point | None:
        """Try to place this prop at a valid random position within its container.
        
        Args:
            max_attempts: Maximum number of random positions to try
            
        Returns:
            Tuple of (x,y) coordinates if valid position found, None if all attempts failed
            
        Note: The prop must already be added to a container element.
        """
        if not self.container:
            return None
            
        # Get container bounds
        bounds = self.container.bounds
        
        # Try random positions
        for _ in range(max_attempts):
            # Generate random position within bounds
            x = random.uniform(bounds.x, bounds.x + bounds.width)
            y = random.uniform(bounds.y, bounds.y + bounds.height)
            
            # Try to snap to valid position
            snapped_pos = self.snap_valid_position(x, y)
            if snapped_pos is not None:
                self.position = snapped_pos
                return snapped_pos
                
        return None

    @property
    def grid_position(self) -> Point:
        """Get the prop's position in grid coordinates.
        
        For grid-aligned props, returns the integer grid cell position accounting for rotation.
        For non-grid props, returns the position modulo grid size rounded down.
        
        Returns:
            Position of s
        """
        return self._grid_bounds.p1 if self._grid_bounds is not None else (self.x, self.y)
    
    @grid_position.setter
    def grid_position(self, pos: Point) -> None:
        """Set the prop's position using grid coordinates.
        
        For grid-aligned props, positions the prop centered on the grid cell
        accounting for rotation. For non-grid props, simply multiplies by cell size.
        
        Args:
            pos: Tuple of (grid_x, grid_y) coordinates
        """
        if not self.is_grid_aligned():
            self.position = (pos[0] * CELL_SIZE, pos[1] * CELL_SIZE)
            return
            
        offset_x = self._x - self._grid_bounds.x
        offset_y = self._y - self._grid_bounds.y

        self.position = (pos[0] * CELL_SIZE + offset_x, pos[1] * CELL_SIZE + offset_y)
    
    @property
    def center(self) -> Point:
        """Get the center position of the prop."""
        bounds = self._grid_bounds if self._grid_bounds is not None else self._bounds
        return bounds.center()
        
    @center.setter
    def center(self, pos: tuple[float, float]) -> None:
        """Set the center position of the prop.
        
        Args:
            pos: Tuple of (x,y) coordinates for the new center position
        """
        bounds = self._grid_bounds if self._grid_bounds is not None else self._bounds
        dx = pos[0] - bounds.center()[0]
        dy = pos[1] - bounds.center()[1]
        self.position = (self.position[0] + dx, self.position[1] + dy)

    def is_valid_position(self, x: float, y: float) -> bool:
        """Check if a position is valid for a prop within its container.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            
        Returns:
            True if position is valid, False otherwise
        """
        # Store current position
        old_pos = self.position
        
        # Temporarily move to test position
        self.position = (x, y)
        
        # Get bounds at test position
        bounds = self._boundary_shape.bounds
        
        # For grid-aligned props, ensure the shape's top-left corner aligns to grid
        if self.is_grid_aligned():
            # Check if top-left corner aligns to grid
            if (bounds.x % CELL_SIZE != 0) or (bounds.y % CELL_SIZE != 0):
                valid = False
            else:
                valid = True
        else:
            valid = True

        # Check if shape is contained within container
        if valid and not self.container.shape.contains_shape(self._boundary_shape):
            valid = False
            
        # For non-decorative props, check intersection with other props
        if valid and not self.__class__.is_decoration():
            for prop in self.container._props:
                if prop is not self and not prop.__class__.is_decoration() and prop.shape.intersects(self._boundary_shape):
                    valid = False
                    break
        
        # Restore original position
        self.position = old_pos
                    
        return valid


    @classmethod
    @abstractmethod
    def is_decoration(cls) -> bool:
        """Whether this prop is a decoration that should be drawn before other props.
        
        Decoration props are small floor items like rocks and cracks that don't
        need to check intersection with other props.
        """
        ...
        
    @classmethod
    def is_wall_aligned(cls) -> bool:
        """Whether this prop should be aligned to walls when placed.
        
        Wall-aligned props will snap to the nearest wall when placed.
        Default implementation returns False.
        """
        return False
        
    def is_grid_aligned(self) -> bool:
        """Whether this prop should be aligned to the grid when placed.
        
        Grid-aligned props will snap to grid intersections.
        Returns True if the prop has grid bounds defined.
        """
        return self._grid_bounds is not None

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
    def _get_rotated_grid_offset(cls, grid_offset: Point, grid_size: Point, rotation: Rotation) -> Point:
        """Calculate offset from grid point to center based on rotation.
        
        For grid-aligned props, calculates the offset from the grid point
        to the prop's center point, accounting for rotation.

        Args:
            rotation: Prop rotation
            
        Returns:
            Tuple of (offset_x, offset_y) in grid units
            
        Raises:
            ValueError: If prop_grid_size is not defined for grid-aligned props
        """
        width = grid_size[0] * CELL_SIZE
        height = grid_size[1] * CELL_SIZE
        
        # Transform offset based on rotation
        if rotation == Rotation.ROT_0:
            return grid_offset
        elif rotation == Rotation.ROT_90:
            return (grid_offset[1], grid_offset[0])  # Flip x,y
        elif rotation == Rotation.ROT_180:
            return (width - grid_offset[0], grid_offset[1])
        else:  # ROT_270
            return (grid_offset[0], height - grid_offset[1])

    @classmethod
    def _get_rotated_grid_size(cls, grid_size: Point, rotation: Rotation) -> Point:
        """Returns the grid size rotated.

        Args:
            rotation: Prop rotation
            
        Returns:
            Tuple of (offset_x, offset_y) in grid units
            
        Raises:
            ValueError: If prop_grid_size is not defined for grid-aligned props
        """
        if rotation == Rotation.ROT_90 or rotation == Rotation.ROT_270:
            return (grid_size[1], grid_size[0])
        else:
            return grid_size

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

        
