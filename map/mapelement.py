from typing import List, TYPE_CHECKING
import random
import math
import skia
from map.enums import Layers
from map.enums import Layers, RockType
from map.props.rock import SMALL_ROCK_SIZE, MEDIUM_ROCK_SIZE, Rock

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.props.prop import Prop
    from map.occupancy import OccupancyGrid
from algorithms.shapes import Rectangle, Circle
from algorithms.shapes import Shape

class MapElement:
    """Base class for all map elements.
    
    A map element has:
    - A shape (which defines its geometry)
    - A calculated bounding box based on the shape
    - Connections to other map elements
    """
    
    def __init__(self, shape: Shape, map_: 'Map') -> None:
        self._shape = shape
        self._connections: List['MapElement'] = []
        self._bounds = self._shape.bounds
        self._map = map_
        self._options = map_.options
        self._props: List['Prop'] = []
        
    def try_add_prop(self, prop: 'Prop') -> bool:
        """Try to add a prop to this element at its current position.
        
        The prop must be contained within the element's bounds.
        Does not modify the prop's position.
        
        Args:
            prop: The prop to try adding
            
        Returns:
            True if prop was added successfully, False if position was invalid
        """
        if not prop._is_valid_position(self._shape):
            return False
            
        if prop.container is not None:
            prop.container.remove_prop(prop)
        prop.container = self
        self._props.append(prop)
        return True
        
    def remove_prop(self, prop: 'Prop') -> None:
        """Remove a prop from this element."""
        if prop in self._props:
            self._props.remove(prop)
            prop.container = None
    
    def recalculate_bounds(self) -> Rectangle:
        """Calculate the bounding rectangle that encompasses the shape."""
        self._bounds = self._shape.bounds
        return self._bounds
    
    @property
    def bounds(self) -> Rectangle:
        """Get the current rectangular bounding box of this element."""
        return self._bounds
    
    @property
    def shape(self) -> Shape:
        """Get the shape of this element."""
        return self._shape
    
    @property
    def connections(self) -> List['MapElement']:
        """Get all map elements connected to this one."""
        return self._connections.copy()
    
    def connect_to(self, other: 'MapElement') -> None:
        """Connect this element to another map element.
        
        The connection is bidirectional - both elements will be connected
        to each other.
        """
        if other not in self._connections:
            self._connections.append(other)
            other.connect_to(self)
    
    def disconnect_from(self, other: 'MapElement') -> None:
        """Remove connection to another map element.
        
        The disconnection is bidirectional - both elements will be
        disconnected from each other.
        """
        if other in self._connections:
            self._connections.remove(other)
            other.disconnect_from(self)
    
    def delete(self) -> None:
        """Remove this element from its connections and map."""
        # Disconnect from all connected elements
        for connection in self.connections:
            self.disconnect_from(connection)
        # Remove from map
        if self._map is not None:
            self._map.remove_element(self)
    
    def add_rocks(self, count: int, rock_type: RockType = RockType.ANY) -> None:
        """Add a specified number of rocks to this element.
        
        Args:
            count: Number of rocks to add
            rock_type: Type of rocks to add (defaults to ANY which randomly selects types)
            
        Note: Does nothing if called on a Door element.
        """
        from map.door import Door
        from map.props.rock import Rock
        
        # Skip if this is a door
        if isinstance(self, Door):
            return
            
        bounds = self.bounds
        for _ in range(count):
            # Determine rock type
            actual_type = rock_type if rock_type != RockType.ANY else RockType.random_type()
            
            # Random rotation
            rotation = random.uniform(0, 2 * math.pi)
            
            # Try to find valid position for rock
            size = (SMALL_ROCK_SIZE if actual_type == RockType.SMALL else MEDIUM_ROCK_SIZE) * self._map.options.cell_size
            valid_pos = Rock.get_valid_position(size, self)
            
            if valid_pos:
                # Create rock at valid position
                if actual_type == RockType.SMALL:
                    rock = Rock.small_rock(valid_pos[0], valid_pos[1], self._map, rotation)
                else:  # MEDIUM
                    rock = Rock.medium_rock(valid_pos[0], valid_pos[1], self._map, rotation)
                    
                if self.try_add_prop(rock):
                    continue

    def draw(self, canvas: 'skia.Canvas', layer: 'Layers' = Layers.PROPS) -> None:
        """Draw this element on the specified layer.
        
        The base implementation draws props.
        Subclasses can override to add custom drawing behavior for different layers,
        but should call super().draw() to ensure props are drawn.
        
        Args:
            canvas: The canvas to draw on
            layer: The current drawing layer
        """
        # Always draw props regardless of layer
        for prop in self._props:
            prop.draw(canvas)
    
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape into the occupancy grid.
        
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        # Handle circles differently from rectangles
        if isinstance(self._shape, Circle):
            grid.mark_circle(self._shape, element_idx, self._options)
        else:
            # For rectangles and other shapes, use bounds
            bounds = self._shape.recalculate_bounds()
            grid.mark_rectangle(bounds, element_idx, self._options)
