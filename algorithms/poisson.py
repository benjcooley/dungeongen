"""Poisson disk sampling implementation for point distribution."""

import math
import random
import skia
from typing import List, Optional, Sequence
from graphics.aliases import Point
from graphics.shapes import Shape
from logging_config import logger, LogTags

class PoissonDiskSampler:
    def __init__(
        self,
        min_distance: float,
        shape: Shape,
        max_attempts: int = 30
    ) -> None:
        """Initialize the Poisson disk sampler.
        
        Args:
            min_distance: Minimum distance between points
            shape: Shape defining valid sampling area
            max_attempts: Maximum sampling attempts per point
        """
        self.min_distance = min_distance
        self.cell_size = min_distance / math.sqrt(2)
        self.max_attempts = max_attempts
        self.shape = shape
        
        # Get bounds from shape
        bounds = shape.bounds
        self.offset_x = bounds.x
        self.offset_y = bounds.y
        self.width = bounds.width
        self.height = bounds.height

        self.grid_width = int(self.width / self.cell_size) + 1
        self.grid_height = int(self.height / self.cell_size) + 1
        self.grid: List[List[Optional[Point]]] = [
            [None for _ in range(self.grid_height)] 
            for _ in range(self.grid_width)
        ]
        self.points: List[Point] = []
        self.spawn_points: List[Point] = []

        # Initialize spawn points within the shape, accounting for offset
        for i in range(0, int(self.width), int(self.min_distance)):
            for j in range(0, int(self.height), int(self.min_distance)):
                x = i + self.offset_x
                y = j + self.offset_y
                if shape.contains(x, y):
                    self.spawn_points.append((x, y))

    def _is_point_valid(self, x: float, y: float) -> bool:
        """Check if a point is valid for sampling.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            
        Returns:
            True if the point is valid for sampling
        """
        return self.shape.contains(x, y)

    def get_neighbors(self, x, y):
        grid_x = int(x / self.cell_size)
        grid_y = int(y / self.cell_size)
        neighbors = []
        for gx in range(max(0, grid_x - 2), min(self.grid_width, grid_x + 3)):
            for gy in range(max(0, grid_y - 2), min(self.grid_height, grid_y + 3)):
                if self.grid[gx][gy] is not None:
                    neighbors.append(self.grid[gx][gy])
        return neighbors


    def sample(self):
        while self.spawn_points:
            sp_index = random.randint(0, len(self.spawn_points) - 1)
            spawn_point = self.spawn_points.pop(sp_index)

            for _ in range(self.max_attempts):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(self.min_distance, 2 * self.min_distance)
                candidate_x = spawn_point[0] + math.cos(angle) * radius
                candidate_y = spawn_point[1] + math.sin(angle) * radius

                # Check if point is within shape bounds
                if (self.offset_x <= candidate_x < self.offset_x + self.width and 
                    self.offset_y <= candidate_y < self.offset_y + self.height and 
                    self._is_point_valid(candidate_x, candidate_y)):
                    # Convert to grid coordinates by subtracting offset
                    grid_x = int((candidate_x - self.offset_x) / self.cell_size)
                    grid_y = int((candidate_y - self.offset_y) / self.cell_size)

                    if all(
                        self.grid[gx][gy] is None or
                        math.dist((candidate_x, candidate_y), self.grid[gx][gy]) >= self.min_distance #type: ignore
                        for gx in range(max(0, grid_x - 2), min(self.grid_width, grid_x + 3))
                        for gy in range(max(0, grid_y - 2), min(self.grid_height, grid_y + 3))
                    ):
                        self.points.append((candidate_x, candidate_y))
                        self.spawn_points.append((candidate_x, candidate_y))
                        self.grid[grid_x][grid_y] = (candidate_x, candidate_y)
                        break

        return self.points
        
    def draw_debug_points(self, canvas: 'skia.Canvas') -> None:
        """Draw debug visualization of sampled points."""
        debug_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=skia.ColorBLUE
        )
        
        for point in self.points:
            canvas.drawCircle(point[0], point[1], 2, debug_paint)

def test_poisson_sampling():
    """Test the Poisson disk sampling implementation."""
    # Create a sampler with test parameters
    width = height = 100
    min_distance = 10
    sampler = PoissonDiskSampler(min_distance, Rectangle)
    
    # Sample points
    points = sampler.sample()
    
    # Verify minimum distance between points
    for i, p1 in enumerate(points):
        for p2 in points[i+1:]:
            distance = math.dist(p1, p2)
            assert distance >= min_distance, f"Points too close: {distance} < {min_distance}"
    
    # Verify points are within bounds
    for x, y in points:
        assert 0 <= x < width, f"X coordinate out of bounds: {x}"
        assert 0 <= y < height, f"Y coordinate out of bounds: {y}"
    
    logger.debug(LogTags.GENERATION, f"Generated {len(points)} points with minimum distance {min_distance}")
    return points
