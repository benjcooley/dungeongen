import random
from algorithms.rotation import Rotation
from map.mapelement import MapElement
from map._props.altar import Altar
from map._arrange.proptypes import PropType
from map._props.rock import Rock
from map._props.prop import Prop
from typing import Optional

def arrange_random_props(elem: MapElement, prop_types: list[PropType], min_count: int = 0, max_count: int = 3) -> list['Prop']:
    """Create and add multiple randomly selected props from a list of types.
    
    Args:
        prop_types: List of prop types to choose from
        min_count: Minimum number of props to create
        max_count: Maximum number of props to create
        
    Returns:
        List of successfully placed props
    """
    count = random.randint(min_count, max_count)
    placed_props = []
    
    # Create and try to place each prop
    for _ in range(count):
        # Randomly select a prop type
        prop_type = random.choice(prop_types)
        if prop := arrange_prop(elem, prop_type):
            placed_props.append(prop)
            
    return placed_props
    
def arrange_prop(elem: MapElement, prop_type: 'PropType') -> Optional['Prop']:
    """Create a single prop of the specified type.
    
    Args:
        prop_type: Type of prop to create
        
    Returns:
        The created prop if successfully placed, None otherwise
    """
    # Create prop based on type
    if prop_type == PropType.SMALL_ROCK:
        prop = Rock.create_small()
    elif prop_type == PropType.MEDIUM_ROCK:
        prop = Rock.create_medium()
    elif prop_type == PropType.LARGE_ROCK:
        prop = Rock.create_large()
    elif prop_type == PropType.ALTAR:
        # Create altar with random rotation
        prop = Altar.create(rotation=Rotation.random_cardinal_rotation())
    else:
        raise ValueError(f"Unsupported prop type: {prop_type}")
        
    # Try to add and place the prop
    elem.add_prop(prop)
    if prop.place_random_position() is None:
        elem.remove_prop(prop)
        return None
        
    return prop
