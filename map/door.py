"""Door map element definition."""

from algorithms.shapes import Rectangle, ShapeGroup
from map.mapelement import MapElement
from algorithms.types import Shape
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class Door(MapElement):
    """A door connecting two map elements.
    
    Doors can be either horizontal or vertical, and either open or closed.
    When closed, the door consists of two rectangles on either side.
    When open, it forms an I-shaped passage connecting the sides.
    """
    
    def __init__(self, grid_x: float, grid_y: float, horizontal: bool, map_: 'Map', open: bool = False) -> None:
        """Initialize a door with position and orientation.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            horizontal: True for horizontal door, False for vertical
            map_: Parent map instance
            open: Initial open/closed state
        """
        # Convert grid coordinates to drawing coordinates
        self._x, self._y = grid_to_drawing(grid_x, grid_y, map_.options)
        self._width, self._height = grid_to_drawing_size(1, 1, map_.options)
        self._open = open
        self._is_horizontal = horizontal
        
        # Calculate side rectangle dimensions (1/3 of total size)
        if self._is_horizontal:
            side_width = self._width / 3
            self._left_rect = Rectangle(self._x, self._y, side_width, self._height)
            self._right_rect = Rectangle(self._x + self._width - side_width, self._y, side_width, self._height)
            self._middle_rect = Rectangle(self._x + side_width, self._y, side_width, self._height)
        else:
            side_height = self._height / 3
            self._top_rect = Rectangle(self._x, self._y, self._width, side_height)
            self._bottom_rect = Rectangle(self._x, self._y + self._height - side_height, self._width, side_height)
            self._middle_rect = Rectangle(self._x, self._y + side_height, self._width, side_height)
        
        # Initialize with empty shape if closed, or full I-shape if open
        shape = self._calculate_shape()
        super().__init__(shape=shape, map_=map_)
        self._bounds = Rectangle(self._x, self._y, self._width, self._height)
    
    def _calculate_shape(self) -> Shape:
        """Calculate the current shape based on open/closed state."""
        if not self._open:
            # When closed, the shape is empty - sides are handled by get_side_shape
            return ShapeGroup(shapes=[])
        else:
            # When open, combine all rectangles into an I-shape
            if self._is_horizontal:
                shapes = [self._left_rect, self._middle_rect, self._right_rect]
            else:
                shapes = [self._top_rect, self._middle_rect, self._bottom_rect]
            return ShapeGroup(shapes=shapes)

    def get_side_shape(self, connected: 'MapElement') -> Rectangle:
        """Get the shape for the door's side that connects to the given element."""
        if connected not in self.connections:
            raise ValueError("Element is not connected to this door")
            
        # Get center point of connected element
        conn_bounds = connected.bounds
        conn_cx = conn_bounds.x + conn_bounds.width / 2
        conn_cy = conn_bounds.y + conn_bounds.height / 2
        
        # Get door center
        door_cx = self._x + self._width / 2
        door_cy = self._y + self._height / 2
        
        # Return appropriate side rectangle based on orientation and position
        if self._is_horizontal:
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
