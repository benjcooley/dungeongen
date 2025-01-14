"""Strategy distribution configuration."""
from typing import List, Tuple, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from options import Options

from map._arrange.arrange_utils import get_size_index_from_tags
from dataclasses import dataclass

from map._arrange.strategy import Strategy, StrategyParams, StrategyType
from map._arrange.linear_strategy import LinearStrategy, LinearStrategyParams
from map._arrange.distribution import normalize_distribution, get_from_distribution

# Define strategy distribution with weights for different map sizes
# Format: (weights[small, medium, large], strategy_class, params)
_STRATEGY_DISTRIBUTION: List[Tuple[Tuple[float, float, float], Type[Strategy], StrategyParams]] = [
    # Linear strategies with different parameters
    ((3.0, 2.0, 1.0), LinearStrategy, LinearStrategyParams(
        min_rooms=1, max_rooms=2, min_spacing=2, max_spacing=3
    )),
    ((2.0, 2.5, 1.5), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=3, min_spacing=2, max_spacing=4
    )),
    ((1.0, 2.0, 2.5), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=4, min_spacing=3, max_spacing=5
    )),
]

# Normalize the distribution once at module load
NORMALIZED_STRATEGY_DISTRIBUTION = normalize_distribution(_STRATEGY_DISTRIBUTION)

def get_random_arrange_strategy(options: Optional['Options'] = None) -> Tuple[Type[Strategy], StrategyParams]:
    """Get a random strategy and its parameters based on weighted probabilities.
    
    Args:
        options: Options containing map size tags
        
    Returns:
        Tuple of (StrategyClass, StrategyParams)
    """
    # Get the appropriate weight index based on map size tags
    weight_idx = get_size_index_from_tags(options.tags) if options else 1  # Default to medium if no options
    
    strategy_class, params = get_from_distribution(NORMALIZED_STRATEGY_DISTRIBUTION, weight_idx)
    return strategy_class, params

