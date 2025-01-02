"""
Crosshatch pattern generator using Skia graphics.

This module provides functionality to generate artistic crosshatch patterns
by drawing strokes in clusters around distributed points.
"""

from typing import List, Tuple
import math
import random
import skia

from algorithms.types import Point, Line
from options import Options

# Initialize Skia canvas
_surface = skia.Surface(400, 400)  # Default size, will be updated when used
_canvas = _surface.getCanvas()

def draw_background(options: Options, canvas: skia.Canvas) -> None:
    """Fill the background with white."""
    background_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRect(skia.Rect.MakeWH(options.width, options.height), background_paint)

def create_line_paint(options: Options) -> skia.Paint:
    """Create a paint object for drawing lines."""
    return skia.Paint(
        AntiAlias=True,
        StrokeWidth=options.stroke_width,
        Color=skia.ColorBLACK,
        Style=skia.Paint.kStroke_Style,
    )
class Cluster:
    """A cluster of crosshatch strokes around a central point."""
    
    def __init__(self, origin: Point) -> None:
        self.origin = origin
        self.strokes: List[Line] = []
        self.base_angle: float | None = None

    def add_stroke(self, stroke: Line) -> None:
        """Add a stroke to this cluster."""
        self.strokes.append(stroke)

    def validate_stroke(self, stroke: Line, neighboring_clusters: List['Cluster']) -> Line | None:
        """Validate and potentially clip a stroke against neighboring clusters."""
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
        if new_length < MIN_STROKE_LENGTH:
            return None

        return (new_start, new_end)

def intersect_lines(line1: Line, line2: Line) -> Tuple[Point, float] | None:
    """Check if lines intersect and return intersection point and t value."""
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

def get_neighbouring_clusters(cluster: Cluster, clusters: List[Cluster], radius: float) -> List[Cluster]:
    """Get clusters within radius distance of the given cluster."""
    return [
        other_cluster for other_cluster in clusters
        if other_cluster is not cluster 
        and math.dist(cluster.origin, other_cluster.origin) <= radius
    ]

def draw_crosshatch_with_clusters(
    options: Options,
    points: List[Point],
    center_point: Point,
    canvas: skia.Canvas,
    line_paint: skia.Paint
) -> None:
    """Draw crosshatch patterns with clusters of strokes."""
    clusters: List[Cluster] = []

    # Sort points by distance to the center point
    points.sort(key=lambda p: math.dist(p, center_point))

    for point in points:
        px, py = point
        cluster = Cluster((px, py))
        clusters.append(cluster)

        # Generate a base angle for alignment
        base_angle = None
        max_attempts = 20
        neighbours = get_neighbouring_clusters(cluster, clusters[:-1], options.neighbor_radius)
        
        for _ in range(max_attempts):
            angle_candidate = random.uniform(0, 2 * math.pi)
            if not any(
                abs(math.cos(angle_candidate - neighbor.base_angle)) > 0.9
                for neighbor in neighbours
                if neighbor.base_angle is not None
            ):
                base_angle = angle_candidate
                break

        if base_angle is None:
            base_angle = random.uniform(0, 2 * math.pi)
            for neighbor in neighbours:
                if neighbor.base_angle is not None:
                    base_angle += options.random_angle_variation

        cluster.base_angle = base_angle
        dx_base = math.cos(base_angle)
        dy_base = math.sin(base_angle)

        # Draw parallel lines for the cluster
        for i in range(options.num_strokes):
            offset = (i - options.num_strokes // 2) * options.spacing
            variation = random.uniform(-options.random_length_variation, options.random_length_variation) * options.stroke_length
            dx = dx_base * (options.stroke_length / 2 + variation)
            dy = dy_base * (options.stroke_length / 2 + variation)

            start_x = px + offset * dy_base - dx
            start_y = py - offset * dx_base - dy
            end_x = px + offset * dy_base + dx
            end_y = py - offset * dx_base + dy

            new_stroke = ((start_x, start_y), (end_x, end_y))
            clipped_stroke = cluster.validate_stroke(new_stroke, clusters[:-1])

            if clipped_stroke:
                canvas.drawLine(*clipped_stroke[0], *clipped_stroke[1], line_paint)
                cluster.add_stroke(clipped_stroke)
