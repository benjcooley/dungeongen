"""Map container class definition."""

from typing import List, Iterator
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
