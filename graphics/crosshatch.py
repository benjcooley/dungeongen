"""
Crosshatch pattern generator using Poisson disk sampling and Skia graphics.

This module provides functionality to generate artistic crosshatch patterns
within defined shapes using Poisson disk sampling for point distribution.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Sequence
import math
import random
import skia

# Private module constants
_RANDOM_ANGLE_VARIATION: float = math.radians(10)
_NUM_STROKES: int = 3
_STROKE_WIDTH: float = 1.2
_SPACING: float = 10
_POISSON_RADIUS: float = _SPACING * (_NUM_STROKES - 1)
_NEIGHBOR_RADIUS: float = _POISSON_RADIUS * 1.5
_WIDTH: int = 400
_HEIGHT: int = 400
_STROKE_LENGTH: float = _POISSON_RADIUS * 2
_MIN_STROKE_LENGTH: float = _STROKE_LENGTH * 0.35
_RANDOM_LENGTH_VARIATION: float = 0.1

# Type aliases
Point = Tuple[float, float]
Line = Tuple[Point, Point]

# Initialize Skia canvas
_surface = skia.Surface(_WIDTH, _HEIGHT)
_canvas = _surface.getCanvas()

# Fill the background with white
def draw_background(canvas):
    background_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRect(skia.Rect.MakeWH(_WIDTH, _HEIGHT), background_paint)

def create_line_paint():
    return skia.Paint(
        AntiAlias=True,
        StrokeWidth=_STROKE_WIDTH,
        Color=skia.ColorBLACK,
        Style=skia.Paint.kStroke_Style,
    )

# Shape classes
class Rectangle:
    def __init__(self, x, y, width, height, inflate=0):
        self.x = x - inflate
        self.y = y - inflate
        self.width = width + 2 * inflate
        self.height = height + 2 * inflate
        self.inflate = inflate

    def contains(self, px, py):
        dx = max(0, abs(px - (self.x + self.width / 2)) - self.width / 2)
        dy = max(0, abs(py - (self.y + self.height / 2)) - self.height / 2)
        return math.sqrt(dx ** 2 + dy ** 2) <= self.inflate

class Circle:
    def __init__(self, cx, cy, radius, inflate = 0):
        self.cx = cx
        self.cy = cy
        self.radius = radius + inflate

    def contains(self, px, py):
        return math.sqrt((px - self.cx)**2 + (py - self.cy)**2) <= self.radius

# Poisson Disk Sampling Implementation
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
        self.spawn_points = []  # Dynamically filled
        self.include_shapes = []
        self.exclude_shapes = []

    def add_include_shape(self, shape):
        self.include_shapes.append(shape)
        # Initialize spawn points systematically within include shapes
        for x in range(0, self.width, int(self.min_distance)):
            for y in range(0, self.height, int(self.min_distance)):
                if shape.contains(x, y):
                    self.spawn_points.append((x, y))

    def add_exclude_shape(self, shape):
        self.exclude_shapes.append(shape)

    def is_point_valid(self, x, y):
        # Check if point is inside at least one include shape
        if self.include_shapes and not any(shape.contains(x, y) for shape in self.include_shapes):
            return False

        # Check if point is inside any exclude shape
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

# Test Poisson Disk Sampling with shapes
def test_poisson_sampling():
    sampler = PoissonDiskSampler(_WIDTH, _HEIGHT, _SPACING)

    # Add an include shape (inset rectangle)
    include_shape = Rectangle(50, 50, _WIDTH - 100, _HEIGHT - 100)
    sampler.add_include_shape(include_shape)

    # Add an exclude shape (central rectangle)
    exclude_shape = Rectangle(_WIDTH // 3, _HEIGHT // 3, _WIDTH // 3, _HEIGHT // 3)
    sampler.add_exclude_shape(exclude_shape)

    points = sampler.sample()

    point_paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK, Style=skia.Paint.kFill_Style)
    shape_paint_include = skia.Paint(AntiAlias=True, Color=skia.ColorBLUE, Style=skia.Paint.kStroke_Style, StrokeWidth=1)
    shape_paint_exclude = skia.Paint(AntiAlias=True, Color=skia.ColorRED, Style=skia.Paint.kStroke_Style, StrokeWidth=1)

    # Draw the include shape
    _canvas.drawRect(skia.Rect.MakeLTRB(50, 50, _WIDTH - 50, _HEIGHT - 50), shape_paint_include)
    # Draw the exclude shape
    _canvas.drawRect(skia.Rect.MakeLTRB(_WIDTH // 3, _HEIGHT // 3, _WIDTH * 2 // 3, _HEIGHT * 2 // 3), shape_paint_exclude)

    # Draw the points
    for x, y in points:
        _canvas.drawCircle(x, y, 2, point_paint)

    image = _surface.makeImageSnapshot()
    image.save('poisson_test_output.png', skia.kPNG)
    print("Poisson Disk Sampling test completed and saved to 'poisson_test_output.png'")

# Run test
# test_poisson_sampling()

# Cluster class
class Cluster:
    def __init__(self, origin):
        self.origin = origin
        self.strokes = []
        self.base_angle = None  # Added to store the orientation of the cluster

    def add_stroke(self, stroke):
        self.strokes.append(stroke)

    def validate_stroke(self, stroke, neighboring_clusters):
        start, end = stroke
        min_t_start = 0
        max_t_end = 1
        found_intersection = False

        # Check intersections and update t values
        for cluster in neighboring_clusters:
            for existing_stroke in cluster.strokes:
                intersection = intersect_lines(stroke, existing_stroke)
                if intersection:
                    found_intersection = True
                    _, t = intersection
                    if t < 0.5:
                        min_t_start = max(min_t_start, t)
                    else:
                        max_t_end = min(max_t_end, t)

        # If no intersections, return the original stroke
        if not found_intersection:
            return stroke

        # Calculate new start and end points using the updated t values
        dx, dy = end[0] - start[0], end[1] - start[1]
        new_start = (start[0] + dx * min_t_start, start[1] + dy * min_t_start)
        new_end = (start[0] + dx * max_t_end, start[1] + dy * max_t_end)

        # Ensure the stroke length is not below the minimum
        new_length = math.sqrt((new_end[0] - new_start[0])**2 + (new_end[1] - new_start[1])**2)
        if new_length < _MIN_STROKE_LENGTH:
            return None

        return (new_start, new_end)

# Check if lines intersect and return intersection point and t value
def intersect_lines(line1, line2):
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    dx1, dy1 = x2 - x1, y2 - y1
    dx2, dy2 = x4 - x3, y4 - y3

    determinant = dx1 * dy2 - dy1 * dx2
    if determinant == 0:
        return None  # Parallel lines

    t2 = ((dy1 * (x3 - x1)) - (dx1 * (y3 - y1))) / determinant
    t1 = ((x3 - x1) + dx2 * t2) / dx1 if abs(dx1) > abs(dy1) else ((y3 - y1) + dy2 * t2) / dy1

    if 0 <= t1 <= 1 and 0 <= t2 <= 1:
        intersection_x = x1 + t1 * dx1
        intersection_y = y1 + t1 * dy1
        return ((intersection_x, intersection_y), t1)

    return None

# Helper function to get nearby clusters
def get_neighbouring_clusters(cluster, clusters, radius):
    neighbours = []
    for other_cluster in clusters:
        if other_cluster is not cluster and math.dist(cluster.origin, other_cluster.origin) <= radius:
            neighbours.append(other_cluster)
    return neighbours

# Crosshatch drawing logic with clusters (updated to match JavaScript defaults)
def draw_crosshatch_with_clusters(points, sampler, center_point, canvas, line_paint):
    clusters = []  # List to hold all clusters

    # Sort points by distance to the center point
    points.sort(key=lambda p: math.dist(p, center_point))

    for point in points:
        px, py = point
        cluster = Cluster((px, py))
        clusters.append(cluster)

        # Generate a base angle for alignment
        base_angle = None
        max_attempts = 20  # Increased attempts to find a non-parallel angle
        neighbours = get_neighbouring_clusters(cluster, clusters[:-1], _NEIGHBOR_RADIUS)
        for _ in range(max_attempts):
            angle_candidate = random.uniform(0, 2 * math.pi)
            # Check if this angle is not parallel to nearby clusters
            if not any(
                abs(math.cos(angle_candidate - neighbor.base_angle)) > 0.9
                for neighbor in neighbours
                if neighbor.base_angle is not None
            ):
                base_angle = angle_candidate
                break
        # If no suitable angle found, incrementally adjust the angle
        if base_angle is None:
            base_angle = random.uniform(0, 2 * math.pi)
            for neighbor in neighbours:
                if neighbor.base_angle is not None:
                    base_angle += _RANDOM_ANGLE_VARIATION

        cluster.base_angle = base_angle
        dx_base = math.cos(base_angle)
        dy_base = math.sin(base_angle)

        # Draw parallel lines for the cluster
        for i in range(_NUM_STROKES):
            # Adjust spacing and stroke length dynamically
            offset = (i - _NUM_STROKES // 2) * _SPACING
            variation = random.uniform(-_RANDOM_LENGTH_VARIATION, _RANDOM_LENGTH_VARIATION) * _STROKE_LENGTH
            dx = dx_base * (_STROKE_LENGTH / 2 + variation)
            dy = dy_base * (_STROKE_LENGTH / 2 + variation)

            start_x = px + offset * dy_base - dx
            start_y = py - offset * dx_base - dy
            end_x = px + offset * dy_base + dx
            end_y = py - offset * dx_base + dy

            new_stroke = ((start_x, start_y), (end_x, end_y))
            clipped_stroke = cluster.validate_stroke(new_stroke, clusters[:-1])

            if clipped_stroke:
                canvas.drawLine(*clipped_stroke[0], *clipped_stroke[1], line_paint)
                cluster.add_stroke(clipped_stroke)

# Generate points using Poisson Disk Sampling
sampler = PoissonDiskSampler(_WIDTH, _HEIGHT, _POISSON_RADIUS)

# Add include and exclude shapes
include_shape = Rectangle(100, 100, _WIDTH - 200, _HEIGHT - 200, inflate=40)
sampler.add_include_shape(include_shape)

exclude_shape = Rectangle(_WIDTH // 3, _HEIGHT // 3, _WIDTH // 3, _HEIGHT // 3)
sampler.add_exclude_shape(exclude_shape)

# Sample points
points = sampler.sample()

# Calculate center of the include shape
center_point = (include_shape.x + include_shape.width / 2, include_shape.y + include_shape.height / 2)

# Initialize canvas and paints
draw_background(_canvas)
line_paint = create_line_paint()

# Draw crosshatch patterns with clipping and sorting by distance to the center
draw_crosshatch_with_clusters(points, sampler, center_point, _canvas, line_paint)

# Save to an image
image = _surface.makeImageSnapshot()
image.save('crosshatch_output.png', skia.kPNG)

print("Crosshatch drawing completed and saved to 'crosshatch_output.png'")
