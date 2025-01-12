"""Distribution system for passage lengths and door configurations."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any, Callable, List, Optional, Tuple
from options import Options
from map._arrange.arrange_utils import get_size_index_from_tags
from map._arrange.distribution import normalize_distribution, get_from_distribution
from map.door import DoorType

class PassageLength(Enum):
    """Categories of passage lengths."""
    SINGLE = auto()    # 1 cell
    SHORT = auto()     # 2-3 cells
    MEDIUM = auto()    # 4-6 cells
    LONG = auto()      # 7+ cells

@dataclass
class DoorConfig:
    """Configuration for doors at passage ends."""
    start_door: Optional[DoorType]
    end_door: Optional[DoorType]

@dataclass
class PassageConfig:
    """Complete passage configuration."""
    length: int
    doors: DoorConfig

def make_door_config(start: Optional[DoorType], end: Optional[DoorType]) -> DoorConfig:
    """Factory function for door configurations."""
    return DoorConfig(start, end)

# Generator function for very long passages
def generate_long_length(data: Dict[str, Any]) -> int:
    """Generate a length for long passages (7-10 cells)."""
    import random
    return random.randint(7, 10)

# Distribution for passage lengths based on map size
# Format: (weights[small, medium, large], item, requirement_fn)
LENGTH_DISTRIBUTION: List[Tuple[Tuple[float, float, float], int | Callable, None]] = [
    # Single cell (varies by size)
    ((2.5, 1.0, 0.5), 1, None),
    
    # Short passages (varies by size)
    ((0.8, 0.8, 0.4), 2, None),
    ((0.3, 0.7, 0.3), 3, None),
    
    # Medium passages (varies by size)
    ((0.1, 0.4, 0.8), 4, None),  # Allow 4-grid passages in small maps with low weight
    ((0.0, 0.3, 0.7), 5, None),
    ((0.0, 0.2, 0.6), 6, None),
    
    # Long passages (varies by size)
    ((0.0, 0.05, 0.3), generate_long_length, None)
]

# Door configurations for different passage lengths
# Format: (unnormalized_weight, door_config)

# Single cell passages (1 cell)
SINGLE_CELL_DOORS: List[Tuple[Tuple[float], DoorConfig, None]] = [
    ((0.7,), make_door_config(None, None), None),              # No doors
    ((0.3,), make_door_config(DoorType.OPEN, None), None),     # One open door
    ((0.2,), make_door_config(None, DoorType.OPEN), None)      # One open door
]

# Short passages (2-3 cells)
SHORT_DOORS: List[Tuple[Tuple[float], DoorConfig, None]] = [
    ((0.6,), make_door_config(DoorType.OPEN, None), None),
    ((0.6,), make_door_config(None, DoorType.OPEN), None),
    ((0.4,), make_door_config(DoorType.OPEN, DoorType.OPEN), None),
    ((0.2,), make_door_config(DoorType.CLOSED, None), None),
    ((0.2,), make_door_config(None, DoorType.CLOSED), None)
]

# Medium passages (4-6 cells)
MEDIUM_DOORS: List[Tuple[Tuple[float], DoorConfig, None]] = [
    ((0.5,), make_door_config(DoorType.OPEN, DoorType.CLOSED), None),
    ((0.5,), make_door_config(DoorType.CLOSED, DoorType.OPEN), None),
    ((0.3,), make_door_config(DoorType.CLOSED, DoorType.CLOSED), None),
    ((0.2,), make_door_config(DoorType.OPEN, DoorType.OPEN), None)
]

# Long passages (7+ cells)
LONG_DOORS: List[Tuple[Tuple[float], DoorConfig, None]] = [
    ((0.7,), make_door_config(DoorType.CLOSED, DoorType.CLOSED), None),
    ((0.2,), make_door_config(DoorType.CLOSED, DoorType.OPEN), None),
    ((0.2,), make_door_config(DoorType.OPEN, DoorType.CLOSED), None),
    ((0.1,), make_door_config(DoorType.OPEN, DoorType.OPEN), None)
]

# Normalize all distributions
NORMALIZED_LENGTH_DIST = normalize_distribution(LENGTH_DISTRIBUTION)
NORMALIZED_SINGLE_DOORS = normalize_distribution(SINGLE_CELL_DOORS)
NORMALIZED_SHORT_DOORS = normalize_distribution(SHORT_DOORS)
NORMALIZED_MEDIUM_DOORS = normalize_distribution(MEDIUM_DOORS)
NORMALIZED_LONG_DOORS = normalize_distribution(LONG_DOORS)

def get_door_distribution(length: int) -> List[Tuple[float, DoorConfig]]:
    """Get the appropriate door distribution for a passage length."""
    if length == 1:
        return NORMALIZED_SINGLE_DOORS
    elif length <= 3:
        return NORMALIZED_SHORT_DOORS
    elif length <= 6:
        return NORMALIZED_MEDIUM_DOORS
    else:
        return NORMALIZED_LONG_DOORS

def get_random_passage_config(options: 'Options') -> PassageConfig:
    """Get a random passage configuration based on weighted probabilities and map size.
    
    Args:
        options: Options containing map size tags
    """
    # Get the appropriate weight index based on map size tags
    weight_idx = get_size_index_from_tags(options.tags)
    
    # Get the length using the appropriate weight column
    length = get_from_distribution(NORMALIZED_LENGTH_DIST, weight_idx)
    
    # Then get appropriate doors for that length
    doors = get_from_distribution(get_door_distribution(length))
    
    return PassageConfig(length, doors)
