"""Utility functions for room arrangement."""

from enum import Enum, auto
from typing import Dict, Optional, Set, Tuple
from tags import Tags
import skia
from logging_config import logger, LogTags
from graphics.math import Matrix2D, Point2D
from graphics.shapes import Rectangle
from map.room import Room, RoomType
from constants import CELL_SIZE
from graphics.aliases import Point
from map._arrange.arrange_enums import RoomDirection

def grid_points_to_grid_rect(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> Tuple[int, int, int, int]:
    """Convert grid points to a rectangle"""
    x = min(grid_x1, grid_x2)
    y = min(grid_y1, grid_y2)
    width = abs(grid_x2 - grid_x1) + 1
    height = abs(grid_y2 - grid_y1) + 1
    return (x, y, width, height)

def grid_line_to_grid_deltas(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> Tuple[int, int]:
    """Gets a delta direction for a line between two grid points."""
    dx = (grid_x2 - grid_x1) // abs(grid_x2 - grid_x1) if grid_x2 != grid_x1 else 0
    dy = (grid_y2 - grid_y1) // abs(grid_y2 - grid_y1) if grid_y2 != grid_y1 else 0
    return dx, dy

# Assumes a vertical or horizontal line
def grid_line_dist(grid_x1: int, grid_y1: int, grid_x2: int, grid_y2: int) -> int:
    """Get the distance between two grid points."""
    return abs(grid_x2 - grid_x1) + abs(grid_y2 - grid_y1) + 1 

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

def get_room_exit_grid_position(room: Room, direction: RoomDirection, wall_pos: float = 0.5, align_to: Point = None) -> Tuple[int, int]:
    """Get a grid position for exiting this room in the given direction.
    
    Args:
        room: The room to exit from
        direction: Which side of the room to exit from
        wall_pos: Position along the wall to exit from (0.0 to 1.0)
        align_to: Optional coordinate to snap to. For vertical passages (NORTH/SOUTH),
                 uses the x-coordinate. For horizontal passages (EAST/WEST), uses
                 the y-coordinate.
        
    Returns:
        Tuple of (grid_x, grid_y) for the exit point one cell outside the room
    """
    # Get room bounds in grid coordinates
    grid_x = int(room.bounds.x / CELL_SIZE)
    grid_y = int(room.bounds.y / CELL_SIZE)
    grid_width = int(room.bounds.width / CELL_SIZE)
    grid_height = int(room.bounds.height / CELL_SIZE)
    
    logger.debug(LogTags.ARRANGEMENT, 
        f"\nCalculating exit position:\n"
        f"  Room bounds: x={room.bounds.x}, y={room.bounds.y}, w={room.bounds.width}, h={room.bounds.height}\n"
        f"  Grid bounds: x={grid_x}, y={grid_y}, w={grid_width}, h={grid_height}")

    # For circular rooms, always exit from center
    if room.room_type == RoomType.CIRCULAR:
        wall_pos = 0.5

    # Calculate exit point along the wall
    if direction == RoomDirection.NORTH:
        x = grid_x + int((grid_width - 1) * wall_pos)
        y = grid_y - 1
    elif direction == RoomDirection.SOUTH:
        x = grid_x + int((grid_width - 1) * wall_pos)
        y = grid_y + grid_height
    elif direction == RoomDirection.EAST:
        x = grid_x + grid_width
        y = grid_y + int((grid_height - 1) * wall_pos)
    else:  # WEST
        x = grid_x - 1
        y = grid_y + int((grid_height - 1) * wall_pos)

    # If we have an align_to point, snap to its coordinate based on passage direction
    if align_to is not None:
        if direction in (RoomDirection.NORTH, RoomDirection.SOUTH):
            x = align_to[0]  # Vertical passages snap to x coordinate
        else:  # EAST, WEST
            y = align_to[1]  # Horizontal passages snap to y coordinate
            
    return (x, y)

def make_room_transform(room: Room, direction: RoomDirection, wall_pos: float = 0.5,
                       align_to: Optional[Tuple[int, int]] = None) -> Matrix2D:
    """Create a transform matrix for positioning relative to a room's exit.
    
    The transform creates a coordinate space where:
    - Origin is at the room's exit point
    - +X axis points in the forward direction
    - +Y axis points to the left
    
    Args:
        room: The source room
        direction: Direction to exit from
        wall_pos: Position along wall (0.0 to 1.0, 0.5 is center)
        align_to: Optional coordinate to snap to
        
    Returns:
        Matrix2D configured for the local coordinate space
    """
    # Get exit point and direction vectors
    exit_pos = get_room_exit_grid_position(room, direction, wall_pos, align_to=align_to)
    forward = direction.get_forward()
    left = direction.get_left()
    
    # Create transform matrix
    transform = Matrix2D()
    
    # Set forward and left vectors as matrix columns
    transform.a = forward[0]  # Forward X
    transform.c = forward[1]  # Forward Y
    transform.b = left[0]     # Left X
    transform.d = left[1]     # Left Y
    
    # Set translation to exit point
    transform.tx = exit_pos[0]
    transform.ty = exit_pos[1]
    
    return transform

def get_size_index_from_tags(tags: Set[str]) -> int:
    """Get the size index (0=small, 1=medium, 2=large) from a set of tags.
    
    Uses the largest size tag present, defaults to small (0) if no size tags.
    """
    if str(Tags.LARGE) in tags:
        return 2
    elif str(Tags.MEDIUM) in tags:
        return 1
    return 0  # Default to small

def get_adjacent_room_rect(room: Room, direction: RoomDirection, grid_dist: int, \
                           grid_breadth: int, grid_depth: int, \
                           breadth_offset: float = 0.0, wall_pos: float = 0.5, \
                           align_to: Optional[Tuple[int, int]] = None) -> Tuple[int, int, int, int]:
    """Return the rectangle for a new passage and new room tht is grid_dist in the given direction
    from the existing room, with the breadth (forward diretion width relative width) and depth 
    (forward direction relative lentgth) of the new room.
    
    Args:
        room: Existing room
        direction: Direction to create the new room
        grid_dist: Distance to the new room
        grid_breadth: Width of the new room from the prespective of facing forward
        grid_depth: Length of the new room from the perspective of facing forward
        breadth_offset: A float shift value to right/left of the new rooms placement (for alternating how room grid positions round)
    
    Returns:
        Tuple of rect of new room relative to passage start point."""
    # Get transform for local coordinate space
    transform = make_room_transform(room, direction, wall_pos, align_to)
    
    logger.debug(LogTags.ARRANGEMENT,
        f"\nCalculating room position: dir={direction}, dist={grid_dist}, breadth={grid_breadth}, depth={grid_depth}\n"
        f"Transform matrix: [{transform.a:.1f} {transform.b:.1f} {transform.tx:.1f}] [{transform.c:.1f} {transform.d:.1f} {transform.ty:.1f}]")
    
    # Calculate passage points. We step from the room exit to the far room's exit.
    # Then we step into the room one grid, and go to the near left corner grid, then we move
    # from there to the far right corener grid. This gives us all the key points we 
    # need to calculate the passage and room rectangles.

    p1 = Point2D(0, 0)                  # Start gridi of passage
    p2 = Point2D(grid_dist - 1, 0)      # End grid of passage

    # Calculate room corners in local space, ensuring integer grid positions
    breadth_center = (grid_breadth - 1) // 2  # Integer division for center
    r1 = p2 + Point2D(1, -breadth_center + int(breadth_offset))  # Near left grid corner of room
    r2 = r1 + Point2D(grid_depth - 1, grid_breadth - 1) # Far right grid corner of room

    logger.debug(LogTags.ARRANGEMENT,
        f"Local points: passage=p1({p1.x}, {p1.y}), p2({p2.x}, {p2.y}), room=r1({r1.x}, {r1.y}), r2({r2.x}, {r2.y})")
    
    # Transform points to world space
    w_p1 = transform.transform_point(p1)
    w_p2 = transform.transform_point(p2)
    w_r1 = transform.transform_point(r1)
    w_r2 = transform.transform_point(r2)
    
    logger.debug(LogTags.ARRANGEMENT,
        f"World points: passage=p1({w_p1.x:.1f}, {w_p1.y:.1f}), p2({w_p2.x:.1f}, {w_p2.y:.1f}), "
        f"room=r1({w_r1.x:.1f}, {w_r1.y:.1f}), r2({w_r2.x:.1f}, {w_r2.y:.1f})")
    
    # Calculate final rectangle in both spaces
    local_rect = (
        int(min(r1.x, r2.x)),
        int(min(r1.y, r2.y)),
        int(abs(r2.x - r1.x)) + 1,
        int(abs(r2.y - r1.y)) + 1
    )
    
    # Calculate final rectangle in world space
    final_rect = (
        int(min(w_r1.x, w_r2.x)),
        int(min(w_r1.y, w_r2.y)), 
        int(abs(w_r2.x - w_r1.x)) + 1,
        int(abs(w_r2.y - w_r1.y)) + 1
    )
    
    logger.debug(LogTags.ARRANGEMENT,
        f"Rects: local=({local_rect[0]}, {local_rect[1]}, {local_rect[2]}, {local_rect[3]}), "
        f"world=({final_rect[0]}, {final_rect[1]}, {final_rect[2]}, {final_rect[3]})")
    return final_rect
