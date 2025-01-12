"""Room shape generation with controlled size distributions."""

from dataclasses import dataclass
from typing import Dict, Any, Callable, Tuple, List
from map.room import RoomType
from map._arrange.distribution import normalize_distribution, get_from_distribution

@dataclass
class RoomShape:
    """Defines the shape and dimensions of a room."""
    room_type: RoomType
    breadth: int  # Width relative to forward direction
    depth: int    # Length relative to forward direction
    breadth_offset: float  # Offset for alternating room placement

def make_room_shape(room_type: RoomType, breadth: int, depth: int) -> RoomShape:
    """Factory function for creating room shapes."""
    return RoomShape(room_type, breadth, depth, 0.0)

# Generator function for large special-case rooms
def generate_large_room(data: Dict[str, Any]) -> RoomShape:
    """Generate a large special-case room based on context."""
    # Example special case generation - could be expanded
    return make_room_shape(RoomType.RECTANGULAR, 5, 7)

# Define room shape distribution with weights
# Format: (weights, item, requirement_fn)
ROOM_DISTRIBUTION: List[Tuple[Tuple[float], RoomShape | Callable, None]] = [
    # Common small symmetric rooms
    ((1.0,), make_room_shape(RoomType.RECTANGULAR, 3, 3), None),
    ((0.8,), make_room_shape(RoomType.CIRCULAR, 3, 3), None),
    
    # Common small asymmetric rooms
    ((0.7,), make_room_shape(RoomType.RECTANGULAR, 2, 3), None),
    ((0.7,), make_room_shape(RoomType.RECTANGULAR, 3, 2), None),
    
    # Medium rooms
    ((0.5,), make_room_shape(RoomType.RECTANGULAR, 3, 4), None),
    ((0.5,), make_room_shape(RoomType.RECTANGULAR, 4, 3), None),
    
    # Larger rooms (less common)
    ((0.3,), make_room_shape(RoomType.RECTANGULAR, 3, 5), None),
    ((0.2,), make_room_shape(RoomType.RECTANGULAR, 5, 5), None),
    ((0.1,), make_room_shape(RoomType.CIRCULAR, 5, 5), None),
    
    # Special case generator for very large rooms (rare)
    ((0.05,), generate_large_room, None)
]

# Normalize the distribution once at module load
NORMALIZED_DISTRIBUTION = normalize_distribution(ROOM_DISTRIBUTION)

def get_random_room_shape(last_shape: RoomShape = None) -> RoomShape:
    """Get a random room shape based on weighted probabilities.
    
    Args:
        last_shape: The previous room shape, used to alternate breadth_offset
        
    Returns:
        A new RoomShape instance with randomized properties
    """
    shape = get_from_distribution(NORMALIZED_DISTRIBUTION)
    
    # Alternate breadth_offset if we have a previous shape
    if last_shape is not None:
        shape.breadth_offset = 0.5 if last_shape.breadth_offset == 0.0 else 0.0
        
    return shape
