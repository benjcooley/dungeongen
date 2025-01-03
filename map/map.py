"""Map container class definition."""

from typing import List, Iterator
from algorithms.shapes import ShapeGroup
from map.mapelement import MapElement
from map.room import Room
from map.door import Door
from map.passage import Passage

class Map:
    """Container for all map elements with type-specific access."""
    
    def __init__(self) -> None:
        self._elements: List[MapElement] = []
    
    def add_element(self, element: MapElement) -> None:
        """Add a map element."""
        self._elements.append(element)
    
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
            # Skip if connection is a closed door
            if isinstance(connection, Door) and not connection.open:
                continue
            self._trace_connected_region(connection, visited, region)
    
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
                shapes = [elem.shape for elem in region]
                regions.append(ShapeGroup.combine(shapes))
        
        return regions
