"""Generic distribution system for weighted random selection with generator functions."""

from typing import Any, Callable, Dict, List, Sequence, Tuple, TypeVar, Union
import random

T = TypeVar('T')
DistributionItem = Union[T, Callable[[Dict[str, Any]], T]]
WeightTuple = Tuple[float, ...]  # Multiple weights per item
RequirementFn = Callable[[Dict[str, Any], List[Tuple[WeightTuple, DistributionItem[T]]], int], bool]
Distribution = List[Tuple[WeightTuple, DistributionItem[T], RequirementFn | None]]

def normalize_distribution(dist: Distribution[T]) -> List[Tuple[WeightTuple, DistributionItem[T], RequirementFn | None]]:
    """Normalize each column of weights in a distribution to sum to 1.0.
    
    Args:
        dist: List of (weights, item, requirement_fn) tuples
        
    Returns:
        Distribution with normalized weight columns
    """
    if not dist:
        return []
        
    # Get number of weight columns from first item
    num_weights = len(dist[0][0])
    
    # Calculate column totals
    totals = [0.0] * num_weights
    for weights, _, _ in dist:
        for i, weight in enumerate(weights):
            totals[i] += weight
            
    # Normalize each column
    normalized = []
    for weights, item, req_fn in dist:
        norm_weights = tuple(w / totals[i] if totals[i] > 0 else 0 
                           for i, w in enumerate(weights))
        normalized.append((norm_weights, item, req_fn))
        
    return normalized

def get_from_distribution(
    dist: Distribution[T],
    weight_index: int = 0,
    gen_data: Dict[str, Any] = None
) -> T:
    """Get a random item from a normalized distribution, for simple distributions without requirements.
    
    This is the simpler version that does not handle requirement functions. Use try_get_from_distribution()
    if you need support for requirements.
    
    Args:
        dist: List of (weights, item, requirement_fn) tuples
        weight_index: Which weight column to use (default 0)
        gen_data: Optional dictionary passed to generator functions
        
    Returns:
        Selected item, calling generator function if needed
        
    Raises:
        ValueError: If any items have requirement functions
    """
    gen_data = gen_data or {}
    
    # Check no requirements exist
    for weights, item, req_fn in dist:
        if req_fn is not None:
            raise ValueError("Distribution contains requirement functions but requirements are not allowed")
    
    # Generate random value between 0 and 1
    r = random.random()
    
    # Find the selected item using specified weight column
    cumulative = 0.0
    for weights, item, _ in dist:
        cumulative += weights[weight_index]
        if r <= cumulative:
            # If item is callable, it's a generator function
            if callable(item):
                return item(gen_data)
            return item
            
    # Fallback to last item (handles floating point imprecision)
    last_item = dist[-1][1]
    if callable(last_item):
        return last_item(gen_data)
    return last_item

def try_get_from_distribution(
    dist: Distribution[T],
    weight_index: int = 0,
    gen_data: Dict[str, Any] = None,
    max_attempts: int = 100
) -> Optional[T]:
    """Try to get a random item from a normalized distribution, handling requirements.
    
    This is the more complex version that supports requirement functions and will retry
    multiple times if requirements aren't met. Use get_from_distribution() if you don't
    need requirement handling.
    
    Args:
        dist: List of (weights, item, requirement_fn) tuples
        weight_index: Which weight column to use (default 0)
        gen_data: Optional dictionary passed to generator/requirement functions
        max_attempts: Maximum number of selection attempts before giving up
        
    Returns:
        Selected item if found, None if no valid item could be selected after max_attempts
    """
    gen_data = gen_data or {}
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        
        # Generate random value between 0 and 1
        r = random.random()
        
        # Find the selected item using specified weight column
        cumulative = 0.0
        for weights, item, req_fn in dist:
            cumulative += weights[weight_index]
            if r <= cumulative:
                # Check requirements if present
                if req_fn is None or req_fn(gen_data, dist, weight_index):
                    # If item is callable, it's a generator function
                    if callable(item):
                        return item(gen_data)
                    return item
                # Requirements failed, try again
                break
                
        # If we get here, either requirements failed or we had floating point imprecision
        # Try the last item if it meets requirements
        last_weights, last_item, last_req_fn = dist[-1]
        if last_req_fn is None or last_req_fn(gen_data, dist, weight_index):
            if callable(last_item):
                return last_item(gen_data)
            return last_item
            
    raise ValueError(f"Could not find valid distribution item after {max_attempts} attempts")
