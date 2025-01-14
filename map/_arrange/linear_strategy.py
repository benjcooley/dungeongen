"""Linear room arrangement strategy."""
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
    branch_chance: float = 0.3

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
        created_rooms = []
        rooms_to_create = min(
            rooms_left,
            random.randint(self.params.min_rooms, self.params.max_rooms)
        )
        
        if rooms_to_create == 0:
            return []
            
        # Pick random cardinal direction
        direction = random.choice([
            RoomDirection.NORTH,
            RoomDirection.SOUTH, 
            RoomDirection.EAST,
            RoomDirection.WEST
        ])
        
        # Create rooms using linear arrangement
        new_rooms = self._arrange_linear(
            rooms_to_create,
            source_room,
            direction,
            GrowDirection.FORWARD,  # Always grow forward for now
            max_attempts=30,
            branch_chance=self.params.branch_chance
        )
        
        return new_rooms
        
    def _arrange_linear(
        self,
        num_rooms: int,
        start_room: Room,
        direction: RoomDirection,
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
        rooms = [start_room]  # Track all rooms
        first_room = last_room = start_room
        last_shape = None
        
        # Calculate initial passage point from first room
        initial_passage_point = get_room_exit_grid_position(
            start_room,
            direction,
            wall_pos=0.5
        )
            
        attempts = 0
        while len(rooms) < num_rooms and attempts < max_attempts:
            attempts += 1
            
            # Possibly start a new branch
            if random.random() < branch_chance and len(rooms) < num_rooms - 1:
                # Pick a random room to branch from
                source_room = random.choice(rooms)
                
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
                remaining_rooms = num_rooms - len(rooms)
                if remaining_rooms > 1:
                    branch_size = random.randint(1, remaining_rooms - 1)
                    self._arrange_linear(
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
            room_shape = get_random_room_shape(last_shape, options=self.map.options)
            
            # Get passage configuration using our distribution system
            passage_config = get_random_passage_config(self.map.options)
            
            # Try to create connected room with retries for different shapes/positions
            new_room = None
            retry_count = 0
            max_shape_retries = 3
            
            while new_room is None and retry_count < max_shape_retries:
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
                
                # Failed to place room, try a different shape
                retry_count += 1
                room_shape = get_random_room_shape(last_shape, options=self.map.options)
            
            if new_room is None:
                # Failed all retries
                attempts += 1
                
        return rooms
