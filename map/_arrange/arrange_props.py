import random
from graphics.rotation import Rotation
from map.mapelement import MapElement
from map._props.altar import Altar
from map._arrange.proptypes import PropType
from map._props.rock import Rock
from map._props.prop import Prop
from typing import Optional

# Constants for prop density
BASE_AREA = 9.0  # Base area in grid cells (3x3 room)
MIN_PROPS_PER_BASE_AREA = 0  # Minimum props per BASE_AREA
MAX_PROPS_PER_BASE_AREA = 2  # Maximum props per BASE_AREA

def arrange_random_props(elem: MapElement, prop_types: list[PropType], min_count: int = 0, max_count: int = 3) -> list['Prop']:
    """Create and add multiple randomly selected props from a list of types.
    
    Args:
        prop_types: List of prop types to choose from
        min_count: Minimum number of props to create (overrides area-based calculation)
        max_count: Maximum number of props to create (overrides area-based calculation)
        
    Returns:
        List of successfully placed props
    """
    # Calculate room area in grid cells
    bounds = elem.bounds
    grid_width = bounds.width / 64  # Convert from pixels to grid cells
    grid_height = bounds.height / 64
    area = grid_width * grid_height
    
    # Scale prop counts based on area relative to BASE_AREA
    area_scale = area / BASE_AREA
    scaled_min = max(min_count, round(MIN_PROPS_PER_BASE_AREA * area_scale))
    scaled_max = max(max_count, round(MAX_PROPS_PER_BASE_AREA * area_scale))
    
    # Use the larger of the scaled or provided counts
    count = random.randint(scaled_min, scaled_max)
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
