"""Distribution configurations for room arrangement strategies."""
from typing import List, Tuple
from dataclasses import dataclass

from map._arrange.strategy import StrategyType
from map._arrange.linear_strategy import LinearStrategyParams
from map._arrange.distribution import Distribution, DistributionItem, WeightTuple

@dataclass 
class StrategyConfig:
    """Configuration for a room arrangement strategy."""
    strategy_type: StrategyType
    params: StrategyParams

# Global strategy distribution
STRATEGY_DISTRIBUTION: Distribution[StrategyConfig] = [
    # Small linear sequences - higher weight
    ([3], StrategyConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=1, max_rooms=2,
            min_spacing=2, max_spacing=3,
            branch_chance=0.2
        )
    )),
    
    # Medium linear sequences
    ([2], StrategyConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=2, max_rooms=3,
            min_spacing=3, max_spacing=4,
            branch_chance=0.3
        )
    )),
    
    # Large linear sequences - lower weight
    ([1], StrategyConfig(
        StrategyType.LINEAR,
        LinearStrategyParams(
            min_rooms=3, max_rooms=4,
            min_spacing=3, max_spacing=5,
            branch_chance=0.4
        )
    ))
]
