"""Strategy distribution configuration."""
from typing import List, Tuple, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dungeongen.options import Options

from dungeongen.map._arrange.arrange_utils import get_size_index_from_tags
from dataclasses import dataclass

from dungeongen.map._arrange.strategy import Strategy, StrategyParams, StrategyType
from dungeongen.map._arrange.linear_strategy import LinearStrategy, LinearStrategyParams
from dungeongen.map._arrange.symmetrical_strategy import SymmetricalStrategy, SymmetricalStrategyParams
from dungeongen.map._arrange.distribution import normalize_distribution, get_from_distribution
from dungeongen.map._arrange.arrange_enums import GrowDirection

# Define strategy distribution with weights for different map sizes
# Format: (weights[small, medium, large], item, requirement_fn)
_STRATEGY_DISTRIBUTION: List[Tuple[Tuple[float, float, float], Tuple[Type[Strategy], StrategyParams], None]] = [
    # Symmetrical strategies - increased weights across all sizes
    ((3.0, 4.0, 4.5), (SymmetricalStrategy, SymmetricalStrategyParams(
        min_rooms=2, max_rooms=4, iterations=2
    )), None),
    ((2.5, 3.5, 4.0), (SymmetricalStrategy, SymmetricalStrategyParams(
        min_rooms=4, max_rooms=6, iterations=3
    )), None),
    
    # Linear strategies with different parameters - reduced weights
    ((2.0, 1.5, 1.0), (LinearStrategy, LinearStrategyParams(
        min_rooms=1, max_rooms=2, min_spacing=2, max_spacing=3,
        grow_direction=GrowDirection.FORWARD
    )), None),
    ((1.5, 2.0, 1.0), (LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=3, min_spacing=2, max_spacing=4,
        grow_direction=GrowDirection.BOTH
    )), None),
    ((1.0, 1.5, 2.0), (LinearStrategy, LinearStrategyParams(
        min_rooms=2, max_rooms=4, min_spacing=3, max_spacing=5,
        grow_direction=GrowDirection.BACKWARD
    )), None),
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

