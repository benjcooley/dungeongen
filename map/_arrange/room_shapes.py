"""Room shape generation with controlled size distributions."""

from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, Tuple, List
from map._arrange.arrange_utils import get_size_index_from_tags
from options import Options
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

# Define room shape distribution with weights for different map sizes
# Format: (weights[small, medium, large], item, requirement_fn)
ROOM_DISTRIBUTION: List[Tuple[Tuple[float, float, float], RoomShape | Callable, None]] = [
    # Common small symmetric rooms (more common in small maps)
    ((2.0, 1.0, 0.5), make_room_shape(RoomType.RECTANGULAR, 3, 3), None),
    ((2.5, 1.2, 0.6), make_room_shape(RoomType.CIRCULAR, 3, 3), None),
    
    # Small asymmetric rooms (very rare in all sizes, prefer odd breadth)
    ((0.02, 0.01, 0.005), make_room_shape(RoomType.RECTANGULAR, 2, 3), None),
    ((0.1, 0.05, 0.02), make_room_shape(RoomType.RECTANGULAR, 3, 2), None),
    
    # Medium rooms (balanced in medium maps, strongly prefer odd breadth)
    ((0.8, 1.4, 1.0), make_room_shape(RoomType.RECTANGULAR, 3, 4), None),
    ((0.6, 0.8, 0.6), make_room_shape(RoomType.CIRCULAR, 3, 4), None),
    ((0.1, 0.2, 0.15), make_room_shape(RoomType.RECTANGULAR, 4, 3), None),
    
    # Larger rooms (more common in large maps, strongly prefer odd breadth)
    ((0.3, 0.8, 1.2), make_room_shape(RoomType.RECTANGULAR, 3, 5), None),
    ((0.02, 0.05, 0.1), make_room_shape(RoomType.RECTANGULAR, 4, 4), None)
]

# Normalize the distribution once at module load
NORMALIZED_DISTRIBUTION = normalize_distribution(ROOM_DISTRIBUTION)

def get_random_room_shape(last_shape: RoomShape = None, options: 'Options' = None) -> RoomShape:
    """Get a random room shape based on weighted probabilities and map size.
    
    Args:
        last_shape: The previous room shape, used to alternate breadth_offset
        options: Options containing map size tags
        
    Returns:
        A new RoomShape instance with randomized properties
    """
    # Get the appropriate weight index based on map size tags
    weight_idx = get_size_index_from_tags(options.tags) if options else 1  # Default to medium if no options
    
    shape = get_from_distribution(NORMALIZED_DISTRIBUTION, weight_idx)
    
    # Alternate breadth_offset if we have a previous shape
    if last_shape is not None:
        shape.breadth_offset = 0.5 if last_shape.breadth_offset == 0.0 else 0.0
        
    return shape
