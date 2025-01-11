"""Generic distribution system for weighted random selection with generator functions."""

from typing import Any, Callable, Dict, List, Tuple, TypeVar, Union
import random

T = TypeVar('T')
DistributionItem = Union[T, Callable[[Dict[str, Any]], T]]
Distribution = List[Tuple[float, DistributionItem[T]]]

def normalize_distribution(dist: Distribution[T]) -> Distribution[T]:
    """Normalize weights in a distribution to sum to 1.0."""
    total = sum(weight for weight, _ in dist)
    return [(weight / total, item) for weight, item in dist]

def get_from_distribution(dist: Distribution[T], gen_data: Dict[str, Any] = None) -> T:
    """Get a random item from a normalized distribution.
    
    Args:
        dist: List of (weight, item) tuples where weights sum to 1.0
        gen_data: Optional dictionary passed to generator functions
        
    Returns:
        Selected item, calling generator function if needed
    """
    # Generate random value between 0 and 1
    r = random.random()
    
    # Find the selected item
    cumulative = 0.0
    for weight, item in dist:
        cumulative += weight
        if r <= cumulative:
            # If item is callable, it's a generator function
            if callable(item):
                return item(gen_data or {})
            return item
            
    # Fallback to last item (handles floating point imprecision)
    last_item = dist[-1][1]
    if callable(last_item):
        return last_item(gen_data or {})
    return last_item
