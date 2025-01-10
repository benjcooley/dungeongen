"""Room decoration utilities.

This module provides functions for randomly decorating rooms with props like
columns, altars, daises and rocks based on room type and size.
"""

import random
from typing import TYPE_CHECKING

from map._arrange.arrange_utils import Direction
from map.props import ColumnType, Altar, Dais, Rock
from map.arrange import ColumnArrangement, arrange_columns, arrange_random_props, PropType
from algorithms.rotation import Rotation

if TYPE_CHECKING:
    from map.room import Room

def decorate_room(room: 'Room') -> None:
    """Randomly decorate a room with props.
    
    Args:
        room: The room to decorate
    """
    # 1 in 5 chance to add columns
    if random.random() < 0.2:
        # Pick column arrangement based on room type
        if room.room_type.is_rectangular():
            # For rectangular rooms:
            # - HORIZONTAL: 3/8 chance
            # - VERTICAL: 3/8 chance  
            # - RECT: 1/8 chance
            # - SQUARE: 1/8 chance
            weights = [3, 3, 1, 1]
            arrangement = random.choices(
                [ColumnArrangement.HORIZONTAL_ROWS,
                 ColumnArrangement.VERTICAL_ROWS,
                 ColumnArrangement.RECT,
                 ColumnArrangement.SQUARE],
                weights=weights
            )[0]
        else:
            # For circular rooms, only use circle arrangement
            arrangement = ColumnArrangement.CIRCLE
            
        arrange_columns(room, arrangement)
        
    # For rectangular rooms only:
    if room.room_type.is_rectangular():
        # 1 in 5 chance to add a dais
        if random.random() < 0.2:
            # Add dais to random side of room
            direction = random.choice(list(Direction))
            dx, dy = direction.get_offset()
            dais = Dais(
                (room.bounds.left + dx * room.bounds.width,
                 room.bounds.top + dy * room.bounds.height),
                Rotation.ROT_0
            )
            room.add_prop(dais)
    
    # Add altars:
    # - 2/10 chance for 1 altar
    # - 1/10 chance for 2 altars
    altar_roll = random.random()
    if altar_roll < 0.2:
        arrange_random_props(room, [PropType.ALTAR], min_count=1, max_count=1)
    elif altar_roll < 0.3:
        arrange_random_props(room, [PropType.ALTAR], min_count=2, max_count=2)
        
    # Add some rocks
    arrange_random_props(room, [PropType.SMALL_ROCK], min_count=0, max_count=5)
    arrange_random_props(room, [PropType.MEDIUM_ROCK], min_count=0, max_count=3)
