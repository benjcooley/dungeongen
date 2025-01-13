"""Distribution configurations for room arrangement strategies and sizes."""
from dataclasses import dataclass
from typing import List, Tuple

from map._arrange.strategy import StrategyType, StrategyParams
from map._arrange.linear_strategy import LinearStrategyParams
from map._arrange.distribution import Distribution

@dataclass
class RoomConfig:
    """Configuration for room arrangement."""
    strategy_type: StrategyType
    params: StrategyParams

@dataclass
class RoomSizeConfig:
    """Configuration for room size ranges."""
    min_size: int
    max_size: int

# Global room size distribution
ROOM_SIZE_DISTRIBUTION: Distribution[RoomSizeConfig] = [
    # Small rooms - higher weight
    ([3], RoomSizeConfig(
        min_size=3,
        max_size=4
    )),
    
    # Medium rooms
    ([2], RoomSizeConfig(
        min_size=4,
        max_size=6
    )),
    
    # Large rooms - lower weight
    ([1], RoomSizeConfig(
        min_size=6,
        max_size=7
    ))
]

# Global room distribution
ROOM_DISTRIBUTION: Distribution[RoomConfig] = [
    # Small linear sequences - higher weight
    ([3], RoomConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=1, max_rooms=2,
            min_spacing=2, max_spacing=3,
            branch_chance=0.2
        )
    )),
    
    # Medium linear sequences
    ([2], RoomConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=2, max_rooms=3,
            min_spacing=3, max_spacing=4,
            branch_chance=0.3
        )
    )),
    
    # Large linear sequences - lower weight
    ([1], RoomConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=3, max_rooms=4,
            min_spacing=3, max_spacing=5,
            branch_chance=0.4
        )
    ))
]
