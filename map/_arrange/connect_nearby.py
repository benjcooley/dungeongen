"""Functions for connecting nearby rooms after initial arrangement."""

import random
from typing import List, Optional, Set, Tuple
from map._arrange.arrange_rooms import connect_rooms
from map._arrange.arrange_utils import RoomDirection, get_room_direction
from map.room import Room
from map.map import Map

def try_connect_nearby_rooms(dungeon_map: Map, max_connection_dist: int = 5) -> None:
    """Try to connect rooms that are near each other but not already connected.
    
    Args:
        dungeon_map: The map to process
        max_connection_dist: Maximum grid distance to search for potential connections
    """
    # Get list of all rooms
    rooms = list(dungeon_map.rooms)
    
    # Try connecting each room to others
    for source_room in rooms:
        # Get existing connections
        connected_rooms = {conn for conn in source_room.connections if isinstance(conn, Room)}
        
        # Get room bounds in grid coordinates
        bounds = source_room.bounds
        grid_x = int(bounds.x / 64)
        grid_y = int(bounds.y / 64)
        
        # Search in random positions within radius
        for _ in range(8):  # Try up to 8 random positions per room
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
                    
                    # Get direction between rooms
                    direction = get_room_direction(source_room, target_elem)
                    
                    # Try to connect the rooms
                    connect_rooms(source_room, target_elem)
