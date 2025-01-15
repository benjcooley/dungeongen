"""Strategy distribution configuration."""
from typing import List, Tuple, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from options import Options

from map._arrange.arrange_utils import get_size_index_from_tags
from dataclasses import dataclass

from map._arrange.strategy import Strategy, StrategyParams, StrategyType
from map._arrange.linear_strategy import LinearStrategy, LinearStrategyParams
from map._arrange.symmetrical_strategy import SymmetricalStrategy, SymmetricalStrategyParams
from map._arrange.distribution import normalize_distribution, try_get_from_distribution
from map._arrange.arrange_enums import GrowDirection

# Define strategy distribution with weights for different map sizes
# Format: ((weights[small, medium, large], None), strategy_class, params)
_STRATEGY_DISTRIBUTION: List[Tuple[Tuple[Tuple[float, float, float], None], Type[Strategy], StrategyParams]] = [
    # Symmetrical strategies
    (((1.0, 2.0, 2.5), None), SymmetricalStrategy, SymmetricalStrategyParams(
        min_rooms=2, max_rooms=4, iterations=2
    )),
    (((0.5, 1.5, 2.0), None), SymmetricalStrategy, SymmetricalStrategyParams(
        min_rooms=4, max_rooms=6, iterations=3
    )),
    
    # Linear strategies with different parameters
    (((3.0, 2.0, 1.0), None), LinearStrategy, LinearStrategyParams(
        min_rooms=1, max_rooms=2, min_spacing=2, max_spacing=3,
        grow_direction=GrowDirection.FORWARD
    )),
    (((2.0, 2.5, 1.5), None), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=3, min_spacing=2, max_spacing=4,
        grow_direction=GrowDirection.BOTH
    )),
    (((1.0, 2.0, 2.5), None), LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=4, min_spacing=3, max_spacing=5,
        grow_direction=GrowDirection.BACKWARD
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
    
    strategy_class, params = try_get_from_distribution(NORMALIZED_STRATEGY_DISTRIBUTION, weight_idx)
    return strategy_class, params

