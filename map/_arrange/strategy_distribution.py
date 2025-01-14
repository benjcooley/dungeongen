"""Strategy distribution configuration."""
from typing import List, Tuple, Type, Optional
from dataclasses import dataclass

from map._arrange.strategy import Strategy, StrategyParams, StrategyType
from map._arrange.linear_strategy import LinearStrategy, LinearStrategyParams
from map._arrange.distribution import normalize_distribution, get_from_distribution

# Define strategy distribution with weights for different map sizes
# Format: (weights[small, medium, large], strategy_class, params)
_STRATEGY_DISTRIBUTION: List[Tuple[Tuple[float, float, float], Type[Strategy], StrategyParams]] = [
    # Linear strategies with different parameters
    ((3.0, 2.0, 1.0), LinearStrategy, LinearStrategyParams(
        min_rooms=1, max_rooms=2, min_spacing=2, max_spacing=3, branch_chance=0.2
    )),
    ((2.0, 2.5, 1.5), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=3, min_spacing=2, max_spacing=4, branch_chance=0.3
    )),
    ((1.0, 2.0, 2.5), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=4, min_spacing=3, max_spacing=5, branch_chance=0.4
    )),
]

# Normalize the distribution once at module load
NORMALIZED_STRATEGY_DISTRIBUTION = normalize_distribution(_STRATEGY_DISTRIBUTION)

def get_random_arrange_strategy() -> Tuple[Type[Strategy], StrategyParams]:
    """Get a random strategy and its parameters based on weighted probabilities.
    
    Returns:
        Tuple of (StrategyClass, StrategyParams)
    """
    # For now we use weight index 1 (medium) until we implement size-based selection
    weight_idx = 1
    
    strategy_class, params = get_from_distribution(NORMALIZED_STRATEGY_DISTRIBUTION, weight_idx)
    return strategy_class, params

