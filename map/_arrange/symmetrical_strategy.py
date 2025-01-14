"""Symmetrical room arrangement strategy."""

from dataclasses import dataclass
import random
from typing import List, Optional, Tuple, Set

from map.room import Room
from map._arrange.strategy import Strategy, StrategyParams
from map._arrange.room_distribution import get_random_room_shape
from map._arrange.arrange_utils import RoomDirection, get_room_exit_grid_position
from map._arrange.passage_distribution import get_random_passage_config
from map._arrange.arrange_rooms import try_create_connected_room

@dataclass
class SymmetricalStrategyParams(StrategyParams):
    """Parameters specific to symmetrical arrangement."""
    iterations: int = 2  # Number of symmetrical pairs to attempt
    min_spacing: int = 2
    max_spacing: int = 4

class SymmetricalStrategy(Strategy):
    """Arranges rooms in symmetrical pairs around a source room."""
    
    def execute(self, rooms_left: int, source_room: Room) -> List[Room]:
        """Create symmetrical pairs of rooms around the source room.
        
        For each iteration:
        1. Pick a random cardinal direction
        2. Create identical room/passage configs
        3. Place rooms on opposite sides of source room
        4. Add successful rooms to candidates for next iteration
        
        Args:
            rooms_left: Maximum number of rooms to create
            source_room: Room to grow from
            
        Returns:
            List of created rooms
        """
        if rooms_left < 2:  # Need at least 2 rooms for symmetry
            return []
            
        rooms_created: List[Room] = []
        candidate_rooms: Set[Room] = {source_room}
        iterations = min(self.params.iterations, rooms_left // 2)
        
        for _ in range(iterations):
            if not candidate_rooms or rooms_left < 2:
                break
                
            # Pick random source room and direction
            current_room = random.choice(list(candidate_rooms))
            direction = random.choice([
                RoomDirection.NORTH,
                RoomDirection.SOUTH,
                RoomDirection.EAST,
                RoomDirection.WEST
            ])
            
            # Get room shape and passage config to use for both sides
            room_shape = get_random_room_shape(options=self.map.options)
            passage_config = get_random_passage_config(self.map.options)
            
            # Try to create the pair of rooms
            room1, _, _, _ = try_create_connected_room(
                current_room,
                direction,
                passage_config.length,
                room_shape.breadth,
                room_shape.depth,
                room_type=room_shape.room_type,
                start_door_type=passage_config.doors.start_door,
                end_door_type=passage_config.doors.end_door,
                breadth_offset=room_shape.breadth_offset
            )
            
            if room1 is None:
                continue
                
            # Try to create the opposite room with same configuration
            room2, _, _, _ = try_create_connected_room(
                current_room,
                direction.get_opposite(),
                passage_config.length,
                room_shape.breadth,
                room_shape.depth,
                room_type=room_shape.room_type,
                start_door_type=passage_config.doors.start_door,
                end_door_type=passage_config.doors.end_door,
                breadth_offset=room_shape.breadth_offset
            )
            
            if room2 is None:
                # Remove room1 since we couldn't create its pair
                self.map.remove_element(room1)
                continue
                
            # Successfully created a pair
            rooms_created.extend([room1, room2])
            candidate_rooms.add(room1)
            candidate_rooms.add(room2)
            rooms_left -= 2
            
        return rooms_created
