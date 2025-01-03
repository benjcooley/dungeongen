"""Map container class definition."""

from typing import List, Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from options import Options
from map.occupancy import OccupancyGrid
from algorithms.shapes import ShapeGroup, Rectangle
from map.mapelement import MapElement
from map.room import Room
from map.door import Door
from map.passage import Passage

class Map:
    """Container for all map elements with type-specific access."""
    
    def __init__(self, options: 'Options') -> None:
        self._elements: List[MapElement] = []
        self.options = options
        self._bounds: Rectangle | None = None
        self._bounds_dirty: bool = True
        self._occupancy: OccupancyGrid | None = None
    
    def add_element(self, element: MapElement) -> None:
        """Add a map element."""
        self._elements.append(element)
        self._bounds_dirty = True
    
    @property
    def rooms(self) -> Iterator[Room]:
        """Get all rooms in the map."""
        return (elem for elem in self._elements if isinstance(elem, Room))
    
    @property
    def doors(self) -> Iterator[Door]:
        """Get all doors in the map."""
        return (elem for elem in self._elements if isinstance(elem, Door))
    
    @property
    def passages(self) -> Iterator[Passage]:
        """Get all passages in the map."""
        return (elem for elem in self._elements if isinstance(elem, Passage))
    
    def _trace_connected_region(self, 
                              element: MapElement,
                              visited: set[MapElement],
                              region: list[MapElement]) -> None:
        """Recursively trace connected elements that aren't separated by closed doors."""
        if element in visited:
            return
        
        visited.add(element)
        region.append(element)
        
        for connection in element.connections:
            # If connection is a closed door, add its side shape but don't traverse
            if isinstance(connection, Door) and not connection.open:
                region.append(connection.get_side_shape(element))
                continue
            self._trace_connected_region(connection, visited, region)
    
    @property
    def bounds(self) -> Rectangle:
        """Get the current bounding rectangle, recalculating if needed."""
        if self._bounds_dirty or self._bounds is None:
            self._recalculate_bounds()
        return self._bounds

    def _recalculate_bounds(self) -> None:
        """Recalculate the bounding rectangle that encompasses all map elements."""
        if not self._elements:
            # Default to single cell at origin if empty
            return Rectangle(0, 0, self.options.cell_size, self.options.cell_size)
        
        # Start with first element's bounds
        bounds = self._elements[0].bounds
        
        # Expand to include all other elements
        for element in self._elements[1:]:
            elem_bounds = element.bounds
            bounds = Rectangle(
                min(bounds.x, elem_bounds.x),
                min(bounds.y, elem_bounds.y),
                max(bounds.x + bounds.width, elem_bounds.x + elem_bounds.width) - min(bounds.x, elem_bounds.x),
                max(bounds.y + bounds.height, elem_bounds.y + elem_bounds.height) - min(bounds.y, elem_bounds.y)
            )
        
        self._bounds = bounds
        self._bounds_dirty = False

    def recalculate_occupied(self) -> None:
        """Recalculate which grid spaces are occupied by map elements."""
        # Update bounds and create new occupancy grid if needed
        bounds = self.bounds
        grid_width = int(bounds.width / self.options.cell_size) + 1
        grid_height = int(bounds.height / self.options.cell_size) + 1
        
        # Create new grid or clear existing one
        if self._occupancy is None or (self._occupancy.width != grid_width or self._occupancy.height != grid_height):
            self._occupancy = OccupancyGrid(grid_width, grid_height)
        else:
            self._occupancy.clear()
        
        # Mark occupied spaces
        for idx, element in enumerate(self._elements):
            element.draw_occupied(self._occupancy, idx)
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied by any map element."""
        return self._occupancy.is_occupied(x, y)
    
    def get_element_at(self, x: int, y: int) -> Optional[MapElement]:
        """Get the map element at a grid position.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            
        Returns:
            The MapElement at that position, or None if unoccupied
        """
        idx = self._occupancy.get_occupant(x, y)
        if idx >= 0:
            return self._elements[idx]
        return None
    
    def get_regions(self) -> list[ShapeGroup]:
        """Get ShapeGroups for each contiguous region of the map.
        
        Returns:
            List of ShapeGroups, each representing a contiguous region not separated
            by closed doors.
        """
        visited: set[MapElement] = set()
        regions: list[ShapeGroup] = []
        
        # Find all connected regions
        for element in self._elements:
            if element in visited:
                continue
            
            # Trace this region
            region: list[MapElement] = []
            self._trace_connected_region(element, visited, region)
            
            # Create ShapeGroup for this region
            if region:
                # Get shapes from elements and any door shapes
                shapes = []
                for item in region:
                    if isinstance(item, MapElement):
                        shapes.append(item.shape)
                    else:  # Rectangle from door side
                        shapes.append(item)
                regions.append(ShapeGroup.combine(shapes))
        
        return regions
