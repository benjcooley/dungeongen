from abc import abstractmethod
from typing import List, Optional, TYPE_CHECKING, Sequence, Union
import random
import math
import skia
from map.enums import Layers
from constants import CELL_SIZE
from debug_config import debug_draw, DebugDrawFlags

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map._props.prop import Prop
    from map.occupancy import OccupancyGrid
from graphics.shapes import Rectangle, Circle
from graphics.shapes import Shape

class MapElement:
    """Base class for all map elements.
    
    A map element has:
    - A shape (which defines its geometry)
    - Connections to other map elements
    - Props (decorations or other elements)
    """
    
    def __init__(self, shape: Shape) -> None:
        self._shape = shape
        self._map = None
        self._options = None
        self._bounds = self._shape.bounds
        self._connections: List['MapElement'] = []
        self._props: List['Prop'] = []

    @property
    def bounds(self) -> Rectangle:
        """Get the current rectangular bounding box of this element."""
        return self._bounds
    
    @property
    def shape(self) -> Shape:
        """Get the shape of this element."""
        return self._shape
    
    def options(self) -> 'Options':
        """Get the current options."""
        return self._options
    
    @property
    def map(self) -> 'Map':
        """Get the current map element is in."""
        return self._map

    @property
    def connections(self) -> Sequence['MapElement']:
        """Read only access to element's connections list."""
        return self._connections
    
    @property
    def connection_count(self) -> int:
        """Get the number of connections this element has."""
        return len(self._connections)
    
    @property
    def props(self) -> Sequence['Prop']:
        """Read only access to element's prop list."""
        return self._props
    
    @property
    def prop_count(self) -> int:
        """Get the number of props in this element."""
        return len(self._props)

    def add_prop(self, prop: 'Prop') -> None:
        """Add a prop to this element at its current position.
        
        Does not modify the prop's position.
        
        Args:
            prop: The prop to add
        """
        if prop.container is not None:
            prop.container.remove_prop(prop)
            
        prop._container = self
        prop._map = self._map
        prop._options = self._options
        self._props.append(prop)

    def remove_prop(self, prop: 'Prop') -> None:
        """Remove a prop from this element."""
        if prop in self._props:
            self._props.remove(prop)
            prop._container = None
            prop._map = None
    
    def recalculate_bounds(self) -> Rectangle:
        """Calculate the bounding rectangle that encompasses the shape."""
        self._bounds = self._shape.bounds
        return self._bounds
    
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

    def get_map_index(self) -> int:
        """Get this element's index in the map.
        
        Returns:
            The element's index, or -1 if not in a map
        """
        if self._map is None:
            return -1
        try:
            return self._map._elements.index(self)
        except ValueError:
            return -1

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
                if prop.prop_type.is_decoration:
                    prop.draw(canvas, layer)
                    
            # Then draw non-decoration props
            for prop in self._props:
                if not prop.prop_type.is_decoration:
                    prop.draw(canvas, layer)
        elif layer == Layers.SHADOW:
            # Only draw shadows for non-decoration props
            for prop in self._props:
                if not prop.prop_type.is_decoration:
                    prop.draw(canvas, layer)
        else:
            # For other layers, draw all props
            for prop in self._props:
                prop.draw(canvas, layer)
                
        # Draw debug visualization on overlay layer if enabled
        if layer == Layers.OVERLAY and debug_draw.is_enabled(DebugDrawFlags.PROP_BOUNDS):
            debug_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=2,
                Color=skia.Color(255, 0, 0)  # Red
            )
            for prop in self._props:
                prop.shape.draw(canvas, debug_paint)
                
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

    def get_grid_position(self, grid_x: int, grid_y: int) -> tuple[float, float]:
        """Convert grid coordinates relative to this element into map coordinates.
        
        Args:
            grid_x: X coordinate in grid units relative to element's top-left
            grid_y: Y coordinate in grid units relative to element's top-left
            
        Returns:
            Tuple of (x,y) coordinates in map space
        """
        return (self._bounds.x + (grid_x * CELL_SIZE), 
                self._bounds.y + (grid_y * CELL_SIZE))

    @abstractmethod
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape into the occupancy grid.
            
        Args:
            grid: The occupancy grid to mark
            element_idx: Index of this element in the map
        """
        pass
