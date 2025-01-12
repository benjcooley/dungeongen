"""Distribution system for passage lengths and door configurations."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Tuple
from map._arrange.distribution import normalize_distribution, try_get_from_distribution
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

# Distribution for passage lengths
# Format: (unnormalized_weight, length or generator)
LENGTH_DISTRIBUTION: List[Tuple[float, int]] = [
    # Single cell (very common)
    (1.0, 1),
    
    # Short passages (common)
    (0.8, 2),
    (0.7, 3),
    
    # Medium passages (less common)
    (0.4, 4),
    (0.3, 5),
    (0.2, 6),
    
    # Long passages (rare)
    (0.05, generate_long_length)
]

# Door configurations for different passage lengths
# Format: (unnormalized_weight, door_config)

# Single cell passages (1 cell)
SINGLE_CELL_DOORS: List[Tuple[float, DoorConfig]] = [
    (0.7, make_door_config(None, None)),              # No doors
    (0.3, make_door_config(DoorType.OPEN, None)),     # One open door
    (0.2, make_door_config(None, DoorType.OPEN))      # One open door
]

# Short passages (2-3 cells)
SHORT_DOORS: List[Tuple[float, DoorConfig]] = [
    (0.6, make_door_config(DoorType.OPEN, None)),
    (0.6, make_door_config(None, DoorType.OPEN)),
    (0.4, make_door_config(DoorType.OPEN, DoorType.OPEN)),
    (0.2, make_door_config(DoorType.CLOSED, None)),
    (0.2, make_door_config(None, DoorType.CLOSED))
]

# Medium passages (4-6 cells)
MEDIUM_DOORS: List[Tuple[float, DoorConfig]] = [
    (0.5, make_door_config(DoorType.OPEN, DoorType.CLOSED)),
    (0.5, make_door_config(DoorType.CLOSED, DoorType.OPEN)),
    (0.3, make_door_config(DoorType.CLOSED, DoorType.CLOSED)),
    (0.2, make_door_config(DoorType.OPEN, DoorType.OPEN))
]

# Long passages (7+ cells)
LONG_DOORS: List[Tuple[float, DoorConfig]] = [
    (0.7, make_door_config(DoorType.CLOSED, DoorType.CLOSED)),
    (0.2, make_door_config(DoorType.CLOSED, DoorType.OPEN)),
    (0.2, make_door_config(DoorType.OPEN, DoorType.CLOSED)),
    (0.1, make_door_config(DoorType.OPEN, DoorType.OPEN))
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

def get_random_passage_config() -> PassageConfig:
    """Get a random passage configuration based on weighted probabilities."""
    # First get the length
    length = get_from_distribution(NORMALIZED_LENGTH_DIST)
    
    # Then get appropriate doors for that length
    doors = get_from_distribution(get_door_distribution(length))
    
    return PassageConfig(length, doors)
