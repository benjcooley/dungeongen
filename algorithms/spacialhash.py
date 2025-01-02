import math

# Grid-based spatial hashing for objs
class SpatialHash:
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.grid = {}

    def _hash(self, x, y):
        return int(x // self.cell_size), int(y // self.cell_size)

    def add(self, obj):
        cx, cy = obj.get_position()
        cell = self._hash(cx, cy)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(obj)

    def get_neighbours(self, obj, radius):
        cx, cy = obj.get_position()
        cell_x, cell_y = self._hash(cx, cy)
        neighbours = []
        cells_to_check = [
            (cell_x + dx, cell_y + dy)
            for dx in range(-1, 2)
            for dy in range(-1, 2)
        ]
        for cell in cells_to_check:
            if cell in self.grid:
                for other_cluster in self.grid[cell]:
                    if other_cluster is not obj and math.dist(obj.get_position(), other_cluster.get_position()) <= radius:
                        neighbours.append(other_cluster)
        return neighbours