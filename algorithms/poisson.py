"""Poisson disk sampling implementation for point distribution."""

import math
import random
from typing import List, Optional, Sequence
from algorithms.shapes import Point

class PoissonDiskSampler:
    def __init__(self, width, height, min_distance, max_attempts=30):
        self.width = width
        self.height = height
        self.min_distance = min_distance
        self.cell_size = min_distance / math.sqrt(2)
        self.max_attempts = max_attempts

        self.grid_width = int(width / self.cell_size) + 1
        self.grid_height = int(height / self.cell_size) + 1
        self.grid = [[None for _ in range(self.grid_height)] for _ in range(self.grid_width)]
        self.points = []
        self.spawn_points = []
        self.include_shapes = []
        self.exclude_shapes = []

    def add_include_shape(self, shape):
        self.include_shapes.append(shape)
        for x in range(0, self.width, int(self.min_distance)):
            for y in range(0, self.height, int(self.min_distance)):
                if shape.contains(x, y):
                    self.spawn_points.append((x, y))

    def add_exclude_shape(self, shape):
        self.exclude_shapes.append(shape)

    def is_point_valid(self, x, y):
        if self.include_shapes and not any(shape.contains(x, y) for shape in self.include_shapes):
            return False
        if any(shape.contains(x, y) for shape in self.exclude_shapes):
            return False
        return True

    def get_neighbours(self, x, y):
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        neighbours = []
        for gx in range(max(0, grid_x - 2), min(self.grid_width, grid_x + 3)):
            for gy in range(max(0, grid_y - 2), min(self.grid_height, grid_y + 3)):
                if self.grid[gx][gy] is not None:
                    neighbours.append(self.grid[gx][gy])
        return neighbours

    def sample(self):
        while self.spawn_points:
            sp_index = random.randint(0, len(self.spawn_points) - 1)
            spawn_point = self.spawn_points.pop(sp_index)

            for _ in range(self.max_attempts):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(self.min_distance, 2 * self.min_distance)
                candidate_x = spawn_point[0] + math.cos(angle) * radius
                candidate_y = spawn_point[1] + math.sin(angle) * radius

                if 0 <= candidate_x < self.width and 0 <= candidate_y < self.height and self.is_point_valid(candidate_x, candidate_y):
                    grid_x = int(candidate_x / self.cell_size)
                    grid_y = int(candidate_y / self.cell_size)

                    if all(
                        self.grid[gx][gy] is None or
                        math.dist((candidate_x, candidate_y), self.grid[gx][gy]) >= self.min_distance
                        for gx in range(max(0, grid_x - 2), min(self.grid_width, grid_x + 3))
                        for gy in range(max(0, grid_y - 2), min(self.grid_height, grid_y + 3))
                    ):
                        self.points.append((candidate_x, candidate_y))
                        self.spawn_points.append((candidate_x, candidate_y))
                        self.grid[grid_x][grid_y] = (candidate_x, candidate_y)
                        break

        return self.points
