"""Linear room arrangement strategy."""

MAX_SHAPE_RETRIES = 3  # Maximum number of times to retry with different room shapes
from dataclasses import dataclass
import random
from typing import List, Optional, Tuple

from map.room import Room
from map._arrange.strategy import Strategy, StrategyParams
from map._arrange.room_distribution import get_random_room_shape
from map._arrange.arrange_utils import RoomDirection, get_room_exit_grid_position
from map._arrange.passage_distribution import get_random_passage_config
from map._arrange.arrange_rooms import try_create_connected_room
from map._arrange.arrange_enums import GrowDirection

@dataclass
class LinearStrategyParams(StrategyParams):
    """Parameters specific to linear room arrangement."""
    min_spacing: int = 2
    max_spacing: int = 4

class LinearStrategy(Strategy):
    """Arranges rooms in a linear sequence."""
    
    def execute(self, rooms_left: int, source_room: Room) -> List[Room]:
        """Create a linear sequence of rooms.
        
        Args:
            rooms_left: Maximum number of rooms to create
            source_room: Room to grow from
            
        Returns:
            List of created rooms
        """
        num_rooms = min(
            rooms_left,
            random.randint(self.params.min_rooms, self.params.max_rooms)
        )
        
        if num_rooms == 0:
            return []
            
        # Pick random cardinal direction
        direction = random.choice([
            RoomDirection.NORTH,
            RoomDirection.SOUTH, 
            RoomDirection.EAST,
            RoomDirection.WEST
        ])
        rooms = []  # Track all rooms
        first_room = last_room = source_room
        last_shape = None
        
        # Calculate initial passage point from source room
        initial_passage_point = get_room_exit_grid_position(
            source_room,
            direction,
            wall_pos=0.5
        )
            
        attempts = 0
        max_attempts = 30
        grow_direction = GrowDirection.FORWARD
        
        while len(rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            
            # Determine growth direction
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
                
            # Try to create connected room with retries for different shapes/positions
            new_room = None
            retry_count = 0
            
            while new_room is None and retry_count < MAX_SHAPE_RETRIES:
                # Get random room shape and passage config for each attempt
                room_shape = get_random_room_shape(last_shape, options=self.map.options)
                passage_config = get_random_passage_config(self.map.options)
                
                new_room, _, _, _ = try_create_connected_room(
                    source_room,
                    connect_dir,
                    passage_config.length,
                    room_shape.breadth,
                    room_shape.depth,
                    room_type=room_shape.room_type,
                    start_door_type=passage_config.doors.start_door,
                    end_door_type=passage_config.doors.end_door,
                    breadth_offset=room_shape.breadth_offset,
                    align_to=initial_passage_point
                )
                
                if new_room is not None:
                    # Successfully placed room
                    if grow_from_first:
                        first_room = new_room
                    else:
                        last_room = new_room
                        
                    rooms.append(new_room)
                    last_shape = room_shape
                    attempts = 0  # Reset attempts on success
                    break
                
                retry_count += 1
            
            # If all retries failed, increment attempts
            if new_room is None:
                attempts += 1
                
        return rooms
