"""Linear room arrangement strategy."""
from dataclasses import dataclass
import random
from typing import List, Optional

from map.room import Room
from map._arrange.strategy import Strategy, StrategyParams
from map._arrange.room_shapes import get_random_room_shape
from map._arrange.arrange_utils import RoomDirection, get_room_exit_grid_position
from map._arrange.passage_distribution import get_random_passage_config

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
        
        # Calculate initial passage point
        initial_point = get_room_exit_grid_position(
            source_room,
            direction,
            wall_pos=0.5
        )
        
        current_room = source_room
        for _ in range(rooms_to_create):
            # Get random room shape
            room_shape = get_random_room_shape(None, options=self.dungeon_map.options)
            
            # Get passage configuration
            passage_config = get_random_passage_config(self.dungeon_map.options)
            
            # Try to create room
            from map._arrange.arrange_rooms import try_create_connected_room
            
            new_room = None
            retry_count = 0
            while new_room is None and retry_count < 3:
                new_room, _, _, _ = try_create_connected_room(
                    current_room,
                    direction,
                    passage_config.length,
                    room_shape.breadth,
                    room_shape.depth,
                    room_type=room_shape.room_type,
                    start_door_type=passage_config.doors.start_door,
                    end_door_type=passage_config.doors.end_door,
                    breadth_offset=room_shape.breadth_offset,
                    align_to=initial_point
                )
                
                if new_room is not None:
                    created_rooms.append(new_room)
                    current_room = new_room
                    break
                    
                retry_count += 1
                room_shape = get_random_room_shape(None, options=self.dungeon_map.options)
                
            if new_room is None:
                # Failed to place room, stop sequence
                break
                
        return created_rooms
