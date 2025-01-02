from typing import Dict, List, Protocol, Tuple, TypeVar
import math

class Spatial2D(Protocol):
    """Protocol for objects that can be stored in the spatial hash."""
    def get_position(self) -> Tuple[float, float]:
        """Return the x, y position of the object."""
        ...

T = TypeVar('T', bound=Spatial2D)
GridCell = Tuple[int, int]

class SpatialHash[T]:
    """Grid-based spatial hashing for objects implementing Spatial2D protocol."""
    
    def __init__(self, cell_size: float) -> None:
        self.cell_size = cell_size
        self.grid: Dict[GridCell, List[T]] = {}

    def _hash(self, x: float, y: float) -> GridCell:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def add(self, obj: T) -> None:
        cx, cy = obj.get_position()
        cell = self._hash(cx, cy)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(obj)

    def get_neighbors(self, obj: T, radius: float) -> List[T]:
        cx, cy = obj.get_position()
        cell_x, cell_y = self._hash(cx, cy)
        neighbors: List[T] = []
        cells_to_check = [
            (cell_x + dx, cell_y + dy)
            for dx in range(-1, 2)
            for dy in range(-1, 2)
        ]
        for cell in cells_to_check:
            if cell in self.grid:
                for other_obj in self.grid[cell]:
                    if other_obj is not obj and math.dist(obj.get_position(), other_obj.get_position()) <= radius:
                        neighbors.append(other_obj)
        return neighbors
