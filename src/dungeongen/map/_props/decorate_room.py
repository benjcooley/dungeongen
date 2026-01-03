"""Room decoration utilities.

This module provides functions for randomly decorating map elements with props like
columns, altars, dias, fountains and rocks based on element type and size.
"""

import random
from typing import TYPE_CHECKING

from dungeongen.constants import CELL_SIZE
from dungeongen.map.enums import Direction, RockType
from dungeongen.map.props import ColumnType, Altar, Dias, Rock, Fountain
from dungeongen.map.arrange import ColumnArrangement, arrange_columns, arrange_random_props, PropType
from dungeongen.map.room import Room, RoomType

if TYPE_CHECKING:
    from dungeongen.map.mapelement import MapElement

def decorate_room(element: 'MapElement') -> None:
    """Randomly decorate a map element with props.
    
    Args:
        element: The map element to decorate
    """
    # Only add larger props to actual Room instances that are large enough
    if isinstance(element, Room):
        # Calculate room area in grid cells
        room_width = int(element.bounds.width / CELL_SIZE)
        room_height = int(element.bounds.height / CELL_SIZE)
        room_area = room_width * room_height
        
        # Add columns for rooms larger than 3x3
        # - 40% chance for round rooms
        # - 20% chance for rectangular rooms
        column_chance = 0.4 if element.room_type != RoomType.RECTANGULAR else 0.2
        if random.random() < column_chance and room_area > 9:
            # Pick column arrangement based on room type 
            if element.room_type == RoomType.RECTANGULAR:
                # For rectangular rooms:
                # - HORIZONTAL_ROWS: 40% chance
                # - VERTICAL_ROWS: 40% chance
                # - CIRCLE: 10% chance
                # - GRID: 10% chance
                weights = [4, 4, 1, 1]
                arrangement = random.choices(
                    [ColumnArrangement.HORIZONTAL_ROWS,
                     ColumnArrangement.VERTICAL_ROWS,
                     ColumnArrangement.CIRCLE,
                     ColumnArrangement.GRID],
                    weights=weights
                )[0]
            else:  # CIRCULAR rooms must use CIRCLE arrangement
                arrangement = ColumnArrangement.CIRCLE
            
            # 50/50 chance for round vs square columns
            column_type = ColumnType.SQUARE if random.random() < 0.5 else ColumnType.ROUND
            arrange_columns(element, arrangement, column_type=column_type)
            
        # For rectangular rooms only - dias requires odd-length walls
        # Dias is 3 tiles wide, centered on wall, needs odd wall length
        # Prefers shorter walls, and walls with no exits or one central exit
        if element.room_type == RoomType.RECTANGULAR:
            # Build list of eligible walls with their lengths
            # Format: (wall_direction, wall_length)
            candidate_walls = []
            
            if room_width % 2 == 1 and room_width >= 3:  # Odd width, at least 3 tiles (dias is 3 wide)
                candidate_walls.append((Direction.NORTH, room_width))
                candidate_walls.append((Direction.SOUTH, room_width))
            if room_height % 2 == 1 and room_height >= 3:  # Odd height, at least 3 tiles
                candidate_walls.append((Direction.EAST, room_height))
                candidate_walls.append((Direction.WEST, room_height))
            
            # Sort by wall length (prefer shorter walls)
            candidate_walls.sort(key=lambda x: x[1])
            
            # 20% chance to add a dias if we have eligible walls
            if candidate_walls and random.random() < 0.2:
                # Pick from the shortest walls (may have ties)
                shortest_length = candidate_walls[0][1]
                shortest_walls = [w for w in candidate_walls if w[1] == shortest_length]
                wall, _ = random.choice(shortest_walls)
                
                # Calculate wall center point
                center_x = element.bounds.left + element.bounds.width / 2
                center_y = element.bounds.top + element.bounds.height / 2
                
                # Use the on_wall helper for correct positioning
                if wall == Direction.NORTH:
                    dias = Dias.on_wall('north', center_x, element.bounds.top)
                elif wall == Direction.SOUTH:
                    dias = Dias.on_wall('south', center_x, element.bounds.bottom)
                elif wall == Direction.EAST:
                    dias = Dias.on_wall('east', element.bounds.right, center_y)
                else:  # WEST
                    dias = Dias.on_wall('west', element.bounds.left, center_y)
                
                element.add_prop(dias)
                
                # 50% chance to place an altar (or casket when available) on the dias
                if random.random() < 0.5:
                    altar = Altar(dias.placement_point)
                    element.add_prop(altar)
        
        # Add fountain in center of larger rooms (area > 16, i.e. 4x4+)
        # - 10% chance for any qualifying room
        if room_area > 16 and random.random() < 0.10:
            center_x = element.bounds.left + element.bounds.width / 2
            center_y = element.bounds.top + element.bounds.height / 2
            fountain = Fountain.create(center_x, center_y)
            element.add_prop(fountain)
        
        # Add altars (reduced frequency):
        # - 5% chance for 1 altar
        # - 2% chance for 2 altars
        altar_roll = random.random()
        if altar_roll < 0.05:
            arrange_random_props(element, [PropType.ALTAR], min_count=1, max_count=1)
        elif altar_roll < 0.07:
            arrange_random_props(element, [PropType.ALTAR], min_count=2, max_count=2)
    
    # Add some rocks to any map element
    arrange_random_props(element, [PropType.SMALL_ROCK], min_count=0, max_count=5)
    arrange_random_props(element, [PropType.MEDIUM_ROCK], min_count=0, max_count=3)
