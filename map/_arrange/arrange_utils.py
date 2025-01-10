"""Utility functions for room arrangement."""

from enum import Enum, auto
from typing import Dict, Tuple
from map.room import Room, RoomType
from constants import CELL_SIZE

class Direction(Enum):
    """Direction to generate rooms."""
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
    
    def get_opposite(self) -> 'Direction':
        """Get the opposite direction."""
        return OPPOSITE_DIRECTIONS[self]

# Mapping of directions to their opposites
OPPOSITE_DIRECTIONS: Dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST
}

def get_room_direction(room1: Room, room2: Room) -> Direction:
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
        return Direction.EAST if dx > 0 else Direction.WEST
    else:
        return Direction.SOUTH if dy > 0 else Direction.NORTH

def get_room_exit_grid_position(room: Room, direction: Direction, wall_pos: float = 0.5) -> Tuple[int, int]:
    """Get a grid position for exiting this room in the given direction.
    
    Args:
        room: The room to exit from
        direction: Which side of the room to exit from
        wall_pos: Position along the wall to exit from (0.0 to 1.0)
        
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
    
    # Calculate exit point along the wall
    if direction == Direction.NORTH:
        return (grid_x + int((grid_width - 1) * wall_pos), grid_y - 1)  # One cell above
    elif direction == Direction.SOUTH:
        return (grid_x + int((grid_width - 1) * wall_pos), grid_y + grid_height)  # One cell below
    elif direction == Direction.EAST:
        return (grid_x + grid_width, grid_y + int((grid_height - 1) * wall_pos))  # One cell right
    else:  # WEST
        return (grid_x - 1, grid_y + int((grid_height - 1) * wall_pos))  # One cell left
