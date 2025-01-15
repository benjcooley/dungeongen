"""Room shape generation with controlled size distributions."""

from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, Tuple, List
from map._arrange.arrange_utils import get_size_index_from_tags
from options import Options
from map.room import RoomType, RoomShape
from map._arrange.distribution import normalize_distribution, get_from_distribution

@dataclass
class RoomShape:
    """Defines the shape and dimensions of a room.
    
    Attributes:
        room_type: The type of room (rectangular, circular, etc)
        breadth: Width perpendicular to growth direction
        depth: Length parallel to growth direction
        breadth_offset: Optional offset for passage placement (default 0.0)
    """
    room_type: RoomType
    breadth: int
    depth: int
    breadth_offset: float = 0.0

def generate_large_room(data: Dict[str, Any]) -> RoomShape:
    """Gets a random room shape given the current options.
    
    Generates rooms with odd dimensions, preferring longer rooms over square ones.
    Maximum area scales with map size:
    - Medium maps: max area = 63 (e.g. 7x9)
    - Large maps: max area = 99 (e.g. 9x11)
    """
    # Get map size index (1=medium, 2=large)
    size_idx = data.get('size_index', 1)
    
    # Set max area based on map size
    max_area = 63 if size_idx == 1 else 99
    
    # Generate random odd dimensions that multiply to <= max_area
    # Prefer longer rooms by picking depth first
    import random
    
    # Generate odd depth first (deeper rooms are more interesting)
    max_depth = int((max_area ** 0.5) * 1.2)  # Allow slightly longer than square
    depth = random.randrange(7, max_depth + 1, 2)  # Start at 7, increment by 2
    
    # Calculate max width based on depth and area
    max_width = min(11, max_area // depth)
    if max_width % 2 == 0:
        max_width -= 1
        
    # Generate odd width
    width = random.randrange(5, max_width + 1, 2)
    
    return RoomShape(RoomType.RECTANGULAR, width, depth)

# Define room shape distribution with weights for different map sizes
# Format: (weights[small, medium, large], item, requirement_fn)
_ROOM_DISTRIBUTION: List[Tuple[Tuple[float, float, float], RoomShape | Callable, None]] = [
    # Circular rooms (very common in medium maps)
    ((3.0, 4.0, 1.5), RoomShape(RoomType.CIRCULAR, 3, 3), None),  # Increased weight for 3x3
    ((2.0, 2.5, 1.2), RoomShape(RoomType.CIRCULAR, 5, 5), None),  # Slightly increased for 5x5
    ((0.8, 1.5, 1.0), RoomShape(RoomType.CIRCULAR, 7, 7), None),  # More common in medium
    ((0.2, 1.0, 0.8), RoomShape(RoomType.CIRCULAR, 9, 9), None),  # More common in medium

    # Small asymmetric rooms (rare, slightly more common in small maps)
    ((0.3, 0.2, 0.1), RoomShape(RoomType.RECTANGULAR, 3, 2), None),
    ((0.2, 0.1, 0.05), RoomShape(RoomType.RECTANGULAR, 2, 3), None),

    # Common small symmetric rooms
    ((3.0, 1.5, 0.8), RoomShape(RoomType.RECTANGULAR, 3, 3), None),
    ((2.0, 1.2, 0.6), RoomShape(RoomType.RECTANGULAR, 3, 4), None),
    ((1.5, 1.0, 0.5), RoomShape(RoomType.RECTANGULAR, 4, 3), None),
    
    # Medium rectangular rooms (balanced distribution)
    ((2.5, 2.0, 1.2), RoomShape(RoomType.RECTANGULAR, 3, 4), None),
    ((2.0, 2.0, 1.2), RoomShape(RoomType.RECTANGULAR, 3, 5), None),
    ((0.2, 1.5, 1.0), RoomShape(RoomType.RECTANGULAR, 3, 7), None),
    ((0.2, 1.8, 1.2), RoomShape(RoomType.RECTANGULAR, 5, 5), None),  # Increased weights for 5x5 rectangular
    ((0.0, 1.0, 0.7), RoomShape(RoomType.RECTANGULAR, 5, 7), None),

    # Larger fixed rooms (more common in larger maps)
    ((0.0, 0.8, 1.2), RoomShape(RoomType.RECTANGULAR, 7, 7), None),
    ((0.0, 0.6, 1.0), RoomShape(RoomType.RECTANGULAR, 7, 9), None),
    
    # Dynamic large rooms (only in medium/large maps)
    ((0.0, 1.0, 2.0), generate_large_room, None)
]

# Normalize the distribution once at module load
NORMALIZED_ROOM_DISTRIBUTION = normalize_distribution(_ROOM_DISTRIBUTION)

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
    
    shape = get_from_distribution(NORMALIZED_ROOM_DISTRIBUTION, weight_idx)
    
    # Alternate breadth_offset if we have a previous shape
    if last_shape is not None:
        shape.breadth_offset = 0.5 if last_shape.breadth_offset == 0.0 else 0.0
        
    return shape
