"""Room shape generation with controlled size distributions."""

from dataclasses import dataclass
from enum import Enum, auto
import random
from typing import List, Tuple
from map.room import RoomType

@dataclass
class RoomShape:
    """Defines the shape and dimensions of a room."""
    room_type: RoomType
    breadth: int  # Width relative to forward direction
    depth: int    # Length relative to forward direction
    breadth_offset: float  # Offset for alternating room placement
    weight: int   # Relative frequency weight

class RoomSizeCategory(Enum):
    """Categories of room sizes for distribution control."""
    SMALL = auto()      # 2x2, 2x3, 3x2
    MEDIUM = auto()     # 3x3, 3x4, 4x3
    LARGE = auto()      # 4x4, 4x5, 5x4
    GRAND = auto()      # 5x5, 5x6, 6x5

# Define common room shapes with their relative frequencies
ROOM_SHAPES = [
    # Small rooms (higher frequency)
    RoomShape(RoomType.RECTANGULAR, 2, 2, 0.0, 8),
    RoomShape(RoomType.RECTANGULAR, 2, 3, 0.0, 6),
    RoomShape(RoomType.RECTANGULAR, 3, 2, 0.0, 6),
    RoomShape(RoomType.CIRCULAR, 2, 2, 0.0, 4),
    
    # Medium rooms (moderate frequency)
    RoomShape(RoomType.RECTANGULAR, 3, 3, 0.0, 4),
    RoomShape(RoomType.RECTANGULAR, 3, 4, 0.0, 3),
    RoomShape(RoomType.RECTANGULAR, 4, 3, 0.0, 3),
    RoomShape(RoomType.CIRCULAR, 3, 3, 0.0, 2),
    
    # Large rooms (lower frequency)
    RoomShape(RoomType.RECTANGULAR, 4, 4, 0.0, 2),
    RoomShape(RoomType.RECTANGULAR, 4, 5, 0.0, 1),
    RoomShape(RoomType.RECTANGULAR, 5, 4, 0.0, 1),
    RoomShape(RoomType.CIRCULAR, 4, 4, 0.0, 1),
    
    # Grand rooms (rare)
    RoomShape(RoomType.RECTANGULAR, 5, 5, 0.0, 1),
    RoomShape(RoomType.RECTANGULAR, 5, 6, 0.0, 1),
    RoomShape(RoomType.RECTANGULAR, 6, 5, 0.0, 1),
    RoomShape(RoomType.CIRCULAR, 5, 5, 0.0, 1),
]

def get_random_room_shape(last_shape: RoomShape = None) -> RoomShape:
    """Get a random room shape based on weighted probabilities.
    
    Args:
        last_shape: The previous room shape, used to alternate breadth_offset
        
    Returns:
        A new RoomShape instance with randomized properties
    """
    # Select shape based on weights
    shape = random.choices(ROOM_SHAPES, weights=[s.weight for s in ROOM_SHAPES])[0]
    
    # Create a copy so we can modify the breadth_offset
    new_shape = RoomShape(
        shape.room_type,
        shape.breadth,
        shape.depth,
        shape.breadth_offset,
        shape.weight
    )
    
    # Alternate breadth_offset if we have a previous shape
    if last_shape is not None:
        new_shape.breadth_offset = 0.5 if last_shape.breadth_offset == 0.0 else 0.0
        
    return new_shape
