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
from typing import List, Optional, Tuple
import random

from algorithms.math import Point2D
from options import Options
from algorithms.shapes import Circle
from constants import CELL_SIZE
from map._arrange.room_shapes import RoomShape, make_room_shape

from map.door import Door, DoorOrientation, DoorType
from map.enums import Direction
from map.map import Map
from map.mapelement import MapElement
from map.passage import Passage
from map.room import Room, RoomType

from map._arrange.arrange_utils import (
    get_room_direction, get_room_exit_grid_position,
    grid_points_to_grid_rect, grid_line_to_grid_deltas, 
    grid_line_dist, get_adjacent_room_rect, RoomDirection
)
from map._arrange.passage_distribution import PassageConfig

class GrowDirection(Enum):
    """Controls which room to grow from when arranging."""
    FORWARD = auto()   # Only grow from last room
    BACKWARD = auto()  # Only grow from first room
    BOTH = auto()      # Grow from either first or last room

class ArrangeRoomStyle(Enum):
    """Room arrangement strategies."""
    SYMMETRIC = auto()  # Arrange rooms symmetrically where possible
    LINEAR = auto()     # Arrange rooms in a roughly linear path
    SPIRAL = auto()     # Arrange rooms in a spiral pattern from center

class GenerateDirection(Enum):
    """Direction to generate new rooms from."""
    BOTH = auto()      # Generate from either first or last room
    FORWARD = auto()   # Generate only from first room
    BACKWARD = auto()  # Generate only from last room

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
    room_shape = make_room_shape(room_type or RoomType.RECTANGULAR, room_breadth, room_depth)
    
    # Get room rect in grid coordinates using arrange utils
    new_room_x, new_room_y, new_room_width, new_room_height = get_adjacent_room_rect(
        source_room, direction, distance, room_breadth, room_depth,
        breadth_offset=breadth_offset,
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


class _RoomArranger:
    """Helper class for arranging rooms with shared state."""
    
    def __init__(
        self,
        dungeon_map: Map,
        min_size: int,
        max_size: int,
        min_spacing: int = 3,
        max_spacing: int = 6
    ):
        self.dungeon_map = dungeon_map
        self.min_size = min_size
        self.max_size = max_size
        self.min_spacing = min_spacing
        self.max_spacing = max_spacing
        self.options = dungeon_map.options
        self.rooms: List[Room] = []
        
    def create_room(self, entrance_grid_x: float, entrance_grid_y: float) -> Room:
        """Create a room at the given grid position."""
        # Sanity checks for position
        if abs(entrance_grid_x) > 1000 or abs(entrance_grid_y) > 1000:
            raise ValueError(f"Room position ({entrance_grid_x}, {entrance_grid_y}) is too far from origin")
        
        width = height = 0
        while width * height < 6: # 2x3 minimum room size
            width = random.randint(self.min_size, self.max_size)
            height = random.randint(self.min_size, self.max_size)
        
        # Sanity checks for dimensions
        if width > 100 or height > 100:
            raise ValueError(f"Room dimensions {width}x{height} exceed maximum allowed size")
        print(f"\nGenerating room {len(self.rooms) + 1}:")
        print(f"  Grid position: ({entrance_grid_x}, {entrance_grid_y})")
        print(f"  Grid size: {width}x{height}")

        room = self.dungeon_map.add_rectangular_room(entrance_grid_x, entrance_grid_y, width, height)
        print(f"  Map bounds: ({room.bounds.x}, {room.bounds.y}) to ({room.bounds.x + room.bounds.width}, {room.bounds.y + room.bounds.height})")
        self.rooms.append(room)
        return room

    def arrange_linear(
        self,
        num_rooms: int,
        start_room: Room,
        direction: 'RoomDirection',
        grow_direction: GrowDirection = GrowDirection.FORWARD,
        max_attempts: int = 100,
        branch_chance: float = 0.4
    ) -> List[Room]:
        """Arrange rooms in a branching sequence.
        
        Args:
            num_rooms: Number of rooms to generate
            start_room: Starting room to build from
            direction: Primary direction to grow in
            grow_direction: Controls which room to grow from
            max_attempts: Maximum attempts before giving up
            branch_chance: Chance (0-1) to start a new branch each room
            
        Returns:
            List of created rooms
        """
        from map._arrange.room_shapes import get_random_room_shape, RoomShape
        
        self.rooms = [start_room]  # Reset rooms list
        first_room = last_room = start_room
        last_shape = None
        
        # Calculate initial passage point from first room
        initial_passage_point = get_room_exit_grid_position(
            start_room,
            direction,
            wall_pos=0.5
        )
            
        attempts = 0
        while len(self.rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            
            # Possibly start a new branch
            if random.random() < branch_chance and len(self.rooms) < num_rooms - 1:
                # Pick a random room to branch from
                source_room = random.choice(self.rooms)
                
                # Pick a new random direction excluding current
                possible_dirs = [
                    RoomDirection.NORTH, RoomDirection.SOUTH,
                    RoomDirection.EAST, RoomDirection.WEST
                ]
                possible_dirs.remove(direction)
                new_direction = random.choice(possible_dirs)
                
                # Pick a random grow mode
                new_grow_mode = random.choice(list(GrowDirection))
                
                # Recursively arrange a new branch
                remaining_rooms = num_rooms - len(self.rooms)
                if remaining_rooms > 1:
                    branch_size = random.randint(1, remaining_rooms - 1)
                    self.arrange_linear(
                        branch_size,
                        source_room,
                        new_direction,
                        new_grow_mode,
                        max_attempts,
                        branch_chance * 0.5  # Reduce branch chance for sub-branches
                    )
                    
            # Continue main sequence
            grow_from_first = (
                random.random() < 0.5 if grow_direction == GrowDirection.BOTH
                else grow_direction == GrowDirection.BACKWARD
            )
            
            # Set source room and growth direction
            if grow_from_first:
                source_room = first_room
                connect_dir = direction.get_opposite()
            else:
                source_room = last_room
                connect_dir = direction
                
            # Get random room shape using map options
            room_shape = get_random_room_shape(last_shape, options=source_room.map.options)
            print(f"\nRoom shape selected:")
            print(f"  Type: {room_shape.room_type}")
            print(f"  Breadth: {room_shape.breadth}")
            print(f"  Depth: {room_shape.depth}")
            print(f"  Offset: {room_shape.breadth_offset}")
            
            # Get passage configuration using our distribution system
            from map._arrange.passage_distribution import get_random_passage_config
            passage_config = get_random_passage_config(self.options)
            print(f"Passage config:")
            print(f"  Length: {passage_config.length}")
            print(f"  Start door: {passage_config.doors.start_door}")
            print(f"  End door: {passage_config.doors.end_door}")
            
            # Extract configuration
            distance = passage_config.length
            start_door = passage_config.doors.start_door
            end_door = passage_config.doors.end_door

            # Try to create connected room with retries for different shapes/positions
            new_room = None
            retry_count = 0
            max_shape_retries = 3
            
            while new_room is None and retry_count < max_shape_retries:
                new_room, start_door, passage, end_door = try_create_connected_room(
                    source_room,
                    connect_dir,
                    distance,
                    room_shape.breadth,
                    room_shape.depth,
                    room_type=room_shape.room_type,
                    start_door_type=start_door,
                    end_door_type=end_door,
                    breadth_offset=room_shape.breadth_offset,
                    align_to=initial_passage_point
                )
                
                if new_room is not None:
                    # Successfully placed room
                    if grow_from_first:
                        first_room = new_room
                    else:
                        last_room = new_room
                        
                    self.rooms.append(new_room)
                    last_shape = room_shape
                    attempts = 0  # Reset attempts on success
                    break
                
                # Failed to place room, try a different shape
                retry_count += 1
                room_shape = get_random_room_shape(last_shape, options=source_room.map.options)
            
            if new_room is None:
                # Failed all retries
                attempts += 1
                
        return self.rooms

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
    from map._arrange.strategy import StrategyType, StrategyParams
    from map._arrange.linear_strategy import LinearStrategy
    
    # Create start room if none provided
    if start_room is None:
        start_room = dungeon_map.create_rectangular_room(0, 0,
            random.randint(min_size, max_size),
            random.randint(min_size, max_size))
    
    from map._arrange.distribution import get_from_distribution
    from map._arrange.strategy_distribution import STRATEGY_DISTRIBUTION, StrategyConfig
    
    # Initialize
    total_rooms = random.randint(min_rooms, max_rooms)
    rooms_left = total_rooms - 1  # Subtract start room
    grow_list = [start_room]  # List of rooms to grow from
    all_rooms = [start_room]
    
    # Keep growing until we hit target room count
    while rooms_left > 0 and grow_list:
        next_rooms = []
        
        # Process each room we can grow from
        for room in grow_list:
            # Get random strategy from distribution
            strategy_config = get_from_distribution(STRATEGY_DISTRIBUTION)
            
            # Create and execute strategy
            if strategy_config.strategy_type in (
                StrategyType.LINEAR_SMALL,
                StrategyType.LINEAR_MEDIUM,
                StrategyType.LINEAR_LARGE
            ):
                strategy = LinearStrategy(dungeon_map, strategy_config.params)
                
            new_rooms = strategy.execute(rooms_left, room)
            next_rooms.extend(new_rooms)
            all_rooms.extend(new_rooms)
            rooms_left -= len(new_rooms)
        
        current_rooms = next_rooms
        
    return all_rooms
