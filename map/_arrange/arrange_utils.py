"""Utility functions for room arrangement."""

from enum import Enum, auto
from typing import Dict, Tuple
from algorithms.math import Point2D
from algorithms.shapes import Rectangle
from map.room import Room, RoomType
from constants import CELL_SIZE
from algorithms.types import Point

def grid_points_to_grid_rect(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> Tuple[int, int, int, int]:
    """Convert grid points to a rectangle"""
    x = min(grid_x1, grid_x2)
    y = min(grid_y1, grid_y2)
    width = abs(grid_x2 - grid_x1) + 1
    height = abs(grid_y2 - grid_y1) + 1
    return (x, y, width, height)

def grid_line_to_grid_deltas(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> Tuple[int, int]:
    """Gets a delta direction for a line between two grid points."""
    dx = grid_x2 - grid_x1 / abs(grid_x2 - grid_x1) if grid_x2 != grid_x1 else 0
    dy = grid_y2 - grid_y1 / abs(grid_y2 - grid_y1) if grid_y2 != grid_y1 else 0
    return dx, dy

# Assumes a vertical or horizontal line
def grid_line_dist(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> int:
    """Get the distance between two grid points."""
    return abs(grid_x2 - grid_x1) + abs(grid_y2 - grid_y1) + 1

class RoomDirection(Enum):
    """Direction to generate rooms."""
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
    
    def get_opposite(self) -> 'RoomDirection':
        """Get the opposite direction."""
        return OPPOSITE_DIRECTIONS[self]
        
    def get_forward(self) -> Tuple[int, int]:
        """Get the (dx, dy) grid offset for this direction."""
        if self == RoomDirection.NORTH:
            return (0, -1)
        elif self == RoomDirection.SOUTH:
            return (0, 1)
        elif self == RoomDirection.EAST:
            return (1, 0)
        else:  # WEST
            return (-1, 0)
        
    def get_left(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the left direction."""
        if self == RoomDirection.NORTH:
            return (-1, 0)
        elif self == RoomDirection.SOUTH:
            return (1, 0)
        elif self == RoomDirection.EAST:
            return (0, -1)
        else:
            return (0, 1)   

# Mapping of directions to their opposites
OPPOSITE_DIRECTIONS: Dict[RoomDirection, RoomDirection] = {
    RoomDirection.NORTH: RoomDirection.SOUTH,
    RoomDirection.SOUTH: RoomDirection.NORTH,
    RoomDirection.EAST: RoomDirection.WEST,
    RoomDirection.WEST: RoomDirection.EAST
}

def get_room_direction(room1: Room, room2: Room) -> RoomDirection:
    """Determine the primary direction from room1 to room2.
    
    Args:
        room1: Source room
        room2: Target room
        
    Returns:
        Direction from room1 to room2 (NORTH, SOUTH, EAST, or WEST)
    """
    # Compare center points
    dx = room2.bounds.x - room1.bounds.x
    dy = room2.bounds.y - room1.bounds.y
    
    # Use the larger distance to determine primary direction
    if abs(dx) > abs(dy):
        return RoomDirection.EAST if dx > 0 else RoomDirection.WEST
    else:
        return RoomDirection.SOUTH if dy > 0 else RoomDirection.NORTH

def get_room_exit_grid_position(room: Room, direction: RoomDirection, wall_pos: float = 0.5, grid_origin: Point = None) -> Tuple[int, int]:
    """Get a grid position for exiting this room in the given direction.
    
    Args:
        room: The room to exit from
        direction: Which side of the room to exit from
        wall_pos: Position along the wall to exit from (0.0 to 1.0)
        origin: Optional passage origin grid position to use to set wall_pos
        
    Returns:
        Tuple of (grid_x, grid_y) for the exit point one cell outside the room
    """
    if room.room_type == RoomType.CIRCULAR:
        wall_pos = 0.5  # Always exit from center for circular rooms

    # Get room bounds in grid coordinates
    grid_x = int(room.bounds.x / CELL_SIZE)
    grid_y = int(room.bounds.y / CELL_SIZE)
    grid_width = int(room.bounds.width / CELL_SIZE)
    grid_height = int(room.bounds.height / CELL_SIZE)

    # If we have an origin grid point for the passage, 
    if grid_origin is not None: 
        if direction == RoomDirection.NORTH or direction == RoomDirection.SOUTH:
            wall_pos = (grid_origin[0] - grid_x) / (grid_width - 1)
        else:
            wall_pos = (grid_origin[1] - grid_y) / (grid_height - 1)
        if wall_pos < 0.0:
            wall_pos = 0.0
        elif wall_pos > 1.0:
            wall_pos = 1.0

    # Calculate exit point along the wall
    if direction == RoomDirection.NORTH:
        return (grid_x + int((grid_width - 1) * wall_pos), grid_y - 1)  # One cell above
    elif direction == RoomDirection.SOUTH:
        return (grid_x + int((grid_width - 1) * wall_pos), grid_y + grid_height)  # One cell below
    elif direction == RoomDirection.EAST:
        return (grid_x + grid_width, grid_y + int((grid_height - 1) * wall_pos))  # One cell right
    else:  # WEST
        return (grid_x - 1, grid_y + int((grid_height - 1) * wall_pos))  # One cell left

def get_adjacent_room_rect(room: Room, direction: RoomDirection, grid_dist: int, \
                           room_breadth: int, room_depth: int) -> Tuple[Rectangle, Rectangle]:
    """Return the rectangle for a new passage and new room tht is grid_dist in the given direction
    from the existing room, with the breadth (forward diretion width relative width) and depth 
    (forward direction relative lentgth) of the new room.
    
    Args:
        room: Existing room
        direction: Direction to create the new room
        grid_dist: Distance to the new room
        room_breadth: Width of the new room in the forward direction
        room_depth: Length of the new room in the forward direction
    
    Returns:
        Tuple of (passage rect, room)"""  
    forward = Point2D(direction.get_forward())
    left = Point2D(direction.get_left())
    # Start from the room's exit grid (exit grid cell outside of room)
    p0 = Point2D(get_room_exit_grid_position(room, direction))
    # Go forward to grid at end of passage outside the new room
    p1 = p0 + forward * (grid_dist - 1)
    # Go one grid forward, then room_breadth/2 to the left
    p2 = p1 + forward + left * int((room_breadth - 1) / 2)
    # Go room_depth - 1 forward, then room_breadth - 1 to the right
    p3 = p2 + forward * (room_depth - 1) + -left * (room_breadth - 1)
    return ( \
        Rectangle(min(p2.x, p3.x), min(p2.y, p2.y), abs(p3.x - p2.x) + 1, abs(p3.y - p2.y) + 1), \
        Rectangle(min(p2.x, p3.x), min(p2.y, p2.y), abs(p3.x - p2.x) + 1, abs(p3.y - p2.y) + 1) \
        )