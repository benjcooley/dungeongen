"""Base class for map props."""

from dataclasses import dataclass
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

@dataclass
class PropType:
    is_decoration: bool = False
    is_wall_aligned: bool = False
    is_grid_aligned: bool = False
    grid_size: Point | None = None
    boundary_shape: Shape | None = None
    
class Prop(ABC):
    """Base class for decorative map props.
    
    Props are visual elements that can be placed in rooms and passages.
    They have a bounding shape, and optional grid bounds (in map units) and custom 
    drawing logic.
    """
    
    def __init__(self, 
                 prop_type: PropType,                    
                 position: Point,
                 rotation: Rotation = Rotation.ROT_0,
                 boundary_shape: Shape | None = None,
                 grid_size: Point | None = None) -> None:
        """
        Props are drawn relative to their center point. The default orientation (0° rotation)
        has the prop facing right. Rotation happens counterclockwise in 90° increments.
        
        Args:
            prop_type: Type info for the prop
            position: Position to place prop in map units
            boundary_shape: Shape defining the prop's collision boundary, centered at (0,0) at rotation 0
            rotation: Rotation angle in 90° increments (default: facing right)
            grid_size: Optional size in grid units prop occupies if prop is grid aligned
        """
        if boundary_shape is None:
            boundary_shape = prop_type.boundary_shape
        if grid_size is None:
            grid_size = prop_type.grid_size
        self._prop_type = prop_type
        # First rotate the boundary shape
        self._boundary_shape = boundary_shape.make_rotated(rotation)
        
        # Calculate bounds before any translation
        self._bounds = self._boundary_shape.bounds
        
        if grid_size is not None:
            # For grid-aligned props, handle grid positioning
            if rotation == Rotation.ROT_90 or rotation == Rotation.ROT_270:
                self._grid_size = (grid_size[1], grid_size[0])
                self._grid_bounds = Rectangle(position[0], position[1], 
                                           grid_size[1] * CELL_SIZE, grid_size[0] * CELL_SIZE)
            else:
                self._grid_size = (grid_size[0], grid_size[1])
                self._grid_bounds = Rectangle(position[0], position[1], 
                                           grid_size[0] * CELL_SIZE, grid_size[1] * CELL_SIZE)
            # Don't multiply by CELL_SIZE here since grid_bounds is already in map units
            self._boundary_shape.translate(self._grid_bounds.width / 2, self._grid_bounds.height / 2)
        else:
            self._grid_bounds = None
            self._grid_size = None
            
        # Finally translate the boundary shape to its position
        self._boundary_shape.translate(position[0], position[1])
        # Update bounds after translation
        self._bounds = self._boundary_shape.bounds
        self._rotation = rotation
        self._map: Optional['Map'] = None
        self._container: Optional['MapElement'] = None
    
    @property
    def prop_type(self) -> PropType:
        """Get the type info of the prop."""
        return self._prop_type

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
    
    @property
    def should_snap(self) -> bool:
        """Check if this prop should snap to positions."""
        return self.prop_type.is_grid_aligned or self.prop_type.is_wall_aligned

    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers) -> None:
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
        # Save canvas state
        save_count = canvas.save()
        
        # Move to prop center
        draw_bounds = self._grid_bounds if self._grid_bounds is not None else self._bounds
        center = draw_bounds.center
        canvas.translate(center[0], center[1])
        
        # Apply rotation (skia uses clockwise degrees, we use counterclockwise radians)
        canvas.rotate(self.rotation.radians * (180 / math.pi))
        
        # Draw additional content in local coordinates centered at 0,0
        self._draw_content(canvas, Rectangle(-draw_bounds.width/2, -draw_bounds.height/2, draw_bounds.width, draw_bounds.height), layer)
        
        # Restore canvas state
        canvas.restoreToCount(save_count)
            
    @property
    def position(self) -> Point:
        """Get the current position of the prop."""
        return self._grid_bounds.p1 if self._grid_bounds is not None else self._bounds.p1
        
    @position.setter 
    def position(self, pos: tuple[float, float]) -> None:
        """Set the position of the prop and update its shape."""
        old_pos = self.position
        dx = pos[0] - old_pos[0]
        dy = pos[1] - old_pos[1]
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
        if self.prop_type.is_wall_aligned and isinstance(self.container._shape, Rectangle):
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
        if self.prop_type.is_grid_aligned:
            # Snap to nearest grid intersection
            grid_x = round(x / CELL_SIZE) * CELL_SIZE
            grid_y = round(y / CELL_SIZE) * CELL_SIZE
            
            # Check if valid
            if self.is_valid_position(grid_x, grid_y, self.rotation, self.container):
                return (grid_x, grid_y)
            return None
            
        # For other props, just check if the original position is valid
        if self.is_valid_position(x, y, self.rotation, self.container):
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
            if self.should_snap:
                pos = self.snap_valid_position(x, y) if self.should_snap else (x, y)
                if pos is not None:
                    self.position = pos
                return pos
            else:
                if self.is_valid_position(x, y):
                    self.position = (x, y)
                    return (x, y)
                
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
        if not self.prop_type.is_grid_aligned:
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

    def is_valid_position(self, x: float, y: float, rotation: Rotation = None, container: 'MapElement' = None) -> bool:
        """Check if current position is valid.

        Returns:
            True if position is valid, False otherwise
        """
        # For grid-aligned props, ensure the shape's top-left corner aligns to grid
        if self.prop_type.is_grid_aligned:
            if (x % CELL_SIZE != 0) or (y % CELL_SIZE != 0):
                return False
        
        pos = self.position
        shape: Shape
        if (x == pos[0]) and (y == pos[1]):
            shape = self._boundary_shape
        else:
            dx = x - pos[0]  # Fixed: Corrected direction of translation
            dy = y - pos[1]
            shape = self._boundary_shape.make_translated(dx, dy)

        # Check if shape is contained within container
        container = container or self.container
        if not container.contains_point(x, y):  # Changed to simpler point check
            return False
            
        # For non-decorative props, check intersection with other props
        if not self.prop_type.is_decoration:
            for prop in self.container._props:
                if prop is not self and \
                    not prop.prop_type.is_decoration and \
                    prop.shape.intersects(shape):
                        return False
                    
        return True

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
