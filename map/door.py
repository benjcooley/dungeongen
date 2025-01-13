"""Door map element definition."""

from enum import Enum, auto
import math
import skia
from algorithms.shapes import Rectangle, ShapeGroup
from map.mapelement import MapElement
from algorithms.shapes import Shape
from graphics.conversions import grid_to_map
from map.enums import Layers
from constants import CELL_SIZE
from typing import TYPE_CHECKING
from map.occupancy import ElementType

if TYPE_CHECKING:
    from map.occupancy import OccupancyGrid

if TYPE_CHECKING:
    from map.map import Map
    from options import Options

class DoorOrientation(Enum):
    """Door orientation enum."""
    HORIZONTAL = auto()
    VERTICAL = auto()

class DoorType(Enum):
    """Door type enum."""
    OPEN = auto()   # Open doorway
    CLOSED = auto()   # Closed door

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
    
    def __init__(self, x: float, y: float, orientation: DoorOrientation, door_type: DoorType = DoorType.OPEN) -> None:
        """Initialize a door with position and orientation.
        
        Args:
            x: X coordinate in map units
            y: Y coordinate in map units
            orientation: Door orientation (HORIZONTAL or VERTICAL)
            open: Initial open/closed state
        """
        
        # Validate position is within reasonable limits
        if abs(x) > 4200 or abs(y) > 4200:
            raise ValueError(f"Door position ({x}, {y}) exceeds reasonable limits (±3200)")
        
        self._x = x
        self._y = y
        self._width = self._height = CELL_SIZE
        self._open = (door_type == DoorType.OPEN)
        self._orientation = orientation
        
        # Calculate dimensions for sides and middle
        if self._orientation == DoorOrientation.HORIZONTAL:
            side_width = self._width / 3
            middle_height = self._height * 0.6  # Make middle section wider (3/5 instead of 2/3)
            middle_y = self._y + (self._height - middle_height) / 2  # Center vertically
            
            # Create left side rectangle with rounded corners
            left_side = Rectangle(
                self._x - DOOR_SIDE_EXTENSION + DOOR_SIDE_ROUNDING,
                self._y + DOOR_SIDE_ROUNDING,
                side_width + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                self._height - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            # Left half of middle rectangle
            left_middle = Rectangle(
                self._x + side_width,
                middle_y,
                side_width / 2,
                middle_height
            )
            self._left_group = ShapeGroup(includes=[left_side, left_middle], excludes=[])
            
            # Create right side rectangle with rounded corners
            right_side = Rectangle(
                self._x + self._width - side_width + DOOR_SIDE_ROUNDING,
                self._y + DOOR_SIDE_ROUNDING,
                side_width + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                self._height - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            # Right half of middle rectangle
            right_middle = Rectangle(
                self._x + side_width + side_width/2,
                middle_y,
                side_width / 2,
                middle_height
            )
            self._right_group = ShapeGroup(includes=[right_side, right_middle], excludes=[])
        else:
            side_height = self._height / 3
            middle_width = self._width * 0.6  # Make middle section wider (3/5 instead of 2/3)
            middle_x = self._x + (self._width - middle_width) / 2  # Center horizontally
            
            # Create top side rectangle with rounded corners
            top_side = Rectangle(
                self._x + DOOR_SIDE_ROUNDING,
                self._y - DOOR_SIDE_EXTENSION + DOOR_SIDE_ROUNDING,
                self._width - (DOOR_SIDE_ROUNDING * 2),
                side_height + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            # Top half of middle rectangle
            top_middle = Rectangle(
                middle_x,
                self._y + side_height,
                middle_width,
                side_height / 2
            )
            self._top_group = ShapeGroup(includes=[top_side, top_middle], excludes=[])
            
            # Create bottom side rectangle with rounded corners
            bottom_side = Rectangle(
                self._x + DOOR_SIDE_ROUNDING,
                self._y + self._height - side_height + DOOR_SIDE_ROUNDING,
                self._width - (DOOR_SIDE_ROUNDING * 2),
                side_height + DOOR_SIDE_EXTENSION - (DOOR_SIDE_ROUNDING * 2),
                inflate=DOOR_SIDE_ROUNDING
            )
            # Bottom half of middle rectangle
            bottom_middle = Rectangle(
                middle_x,
                self._y + side_height + side_height/2,
                middle_width,
                side_height / 2
            )
            self._bottom_group = ShapeGroup(includes=[bottom_side, bottom_middle], excludes=[])
        
        shape = self._calculate_shape()
        
        super().__init__(shape)
    
    def _calculate_shape(self) -> Shape:
        """Calculate the current shape based on open/closed state."""
        if not self._open:
            # When closed, return empty shape list
            return ShapeGroup(includes=[], excludes=[])
        else:
            # When open, combine the side groups into a single shape
            if self._orientation == DoorOrientation.HORIZONTAL:
                return ShapeGroup.combine([self._left_group, self._right_group])
            else:
                return ShapeGroup.combine([self._top_group, self._bottom_group])

    def get_side_shape(self, connected: 'MapElement') -> ShapeGroup:
        """Get the shape for the door's side that connects to the given element."""
        # Get center point of connected element
        conn_bounds = connected.bounds
        conn_cx = conn_bounds.x + conn_bounds.width / 2
        conn_cy = conn_bounds.y + conn_bounds.height / 2
        
        # Get door center
        door_cx = self._x + self._width / 2
        door_cy = self._y + self._height / 2
        
        # Return appropriate side group based on orientation and position
        if self._orientation == DoorOrientation.HORIZONTAL:
            return self._left_group if conn_cx < door_cx else self._right_group
        else:
            return self._top_group if conn_cy < door_cy else self._bottom_group
    
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
    
    def draw(self, canvas: skia.Canvas, layer: 'Layers' = Layers.PROPS) -> None:
        """Draw the door if it's closed."""
        if not self._open and layer == Layers.OVERLAY:
            # Create paint for door
            door_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.prop_light_color
            )
            
            # Calculate door rectangle dimensions
            if self._orientation == DoorOrientation.HORIZONTAL:
                # Door width is 1/6 of cell size
                door_width = self._width / 6
                # Door height is 55% of cell height
                door_height = self._height * 0.55
                # Center the door
                door_x = self._x + (self._width - door_width) / 2
                door_y = self._y + (self._height - door_height) / 2
            else:
                # Door width is 60% of cell width
                door_width = self._width * 0.6
                # Door height is 1/5 of cell size
                door_height = self._height / 5
                # Center the door
                door_x = self._x + (self._width - door_width) / 2
                door_y = self._y + (self._height - door_height) / 2
            
            # Create door rectangle
            door = Rectangle(door_x, door_y, door_width, door_height, inflate=1.0)
            if not door.is_valid:
                print("Warning: Door rectangle is invalid!")
            
            # Draw filled door with thinner stroke
            fill_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self._map.options.room_color
            )
            door.draw(canvas, fill_paint)
            
            # Draw border with half the normal border width
            border_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=self._map.options.door_stroke_width,
                Color=self._map.options.border_color
            )
            door.draw(canvas, border_paint)
            
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, orientation: DoorOrientation, door_type: DoorType = DoorType.OPEN) -> 'Door':
        """Create a door using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            orientation: Door orientation (HORIZONTAL or VERTICAL)
            open: Initial open/closed state
            
        Returns:
            A new Door instance
        """
        x, y = grid_to_map(grid_x, grid_y)
        return cls(x, y, orientation, door_type)
        
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape and blocked areas into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        # Mark the door cell itself
        grid_x = int(self._x / CELL_SIZE)
        grid_y = int(self._y / CELL_SIZE)
        grid.mark_cell(grid_x, grid_y, ElementType.DOOR, element_idx)
        
        # Mark one blocked cell on each side of the door
        if self._orientation == DoorOrientation.HORIZONTAL:
            # Mark one cell before and after horizontally
            grid.mark_cell(grid_x - 1, grid_y, ElementType.BLOCKED, element_idx, blocked=True)
            grid.mark_cell(grid_x + 1, grid_y, ElementType.BLOCKED, element_idx, blocked=True)
        else:  # VERTICAL
            # Mark one cell before and after vertically
            grid.mark_cell(grid_x, grid_y - 1, ElementType.BLOCKED, element_idx, blocked=True)
            grid.mark_cell(grid_x, grid_y + 1, ElementType.BLOCKED, element_idx, blocked=True)
