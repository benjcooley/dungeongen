"""Room arrangement strategies for dungeon map generation.

This module provides different strategies for arranging rooms in a dungeon map:

- ArrangeSymmetric: Arranges rooms in symmetrical patterns, attempting to maintain
  left/right balance where possible. Good for formal dungeon layouts like temples.

- ArrangeLinear: Arranges rooms in a more or less linear fashion, good for
  dungeons that tell a story or represent a journey from start to finish.

- ArrangeSpiral: Arranges rooms in a spiral pattern expanding outward from the
  center. Good for creating maze-like dungeons that loop back on themselves.

  This is a submodule of the arrange.py module. Update this aggregator module
  when you add new symbols here.
"""

from enum import Enum, auto
from typing import List, Optional, Tuple
import random
from algorithms.shapes import Circle
from map.map import Map
from map.room import Room
from map.passage import Passage
from constants import CELL_SIZE
from map.door import Door, DoorOrientation

class Direction(Enum):
    """Direction to generate rooms."""
    BOTH = auto()
    FORWARD = auto()
    BACKWARD = auto()

class Orientation(Enum):
    """Orientation for room generation."""
    HORIZONTAL = auto()
    VERTICAL = auto()

class ArrangeRoomStyle(Enum):
    """Room arrangement strategies."""
    SYMMETRIC = auto()  # Arrange rooms symmetrically where possible
    LINEAR = auto()     # Arrange rooms in a roughly linear path
    SPIRAL = auto()     # Arrange rooms in a spiral pattern from center

class Direction(Enum):
    """Direction to generate rooms."""
    BOTH = auto()
    FORWARD = auto()
    BACKWARD = auto()

class Orientation(Enum):
    """Orientation for room generation."""
    HORIZONTAL = auto()
    VERTICAL = auto()

def arrange_rooms(
    dungeon_map: Map,
    style: ArrangeRoomStyle,
    min_rooms: int = 3,
    max_rooms: int = 7,
    min_size: int = 3,
    max_size: int = 7,
    start_room: Optional[Room] = None
) -> List[Room]:
    """Arrange rooms according to the specified style.
    
    Args:
        dungeon_map: The map to add rooms to
        style: The arrangement strategy to use
        min_rooms: Minimum number of rooms to create
        max_rooms: Maximum number of rooms to create
        min_size: Minimum room size in grid units
        max_size: Maximum room size in grid units
        
    Returns:
        List of created Room instances
    """
    num_rooms = random.randint(min_rooms, max_rooms)
    arranger = _RoomArranger(dungeon_map, min_size, max_size)
    
    if style == ArrangeRoomStyle.LINEAR:
        return arranger.arrange_linear(num_rooms, start_room)
    elif style == ArrangeRoomStyle.SYMMETRIC:
        # TODO: Implement symmetric arrangement
        return []
    else:  # SPIRAL
        # TODO: Implement spiral arrangement
        return []

class _RoomArranger:
    """Helper class for arranging rooms with shared state."""
    
    def __init__(
        self,
        dungeon_map: Map,
        min_size: int,
        max_size: int,
        min_spacing: int = 2,
        max_spacing: int = 4
    ):
        self.dungeon_map = dungeon_map
        self.min_size = min_size
        self.max_size = max_size
        self.min_spacing = min_spacing
        self.max_spacing = max_spacing
        self.rooms: List[Room] = []
        
    def create_room(self, grid_x: float, grid_y: float) -> Room:
        """Create a room at the given grid position."""
        # Sanity checks for position
        if abs(grid_x) > 1000 or abs(grid_y) > 1000:
            raise ValueError(f"Room position ({grid_x}, {grid_y}) is too far from origin")
            
        width = random.randint(self.min_size, self.max_size)
        height = random.randint(self.min_size, self.max_size)
        
        # Sanity checks for dimensions
        if width < 1 or height < 1:
            raise ValueError(f"Invalid room dimensions: {width}x{height}")
        if width > 100 or height > 100:
            raise ValueError(f"Room dimensions {width}x{height} exceed maximum allowed size")
        print(f"\nGenerating room {len(self.rooms) + 1}:")
        print(f"  Grid position: ({grid_x}, {grid_y})")
        print(f"  Grid size: {width}x{height}")
        room = self.dungeon_map.add_rectangular_room(grid_x, grid_y, width, height)
        print(f"  Map bounds: ({room.bounds.x}, {room.bounds.y}) to ({room.bounds.x + room.bounds.width}, {room.bounds.y + room.bounds.height})")
        self.rooms.append(room)
        return room
        
    def get_room_grid_connection(self, room: Room, direction: Direction) -> tuple[int, int]:
        """Get a grid position for connecting to this room from the given direction.
        
        Args:
            room: The room to connect to
            direction: Which side of the room to connect from
            
        Returns:
            Tuple of (grid_x, grid_y) for the connection point
        """
        # Get room bounds in grid coordinates
        grid_x = int(room.bounds.x / CELL_SIZE)
        grid_y = int(room.bounds.y / CELL_SIZE)
        grid_width = int(room.bounds.width / CELL_SIZE)
        grid_height = int(room.bounds.height / CELL_SIZE)
        
        # Calculate center point
        center_x = grid_x + grid_width // 2
        center_y = grid_y + grid_height // 2
        
        # Return appropriate edge point based on direction
        if direction == Direction.NORTH:
            return (center_x, grid_y)
        elif direction == Direction.SOUTH:
            return (center_x, grid_y + grid_height)
        elif direction == Direction.EAST:
            return (grid_x + grid_width, center_y)
        else:  # WEST
            return (grid_x, center_y)

    def _create_passage(self, room1: Room, room2: Room, orientation: Orientation) -> None:
        """Create a passage between two rooms with appropriate doors."""
        # Determine which sides to connect based on orientation and relative positions
        if orientation == Orientation.HORIZONTAL:
            # For horizontal passages, connect east side of leftmost room to west side of rightmost room
            if room1.bounds.x < room2.bounds.x:
                r1_dir = Direction.EAST
                r2_dir = Direction.WEST
            else:
                r1_dir = Direction.WEST
                r2_dir = Direction.EAST
        else:  # VERTICAL
            # For vertical passages, connect south side of upper room to north side of lower room
            if room1.bounds.y < room2.bounds.y:
                r1_dir = Direction.SOUTH
                r2_dir = Direction.NORTH
            else:
                r1_dir = Direction.NORTH
                r2_dir = Direction.SOUTH
                
        # Get connection points in grid coordinates
        r1_x, r1_y = self.get_room_grid_connection(room1, r1_dir)
        r2_x, r2_y = self.get_room_grid_connection(room2, r2_dir)
        
        # Convert to map coordinates
        x1, y1 = r1_x * CELL_SIZE, r1_y * CELL_SIZE
        x2, y2 = r2_x * CELL_SIZE, r2_y * CELL_SIZE
        """Create a passage between two rooms with appropriate doors."""
        # Get connection points
        x1, y1 = self._get_room_connection_point(room1, orientation)
        x2, y2 = self._get_room_connection_point(room2, orientation)
        
        print(f"\nCreating passage:")
        print(f"  Room1 connection point: ({x1}, {y1})")
        print(f"  Room2 connection point: ({x2}, {y2})")
        
        # Determine passage dimensions and position
        if orientation == Orientation.HORIZONTAL:
            passage_x = min(x1, x2)
            passage_width = abs(x2 - x1)
            passage_y = (y1 + y2) / 2 - 0.5  # Center between rooms
            
            print(f"  Horizontal passage:")
            print(f"    Position: ({passage_x}, {passage_y})")
            print(f"    Width: {passage_width}")
            
            # Convert passage position to grid coordinates
            grid_passage_x = passage_x / CELL_SIZE
            grid_passage_y = passage_y / CELL_SIZE
            grid_passage_width = passage_width / CELL_SIZE
            
            # Create passage and doors
            passage = Passage.from_grid(grid_passage_x, grid_passage_y, grid_passage_width, 1, self.dungeon_map)
            door1 = Door.from_grid(grid_passage_x, grid_passage_y, DoorOrientation.HORIZONTAL, self.dungeon_map, open=True)
            door2 = Door.from_grid(grid_passage_x + grid_passage_width - 1, grid_passage_y,
                                DoorOrientation.HORIZONTAL, self.dungeon_map, open=True)
        else:
            passage_x = (x1 + x2) / 2 - 0.5  # Center between rooms
            passage_y = min(y1, y2)
            passage_height = abs(y2 - y1)
            
            # Create passage and doors
            # Calculate grid coordinates
            grid_passage_x = round(passage_x / CELL_SIZE)
            grid_passage_y = round(passage_y / CELL_SIZE)
            grid_passage_height = round(abs(y2 - y1) / CELL_SIZE)
            
            print(f"  Vertical passage:")
            print(f"    Position: ({grid_passage_x}, {grid_passage_y})")
            print(f"    Height: {grid_passage_height}")
            
            # Create passage and doors
            passage = Passage.from_grid(grid_passage_x, grid_passage_y, 1, grid_passage_height, self.dungeon_map)
            door1 = Door.from_grid(grid_passage_x, grid_passage_y, DoorOrientation.VERTICAL, self.dungeon_map, open=True)
            door2 = Door.from_grid(grid_passage_x, grid_passage_y + grid_passage_height - 1,
                                DoorOrientation.VERTICAL, self.dungeon_map, open=True)
        
        # Connect everything
        room1.connect_to(door1)
        door1.connect_to(passage)
        passage.connect_to(door2)
        door2.connect_to(room2)

    def connect_rooms(self, room1: Room, room2: Room, orientation: Orientation) -> None:
        """Connect two rooms with a passage and doors."""
        print(f"\nConnecting rooms:")
        print(f"  Room1 bounds: ({room1.bounds.x}, {room1.bounds.y}) to ({room1.bounds.x + room1.bounds.width}, {room1.bounds.y + room1.bounds.height})")
        print(f"  Room2 bounds: ({room2.bounds.x}, {room2.bounds.y}) to ({room2.bounds.x + room2.bounds.width}, {room2.bounds.y + room2.bounds.height})")
        print(f"  Orientation: {orientation}")
        self._create_passage(room1, room2, orientation)
        
    def arrange_linear(
        self,
        num_rooms: int,
        start_room: Optional[Room] = None,
        direction: Optional[Direction] = None,
        orientation: Optional[Orientation] = None,
        max_attempts: int = 100
    ) -> List[Room]:
        """Arrange rooms in a linear sequence."""
        if start_room:
            self.rooms.append(start_room)
            current_x = start_room.bounds.x
            current_y = start_room.bounds.y
        else:
            current_x = current_y = 0
            self.create_room(current_x, current_y)
            
        # Choose random direction and orientation if not specified
        direction = direction or random.choice(list(Direction))
        orientation = orientation or random.choice(list(Orientation))
        
        # Generate remaining rooms
        attempts = 0
        last_room = self.rooms[-1]  # Track the last room we added
        while len(self.rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            # Choose spacing
            spacing = random.randint(self.min_spacing, self.max_spacing)
            
            # Get position of last room
            current_x = last_room.bounds.x / CELL_SIZE
            current_y = last_room.bounds.y / CELL_SIZE
            
            # Limit maximum spacing between rooms
            max_allowed_spacing = 3  # Maximum spacing in grid units
            spacing = min(spacing, max_allowed_spacing)
            
            # Calculate room offset based on max size
            room_offset = min(self.max_size, 5)  # Limit maximum room size contribution
            
            # Calculate new position based on orientation
            next_x = current_x
            next_y = current_y
            
            if orientation == Orientation.HORIZONTAL:
                if direction == Direction.FORWARD or (direction == Direction.BOTH and len(self.rooms) % 2 == 0):
                    next_x = current_x + spacing + room_offset
                else:
                    next_x = current_x - spacing - room_offset
            else:  # VERTICAL
                if direction == Direction.FORWARD or (direction == Direction.BOTH and len(self.rooms) % 2 == 0):
                    next_y = current_y + spacing + room_offset
                else:
                    next_y = current_y - spacing - room_offset
                    
            # Sanity check the new position
            if abs(next_x) > 3200 or abs(next_y) > 3200:
                print(f"Warning: Room position ({next_x}, {next_y}) exceeds reasonable bounds (±3200), retrying...")
                continue
                
            # Create and connect new room
            new_room = self.create_room(next_x, next_y)
            self.connect_rooms(last_room, new_room, orientation)
            last_room = new_room  # Update last room
            
        return self.rooms
