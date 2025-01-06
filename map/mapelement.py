from typing import List, Optional, TYPE_CHECKING

from map.props.proptypes import PropType
import random
import math
import skia
from map.enums import Layers
from map.enums import Layers

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
        
    def create_props(self, prop_type: 'PropType', min_count: int = 1, max_count: int = 1, options: dict = None) -> list['Prop']:
        """Create and add multiple props of the specified type.
        
        Args:
            prop_type: Type of prop to create
            min_count: Minimum number of props to create
            max_count: Maximum number of props to create
            options: Optional dict of prop-specific options
            
        Returns:
            List of successfully placed props
        """
        from map.props.rock import Rock  # Avoid circular import
        
        count = random.randint(min_count, max_count)
        placed_props = []
        
        # Create and try to place each prop
        for _ in range(count):
            if prop := self.create_prop(prop_type, options):
                placed_props.append(prop)
                
        return placed_props
        
    def create_prop(self, prop_type: 'PropType', options: dict = None) -> Optional['Prop']:
        """Create and add a single prop of the specified type.
        
        Args:
            prop_type: Type of prop to create
            options: Optional dict of prop-specific options
            
        Returns:
            The created prop if successfully placed, None otherwise
        """
        from map.props.rock import Rock  # Avoid circular import
        
        # Create prop based on type
        if prop_type == PropType.SMALL_ROCK:
            prop = Rock.create_small()
        elif prop_type == PropType.MEDIUM_ROCK:
            prop = Rock.create_medium()
        elif prop_type == PropType.LARGE_ROCK:
            prop = Rock.create_large()
        else:
            raise ValueError(f"Unsupported prop type: {prop_type}")
            
        # Try to add and place the prop
        self.add_prop(prop)
        if prop.place_random_position() is None:
            self.remove_prop(prop)
            return None
            
        return prop
        
    def add_prop(self, prop: 'Prop') -> None:
        """Add a prop to this element at its current position.
        
        Does not modify the prop's position.
        
        Args:
            prop: The prop to add
        """
        if prop.container is not None:
            prop.container.remove_prop(prop)
            
        prop.container = self
        prop._map = self._map
        self._props.append(prop)
        
    def remove_prop(self, prop: 'Prop') -> None:
        """Remove a prop from this element."""
        if prop in self._props:
            self._props.remove(prop)
            prop.container = None
            prop._map = None
    
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
    

    @classmethod
    def is_decoration(cls) -> bool:
        """Whether this element is a decoration that should be drawn before other props."""
        return False

    def draw(self, canvas: 'skia.Canvas', layer: 'Layers' = Layers.PROPS) -> None:
        """Draw this element on the specified layer.
        
        The base implementation draws props.
        Subclasses can override to add custom drawing behavior for different layers,
        but should call super().draw() to ensure props are drawn.
        
        Args:
            canvas: The canvas to draw on
            layer: The current drawing layer
        """
        if layer == Layers.PROPS:
            # Draw decoration props first
            for prop in self._props:
                if prop.__class__.is_decoration():
                    prop.draw(canvas)
                    
            # Then draw non-decoration props
            for prop in self._props:
                if not prop.__class__.is_decoration():
                    prop.draw(canvas)
        elif layer == Layers.SHADOW:
            # Only draw shadows for non-decoration props
            for prop in self._props:
                if not prop.__class__.is_decoration():
                    prop.draw(canvas, layer)
        else:
            # For other layers, draw all props
            for prop in self._props:
                prop.draw(canvas, layer)
    
    def prop_intersects(self, prop: 'Prop') -> list['Prop']:
        """Check if a prop intersects with any non-decoration props in this element.
        
        Args:
            prop: The prop to check for intersections
            
        Returns:
            List of non-decoration props that intersect with the given prop
        """
        intersecting = []
        for existing_prop in self._props:
            if not existing_prop.is_decoration:
                # Check bounding box intersection first
                if (prop.bounds.x < existing_prop.bounds.x + existing_prop.bounds.width and
                    prop.bounds.x + prop.bounds.width > existing_prop.bounds.x and
                    prop.bounds.y < existing_prop.bounds.y + existing_prop.bounds.height and
                    prop.bounds.y + prop.bounds.height > existing_prop.bounds.y):
                    intersecting.append(existing_prop)
        return intersecting

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is contained within this element's shape."""
        return self._shape.contains(x, y)
        
    def contains_rectangle(self, rect: Rectangle, margin: float = 0) -> bool:
        """Check if a rectangle is fully contained within this element's shape.
        
        Args:
            rect: Rectangle to check
            margin: Optional margin to maintain from shape edges
            
        Returns:
            True if rectangle is fully contained
        """
        # Check all four corners
        corners = [
            (rect.x + margin, rect.y + margin),
            (rect.x + rect.width - margin, rect.y + margin),
            (rect.x + margin, rect.y + rect.height - margin),
            (rect.x + rect.width - margin, rect.y + rect.height - margin)
        ]
        return all(self._shape.contains(x, y) for x, y in corners)
        
    def contains_circle(self, circle: Circle, margin: float = 0) -> bool:
        """Check if a circle is fully contained within this element's shape.
        
        Args:
            circle: Circle to check
            margin: Optional margin to maintain from shape edges
            
        Returns:
            True if circle is fully contained
        """
        # Check points around the circle perimeter
        num_points = 8
        for i in range(num_points):
            angle = (i * 2 * math.pi / num_points)
            x = circle.cx + (circle.radius + margin) * math.cos(angle)
            y = circle.cy + (circle.radius + margin) * math.sin(angle)
            if not self._shape.contains(x, y):
                return False
        return True

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
