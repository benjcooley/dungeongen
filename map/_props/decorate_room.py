"""Room decoration utilities.

This module provides functions for randomly decorating map elements with props like
columns, altars, daises and rocks based on element type and size.
"""

import random
from typing import TYPE_CHECKING

from map.enums import Direction, RockType
from map.props import ColumnType, Altar, Dais, Rock
from map.arrange import ColumnArrangement, arrange_columns, arrange_random_props, PropType
from algorithms.rotation import Rotation
from map.room import Room, RoomType

if TYPE_CHECKING:
    from map.mapelement import MapElement

def decorate_room(element: 'MapElement') -> None:
    """Randomly decorate a map element with props.
    
    Args:
        element: The map element to decorate
    """
    # Only add larger props to actual Room instances
    if isinstance(element, Room):
        # 1 in 5 chance to add columns
        if random.random() < 0.2:
            # Pick column arrangement based on room type
            if element.room_type == RoomType.RECTANGULAR:
                # For rectangular rooms:
                # - HORIZONTAL_ROWS: 40% chance
                # - VERTICAL_ROWS: 40% chance
                # - CIRCLE: 10% chance
                # - SQUARE: 10% chance
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
                
            arrange_columns(element, arrangement)
            
        # For rectangular rooms only:
        if element.room_type == RoomType.RECTANGULAR:
            # 1 in 5 chance to add a dais
            if random.random() < 0.2:
                # Add dais to random side of room
                direction = random.choice(list(Direction))
                dx, dy = direction.get_offset()
                dais = Dais(
                    (element.bounds.left + dx * element.bounds.width,
                     element.bounds.top + dy * element.bounds.height),
                    Rotation.random_cardinal_rotation()
                )
                element.add_prop(dais)
        
        # Add altars:
        # - 2/10 chance for 1 altar
        # - 1/10 chance for 2 altars
        altar_roll = random.random()
        if altar_roll < 0.2:
            arrange_random_props(element, [PropType.ALTAR], min_count=1, max_count=1)
        elif altar_roll < 0.3:
            arrange_random_props(element, [PropType.ALTAR], min_count=2, max_count=2)
    
    # Add some rocks to any map element
    arrange_random_props(element, [PropType.SMALL_ROCK], min_count=0, max_count=5)
    arrange_random_props(element, [PropType.MEDIUM_ROCK], min_count=0, max_count=3)
