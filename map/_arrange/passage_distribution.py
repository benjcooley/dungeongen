"""Distribution system for passage lengths and door configurations."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from map._arrange.distribution import normalize_distribution, get_from_distribution
from map.door import DoorType

@dataclass
class PassageConfig:
    """Configuration for a passage including length and doors."""
    length: int  # Grid cells
    start_door: Optional[DoorType]
    end_door: Optional[DoorType]

def make_passage_config(length: int, start_door: Optional[DoorType], end_door: Optional[DoorType]) -> PassageConfig:
    """Factory function for creating passage configs."""
    return PassageConfig(length, start_door, end_door)

# Generator function for very long passages
def generate_long_passage(data: Dict[str, Any]) -> PassageConfig:
    """Generate a long passage (8-12 cells) with appropriate doors."""
    import random
    length = random.randint(8, 12)
    return PassageConfig(length, DoorType.CLOSED, DoorType.CLOSED)

# Distribution for passage lengths
# Format: (unnormalized_weight, length or generator)
LENGTH_DISTRIBUTION: List[Tuple[float, PassageConfig]] = [
    # Very short passages (1-2 cells) - most common
    (1.0, make_passage_config(1, None, DoorType.OPEN)),
    (1.0, make_passage_config(1, DoorType.OPEN, None)),
    (0.8, make_passage_config(2, DoorType.OPEN, DoorType.OPEN)),
    
    # Medium passages (3-4 cells) - common
    (0.6, make_passage_config(3, DoorType.OPEN, DoorType.CLOSED)),
    (0.6, make_passage_config(3, DoorType.CLOSED, DoorType.OPEN)),
    (0.4, make_passage_config(4, DoorType.CLOSED, DoorType.CLOSED)),
    
    # Longer passages (5-7 cells) - less common
    (0.3, make_passage_config(5, DoorType.CLOSED, DoorType.CLOSED)),
    (0.2, make_passage_config(6, DoorType.CLOSED, DoorType.CLOSED)),
    (0.1, make_passage_config(7, DoorType.CLOSED, DoorType.CLOSED)),
    
    # Very long passages (8+ cells) - rare
    (0.05, generate_long_passage)
]

# Normalize the distribution once at module load
NORMALIZED_DISTRIBUTION = normalize_distribution(LENGTH_DISTRIBUTION)

def get_random_passage_config() -> PassageConfig:
    """Get a random passage configuration based on weighted probabilities."""
    return get_from_distribution(NORMALIZED_DISTRIBUTION)
