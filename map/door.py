"""Door map element definition."""

from enum import Enum, auto
import math
from algorithms.shapes import Rectangle, ShapeGroup
from map.mapelement import MapElement
from algorithms.shapes import Shape
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class DoorOrientation(Enum):
    """Door orientation enum."""
    HORIZONTAL = auto()
    VERTICAL = auto()

# Amount to round the door side corners by
DOOR_SIDE_ROUNDING = 8.0
# Amount to extend the door sides to ensure proper connection with rooms
DOOR_SIDE_EXTENSION = DOOR_SIDE_ROUNDING

class Door(MapElement):
    """A door connecting two map elements.
    
    Doors can be either horizontal or vertical, and either open or closed.
    When closed, the door consists of two rectangles on either side.
    When open, it forms an I-shaped passage connecting the sides.
    """
    
    def __init__(self, x: float, y: float, orientation: DoorOrientation, map_: 'Map', open: bool = False) -> None:
        """Initialize a door with position and orientation.
        
        Args:
            x: X coordinate in map units
            y: Y coordinate in map units
            orientation: Door orientation (HORIZONTAL or VERTICAL)
            map_: Parent map instance
            open: Initial open/closed state
        """
        self._x = x
        self._y = y
        self._width = self._height = map_.options.cell_size
        self._open = open
        self._orientation = orientation
        
        # Calculate rectangle dimensions (1/3 of size in both dimensions)
        if self._orientation == DoorOrientation.HORIZONTAL:
            side_width = self._width / 3
            middle_height = self._height / 3
            middle_y = self._y + (self._height - middle_height) / 2  # Center vertically
            
            # Create inflated rectangles for rounded sides
            # Account for both extension and inflation in width/height calculation
            # Offset x,y by inflation amount since Rectangle will expand outward
            self._left_rect = Rectangle(
                self._x - DOOR_SIDE_EXTENSION + DOOR_SIDE_ROUNDING,
                self._y + DOOR_SIDE_ROUNDING,
                side_width + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                self._height - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            self._right_rect = Rectangle(
                self._x + self._width - side_width + DOOR_SIDE_ROUNDING,
                self._y + DOOR_SIDE_ROUNDING,
                side_width + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                self._height - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            self._middle_rect = Rectangle(self._x + side_width, middle_y, side_width, middle_height)
        else:
            side_height = self._height / 3
            middle_width = self._width / 3
            middle_x = self._x + (self._width - middle_width) / 2  # Center horizontally
            
            # Create inflated rectangles for rounded sides
            # Account for both extension and inflation in width/height calculation
            # Offset x,y by inflation amount since Rectangle will expand outward
            self._top_rect = Rectangle(
                self._x + DOOR_SIDE_ROUNDING,
                self._y - DOOR_SIDE_EXTENSION + DOOR_SIDE_ROUNDING,
                self._width - (DOOR_SIDE_ROUNDING * 2),
                side_height + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            self._bottom_rect = Rectangle(
                self._x + DOOR_SIDE_ROUNDING,
                self._y + self._height - side_height + DOOR_SIDE_ROUNDING,
                self._width - (DOOR_SIDE_ROUNDING * 2),
                side_height + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            self._middle_rect = Rectangle(middle_x, self._y + side_height, middle_width, side_height)
        
        # Initialize with empty shape if closed, or full I-shape if open
        shape = self._calculate_shape()
        super().__init__(shape=shape, map_=map_)
        self._bounds = Rectangle(self._x, self._y, self._width, self._height)
    
    def _calculate_shape(self) -> Shape:
        """Calculate the current shape based on open/closed state."""
        if not self._open:
            # When closed, include only the side rectangles
            if self._orientation == DoorOrientation.HORIZONTAL:
                shapes = [self._left_rect, self._right_rect]
            else:
                shapes = [self._top_rect, self._bottom_rect]
        else:
            # When open, combine all rectangles into an I-shape
            if self._orientation == DoorOrientation.HORIZONTAL:
                shapes = [self._left_rect, self._middle_rect, self._right_rect]
            else:
                shapes = [self._top_rect, self._middle_rect, self._bottom_rect]
        return ShapeGroup(includes=shapes, excludes=[])

    def get_side_shape(self, connected: 'MapElement') -> Rectangle:
        """Get the shape for the door's side that connects to the given element."""
        # Get center point of connected element
        conn_bounds = connected.bounds
        conn_cx = conn_bounds.x + conn_bounds.width / 2
        conn_cy = conn_bounds.y + conn_bounds.height / 2
        
        # Get door center
        door_cx = self._x + self._width / 2
        door_cy = self._y + self._height / 2
        
        # Return appropriate side rectangle based on orientation and position
        if self._orientation == DoorOrientation.HORIZONTAL:
            return self._left_rect if conn_cx < door_cx else self._right_rect
        else:
            return self._top_rect if conn_cy < door_cy else self._bottom_rect
    
    @property
    def open(self) -> bool:
        """Whether this door is open (can be passed through)."""
        return self._open
    
    @open.setter
    def open(self, value: bool) -> None:
        """Set the door's open state and update its shape."""
        if self._open != value:
            self._open = value
            self._shape = self._calculate_shape()
            
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, orientation: DoorOrientation, map_: 'Map', open: bool = False) -> 'Door':
        """Create a door using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            orientation: Door orientation (HORIZONTAL or VERTICAL)
            map_: Parent map instance
            open: Initial open/closed state
            
        Returns:
            A new Door instance
        """
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        return cls(x, y, orientation, map_, open)
