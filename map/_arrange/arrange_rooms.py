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
from logging_config import logger, LogTags
from graphics.conversions import map_to_grid
from graphics.math import Point2D
from graphics.shapes import Circle, Rectangle
from map._arrange.arrange_utils import (
    get_room_direction, grid_points_to_grid_rect, grid_line_to_grid_deltas,
    grid_line_dist, get_adjacent_room_rect
)
from map._arrange.passage_distribution import PassageConfig
from map._arrange.room_distribution import RoomShape, get_random_room_shape
from map.door import Door, DoorOrientation, DoorType
from map.enums import Direction, RoomDirection
from map.map import Map
from map.mapelement import MapElement
from map.occupancy import ElementType
from map.passage import Passage
from map.room import Room, RoomType
from options import Options
from tags import Tags

class GrowDirection(Enum):
    """Direction to grow rooms during arrangement."""
    FORWARD = auto()
    BACKWARD = auto()
    BOTH = auto()

def try_connect_rooms(
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
            
    # Check if passage positions are fixed
    constrained = (room1.room_type == RoomType.CIRCULAR and \
                  room2.room_type == RoomType.CIRCULAR) or \
                  align_to is not None

    crossed_passages: List[Tuple[int, int, int]] = []

    # Try to find an entry/exit point pair from the room that aren't blocked
    tries = 0
    max_tries = 1 if constrained else 4
    valid = False
    while tries < max_tries:

        # Get connection points in grid coordinates
        if align_to is not None:
            r1_x, r1_y = room1.get_exit(r1_dir, align_to=align_to)
            r2_x, r2_y = room2.get_exit(r2_dir, align_to=align_to)
        else:
            r1_x, r1_y = room1.get_exit(r1_dir, wall_pos=random.random())
            r2_x, r2_y = room2.get_exit(r2_dir, align_to=(r1_x, r1_y))

        dist = grid_line_dist(r1_x, r1_y, r2_x, r2_y)

        # Check passage area in grid coordinates
        passage_rect = grid_points_to_grid_rect(r1_x, r1_y, r2_x, r2_y)
        valid, crossed_passages = map.occupancy.check_passage(Rectangle(*passage_rect), r1_dir)

        if crossed_passages and dist <= 3:
            valid = False

        # We're constrained on both ends, so give up
        if not valid and constrained:
            return None, None, None
        
        tries += 1

    if not valid:
        return None, None, None

    # Make sure we don't have too many doors
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

    door1: Optional[Door] = None
    if dist > 0 and start_door_type is not None and \
            map.occupancy.check_door(r1_x, r1_y):
        door1 = Door.from_grid(r1_x, r1_y, door_orientation, door_type=start_door_type)
        map.add_element(door1)
        r1_x += dx
        r1_y += dy
        dist -= 1

    door2: Optional[Door] = None
    if dist > 0 and end_door_type is not None and \
            map.occupancy.check_door(r2_x, r2_y):
        door2 = Door.from_grid(r2_x, r2_y, door_orientation, door_type=end_door_type)
        map.add_element(door2)
        r2_x -= dx
        r2_y -= dy
        dist -= 1

    passage: Optional[Passage] = None
    if dist > 0:
        # Calculate passage rect in grid coordinates
        passage_x = min(r1_x, r2_x)
        passage_y = min(r1_y, r2_y)
        passage_width = abs(r2_x - r1_x) + 1
        passage_height = abs(r2_y - r1_y) + 1
        
        logger.debug(LogTags.ARRANGEMENT,
            f"\nPassage dimensions:\n"
            f"  Start point: ({r1_x}, {r1_y})\n"
            f"  End point: ({r2_x}, {r2_y})\n"
            f"  Grid rect: ({passage_x}, {passage_y}, {passage_width}, {passage_height})\n"
            f"  Size: {passage_width}x{passage_height}")
        
        # Create and add passage
        passage = Passage.from_grid(passage_x, passage_y, passage_width, passage_height)
        passage = map.add_element(passage)
    
    # Connect everything based on which door types were specified
    elems: List[MapElement] = [room1]    
    if door1 is not None:
        elems.append(door1)
    if passage is not None:
        elems.append(passage)
    if door2 is not None:
        elems.append(door2)
    elems.append(room2)

    # Log the connections being made
    map = room1.map
    logger.debug(LogTags.ARRANGEMENT, 
        f"Connecting elements: {[map.elements.index(e) for e in elems]}")

    for i in range(len(elems) - 1):
        elems[i].connect_to(elems[i + 1])
    
    # Connect our passage to any passages it crossed
    if passage is not None:
        for i in crossed_passages:
            cross_passage = map.get_element_at(i)
            passage.connect_to(cross_passage)

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
            
    map = source_room.map

    if room_type is None:
        room_type = RoomType.RECTANGULAR
    
    # Get room rect in grid coordinates using arrange utils
    new_room_x, new_room_y, new_room_width, new_room_height = get_adjacent_room_rect(
        source_room, direction, distance, room_breadth, room_depth,
        wall_pos=0.5,
        align_to=align_to
    )
    
    if room_type == RoomType.CIRCULAR:
        # Check if position is valid using occupancy grid
        radius = room_breadth / 2
        test_circle = Circle(new_room_x + radius, new_room_y + radius, radius)
        if not map.occupancy.check_circle(test_circle):
            return None, None, None, None
    else:
        test_rect = Rectangle(new_room_x, new_room_y, new_room_width, new_room_height)
        if not map.occupancy.check_rectangle(test_rect):
            return None, None, None, None
        
    # Create the new room and add it to the map
    new_room = Room.from_grid(
        new_room_x,
        new_room_y, 
        new_room_width,
        new_room_height,
        room_type=room_type or RoomType.RECTANGULAR
    )
    source_room.map.add_element(new_room)
    
    # Connect the rooms using the utility function
    start_door_elem, passage, end_door_elem = try_connect_rooms(
        source_room, new_room,
        start_door_type=start_door_type,
        end_door_type=end_door_type,
        align_to=align_to
    )

    # Failed to connect rooms, remove the room and exit
    if start_door_elem is None and passage is None and end_door_elem is None:
        # Failed to connect rooms, remove the test room
        source_room.map.remove_element(new_room)
        return None, None, None, None
    
    return new_room, start_door_elem, passage, end_door_elem

def try_connect_nearby_rooms(dungeon_map: Map, options: Options) -> bool:
    """Try to connect rooms that are near each other but not already connected.
    
    Args:
        dungeon_map: The map to process
        max_connection_dist: Maximum grid distance to search for potential connections
    """
    # Get list of all rooms
    rooms = list(dungeon_map.rooms)
    
    if Tags.LARGE in options.tags:
        max_connection_dist = 9
        max_tries = 12
    elif Tags.MEDIUM in options.tags:
        max_connection_dist = 7
        max_tries = 10
    else:
        max_connection_dist = 5
        max_tries = 8

    # Try connecting each room to others
    for source_room in rooms:
        # Get existing connections
        connected_rooms = {conn for conn in source_room.connections if isinstance(conn, Room)}
        
        # Get room bounds in grid coordinates
        bounds = source_room.bounds
        grid_x, grid_y = map_to_grid(bounds.x, bounds.y)
        
        # Search in random positions within radius
        for _ in range(max_tries):  # Try up to 8 random positions per room
            # Pick random offset within max distance
            dx = random.randint(-max_connection_dist, max_connection_dist)
            dy = random.randint(-max_connection_dist, max_connection_dist)
            
            # Get target position
            target_x = grid_x + dx
            target_y = grid_y + dy
            
            # Check occupancy at target
            element_idx = dungeon_map.occupancy.get_element_index(target_x, target_y)
            if element_idx >= 0:
                target_elem = dungeon_map.elements[element_idx]
                
                # If we found a different room we're not connected to, try connecting
                if (isinstance(target_elem, Room) and 
                    target_elem != source_room and
                    target_elem not in connected_rooms):
                    
                    # Try to connect the rooms
                    d1, p, d2, = try_connect_rooms(source_room, target_elem)
                    if d1 is not None or p is not None or d2 is not None:
                        return True
                    
    return False

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
        logger.debug(LogTags.ARRANGEMENT, f"Created start room (element {len(dungeon_map.elements)-1})")
    
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
            strategy_class, strategy_params = get_random_arrange_strategy(dungeon_map.options)
            
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
                
                # Log the new rooms that were created
                for room in new_rooms:
                    room_idx = dungeon_map.elements.index(room)
                    logger.debug(LogTags.ARRANGEMENT, 
                        f"Created new room (element {room_idx}) using {strategy_class.__name__}")
                break
                
        # If all attempts failed, just continue to next room in queue
        if not success:
            continue
        
    return all_rooms
