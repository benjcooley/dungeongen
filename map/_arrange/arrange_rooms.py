"""Room arrangement strategies for dungeon map generation.

This module provides different strategies for arranging rooms in a dungeon map:

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
from algorithms.shapes import Circle
from map.map import Map
from map.room import Room
from map.passage import Passage
from map.door import Door, DoorOrientation

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
        width = random.randint(self.min_size, self.max_size)
        height = random.randint(self.min_size, self.max_size)
        room = self.dungeon_map.add_rectangular_room(grid_x, grid_y, width, height)
        self.rooms.append(room)
        return room
        
    def _get_room_connection_point(self, room: Room, orientation: Orientation) -> tuple[float, float]:
        """Get a point on the room's edge for connecting a passage.
        
        For circular rooms, uses the center point projected to the edge.
        For rectangular rooms, uses the center of the appropriate side.
        """
        bounds = room.bounds
        is_circle = isinstance(room.shape, Circle)
        
        if is_circle:
            # For circles, project from center to edge
            cx = bounds.x + bounds.width / 2
            cy = bounds.y + bounds.height / 2
            radius = bounds.width / 2  # Assuming width == height for circles
            
            if orientation == Orientation.HORIZONTAL:
                return (cx + radius if bounds.x < 0 else cx - radius, cy)
            else:
                return (cx, cy + radius if bounds.y < 0 else cy - radius)
        else:
            # For rectangles, use center of appropriate side
            if orientation == Orientation.HORIZONTAL:
                x = bounds.x + bounds.width if bounds.x < 0 else bounds.x
                y = bounds.y + bounds.height / 2
                return (x, y)
            else:
                x = bounds.x + bounds.width / 2
                y = bounds.y + bounds.height if bounds.y < 0 else bounds.y
                return (x, y)

    def _create_passage(self, room1: Room, room2: Room, orientation: Orientation) -> None:
        """Create a passage between two rooms with appropriate doors."""
        # Get connection points
        x1, y1 = self._get_room_connection_point(room1, orientation)
        x2, y2 = self._get_room_connection_point(room2, orientation)
        
        # Determine passage dimensions and position
        if orientation == Orientation.HORIZONTAL:
            passage_x = min(x1, x2)
            passage_width = abs(x2 - x1)
            passage_y = (y1 + y2) / 2 - 0.5  # Center between rooms
            
            # Create passage and doors
            passage = Passage.from_grid(passage_x, passage_y, passage_width, 1, self.dungeon_map)
            door1 = Door.from_grid(passage_x, passage_y, DoorOrientation.HORIZONTAL, self.dungeon_map, open=True)
            door2 = Door.from_grid(passage_x + passage_width - 1, passage_y,
                                DoorOrientation.HORIZONTAL, self.dungeon_map, open=True)
        else:
            passage_x = (x1 + x2) / 2 - 0.5  # Center between rooms
            passage_y = min(y1, y2)
            passage_height = abs(y2 - y1)
            
            # Create passage and doors
            passage = Passage.from_grid(passage_x, passage_y, 1, passage_height, self.dungeon_map)
            door1 = Door.from_grid(passage_x, passage_y, DoorOrientation.VERTICAL, self.dungeon_map, open=True)
            door2 = Door.from_grid(passage_x, passage_y + passage_height - 1,
                                DoorOrientation.VERTICAL, self.dungeon_map, open=True)
        
        # Connect everything
        room1.connect_to(door1)
        door1.connect_to(passage)
        passage.connect_to(door2)
        door2.connect_to(room2)

    def connect_rooms(self, room1: Room, room2: Room, orientation: Orientation) -> None:
        """Connect two rooms with a passage and doors."""
        self._create_passage(room1, room2, orientation)
        
    def arrange_linear(
        self,
        num_rooms: int,
        start_room: Optional[Room] = None,
        direction: Optional[Direction] = None,
        orientation: Optional[Orientation] = None
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
        for i in range(len(self.rooms), num_rooms):
            # Choose spacing
            spacing = random.randint(self.min_spacing, self.max_spacing)
            
            # Calculate new position based on orientation
            if orientation == Orientation.HORIZONTAL:
                if direction == Direction.FORWARD or (direction == Direction.BOTH and i % 2 == 0):
                    current_x += spacing + self.max_size
                else:
                    current_x -= spacing + self.max_size
            else:  # VERTICAL
                if direction == Direction.FORWARD or (direction == Direction.BOTH and i % 2 == 0):
                    current_y += spacing + self.max_size
                else:
                    current_y -= spacing + self.max_size
                    
            # Create and connect new room
            new_room = self.create_room(current_x, current_y)
            self.connect_rooms(self.rooms[-2], new_room, orientation)
            
        return self.rooms
