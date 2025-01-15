"""Room arrangement strategies for dungeon map generation.

This module provides different strategies for arranging rooms in a dungeon map:

Includes functions for:
- Creating connected rooms with passages and doors
- Arranging rooms in different patterns (linear, symmetric, spiral)
- Managing room shapes and sizes

Available arrangement styles:
- ArrangeSymmetric: Arranges rooms in symmetrical patterns, attempting to maintain
  left/right balance where possible. Good for formal dungeon layouts like temples.
- ArrangeLinear: Arranges rooms in a more or less linear fashion, good for
  dungeons that tell a story or represent a journey from start to finish.
- ArrangeSpiral: Arranges rooms in a spiral pattern expanding outward from the
  center. Good for creating maze-like dungeons that loop back on themselves.
"""

from enum import Enum, auto
import random
from typing import List, Optional, Tuple

from constants import CELL_SIZE
from graphics.math import Point2D
from graphics.shapes import Circle
from map._arrange.arrange_utils import (
    get_room_direction, get_room_exit_grid_position,
    grid_points_to_grid_rect, grid_line_to_grid_deltas,
    grid_line_dist, get_adjacent_room_rect, RoomDirection
)
from map._arrange.passage_distribution import PassageConfig
from map._arrange.room_distribution import RoomShape, get_random_room_shape
from map.door import Door, DoorOrientation, DoorType
from map.enums import Direction
from map.map import Map
from map.mapelement import MapElement
from map.passage import Passage
from map.room import Room, RoomType
from options import Options

class GrowDirection(Enum):
    """Direction to grow rooms during arrangement."""
    FORWARD = auto()
    BACKWARD = auto()
    BOTH = auto()

def connect_rooms(
    room1: Room,
    room2: Room,
    start_door_type: Optional[DoorType] = None,
    end_door_type: Optional[DoorType] = None,
    align_to: Optional[Tuple[int, int]] = None
) -> Tuple[Optional[Door], Optional[Passage], Optional[Door]]:
    """Create a passage between two rooms with optional doors.
    
    Args:
        room1: First room to connect
        room2: Second room to connect 
        start_door_type: Optional door type at start of passage
        end_door_type: Optional door type at end of passage
        
    Returns:
        Tuple of (start_door, passage, end_door) where doors may be None
    """
    map = room1.map

    # Get the primary direction between rooms
    r1_dir = get_room_direction(room1, room2)
    
    # Get the opposite direction for room2
    r2_dir = r1_dir.get_opposite()
            
    # Get connection points in grid coordinates
    r1_x, r1_y = get_room_exit_grid_position(room1, r1_dir, align_to=align_to)
    r2_x, r2_y = get_room_exit_grid_position(room2, r2_dir, align_to=(r1_x, r1_y))

    # Make sure we don't have too many doors
    dist = grid_line_dist(r1_x, r1_y, r2_x, r2_y)
    if start_door_type is not None and end_door_type is not None and dist <= 2:
        raise ValueError("Cannot have two doors in a passage 2 grids or smaller")

    # Deltas
    dx, dy = grid_line_to_grid_deltas(r1_x, r1_y, r2_x, r2_y)

    door1: Optional[Door] = None
    door2: Optional[Door] = None
    passage: Optional[Passage] = None

    # Set door orientation based on room direction
    door_orientation = (
        DoorOrientation.HORIZONTAL 
        if r1_dir in (RoomDirection.EAST, RoomDirection.WEST)
        else DoorOrientation.VERTICAL
    )

    if dist > 0 and start_door_type is not None:
        door1 = Door.from_grid(r1_x, r1_y, door_orientation, door_type=start_door_type)
        map.add_element(door1)
        r1_x += dx
        r1_y += dy
        dist -= 1

    if dist > 0 and end_door_type is not None:
        door2 = Door.from_grid(r2_x, r2_y, door_orientation, door_type=end_door_type)
        map.add_element(door2)
        r2_x -= dx
        r2_y -= dy
        dist -= 1

    if dist > 0:
        # Calculate passage rect in grid coordinates
        passage_x = min(r1_x, r2_x)
        passage_y = min(r1_y, r2_y)
        passage_width = abs(r2_x - r1_x) + 1
        passage_height = abs(r2_y - r1_y) + 1
        
        print(f"\nPassage dimensions:")
        print(f"  Start point: ({r1_x}, {r1_y})")
        print(f"  End point: ({r2_x}, {r2_y})")
        print(f"  Grid rect: ({passage_x}, {passage_y}, {passage_width}, {passage_height})")
        print(f"  Size: {passage_width}x{passage_height}")
        
        passage = Passage.from_grid(passage_x, passage_y, passage_width, passage_height)
        map.add_element(passage)
    
    # Connect everything based on which door types were specified
    elems: List[MapElement] = [room1]    
    if start_door_type is not None:
        elems.append(door1)
    if passage is not None:
        elems.append(passage)
    if end_door_type is not None:
        elems.append(door2)
    elems.append(room2)

    for i in range(len(elems) - 1):
        elems[i].connect_to(elems[i + 1])
        
    return door1, passage, door2

def try_create_connected_room(
    source_room: Room,
    direction: RoomDirection,
    distance: int,
    room_breadth: int,
    room_depth: int,
    room_type: Optional[RoomType] = None,
    start_door_type: Optional[DoorType] = None,
    end_door_type: Optional[DoorType] = None,
    breadth_offset: float = 0.0,
    align_to: Optional[Tuple[int, int]] = None
) -> Tuple[Room, Optional[Door], Passage, Optional[Door]]:
    """Attempt to create a new room connected to an existing room via a passage.
        
    Creates a new Room of the specified type and size, positioned in the given direction
    and distance from the source room. The rooms are connected by a Passage with optional
    doors at either end. The room will only be created if the space is unoccupied.
        
    Args:
        source_room: The existing room to connect from
        direction: Direction to create the new room
        distance: Grid distance to place the new room (must be > 0)
        room_breadth: Width perpendicular to growth direction (must be > 0)
        room_depth: Length parallel to growth direction (must be > 0)
        room_type: Optional RoomType (defaults to RECTANGULAR)
        start_door_type: Optional DoorType for start of passage
        end_door_type: Optional DoorType for end of passage
            
    Returns:
        Tuple of (new_room, start_door, passage, end_door) where all elements will be None
        if the room cannot be placed in the desired location.
    """    
    # Validate inputs
    if distance <= 0:
        raise ValueError("Distance must be positive")
    if room_breadth * room_depth <= 0:
        raise ValueError("Room dimensions must be positive")
            
    # Create room shape
    room_shape = RoomShape(room_type or RoomType.RECTANGULAR, room_breadth, room_depth)
    
    # Get room rect in grid coordinates using arrange utils
    new_room_x, new_room_y, new_room_width, new_room_height = get_adjacent_room_rect(
        source_room, direction, distance, room_breadth, room_depth,
        wall_pos=0.5,
        align_to=align_to
    )
        
    # Check if position is valid using occupancy grid
    test_room = Room.from_grid(
        new_room_x,
        new_room_y, 
        new_room_width,
        new_room_height,
        room_type=room_type or RoomType.RECTANGULAR
    )
    
    if not source_room.map.occupancy.check_rectangle(test_room.bounds):
        return None, None, None, None
        
    # Create the new room
    new_room = source_room.map.add_element(test_room)
    
    # Connect the rooms using the utility function
    start_door_elem, passage, end_door_elem = connect_rooms(
        source_room, new_room,
        start_door_type=start_door_type,
        end_door_type=end_door_type,
        align_to=align_to
    )
    
    return new_room, start_door_elem, passage, end_door_elem

def arrange_rooms(
    dungeon_map: Map,
    min_rooms: int = 3,
    max_rooms: int = 7,
    min_size: int = 3,
    max_size: int = 7,
    start_room: Optional[Room] = None
) -> List[Room]:
    """Arrange rooms using a mix of strategies.
    
    Args:
        dungeon_map: The map to add rooms to
        min_rooms: Minimum number of rooms to create
        max_rooms: Maximum number of rooms to create
        min_size: Minimum room size in grid units
        max_size: Maximum room size in grid units
        start_room: Optional starting room
        
    Returns:
        List of created Room instances
    """
    from map._arrange.strategy_distribution import get_random_arrange_strategy
    
    # Create start room if none provided
    if start_room is None:
        start_room = dungeon_map.create_rectangular_room(0, 0,
            random.randint(min_size, max_size),
            random.randint(min_size, max_size))
    
    # Initialize
    total_rooms = random.randint(min_rooms, max_rooms)
    rooms_left = total_rooms - 1  # Subtract start room
    room_queue = [start_room]  # Queue of rooms to grow from
    all_rooms = [start_room]
    
    STRATEGY_ATTEMPTS = 3

    # Keep growing until we hit target room count or run out of rooms to grow from
    while rooms_left > 0 and room_queue:
        # Get next room to grow from
        current_room = room_queue.pop(0)
        
        # Try the same room with different strategies multiple times
        success = False
        for _ in range(STRATEGY_ATTEMPTS):
            # Get random strategy and its parameters
            strategy_class, strategy_params = get_random_arrange_strategy(dungeon_map.options, gen_data={"map": dungeon_map})
            
            # Limit rooms to generate based on remaining count
            strategy_params.max_rooms = min(strategy_params.max_rooms, rooms_left)
            
            # Create and execute strategy
            strategy = strategy_class(dungeon_map, strategy_params)
            new_rooms = strategy.execute(rooms_left, current_room)
            
            if new_rooms:
                # Add new rooms to queue and tracking lists
                room_queue.extend(new_rooms)
                all_rooms.extend(new_rooms)
                rooms_left -= len(new_rooms)
                success = True
                break
                
        # If all attempts failed, just continue to next room in queue
        if not success:
            continue
        
    return all_rooms
