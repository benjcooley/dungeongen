"""
Crosshatch pattern generator using Skia graphics.

This module provides functionality to generate artistic crosshatch patterns
by drawing strokes in clusters around distributed points.
"""

from typing import List, Tuple, Sequence
import math
import random
import skia

from algorithms.types import Point, Line
from algorithms.shapes import Rectangle
from algorithms.poisson import PoissonDiskSampler
from algorithms.lines import intersect_lines
from options import Options


def draw_background(options: Options, canvas: skia.Canvas) -> None:
    """Fill the background with white."""
    background_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    canvas.drawRect(skia.Rect.MakeWH(options.canvas_width, options.canvas_height), background_paint)

def create_line_paint(options: Options) -> skia.Paint:
    """Create a paint object for drawing lines."""
    return skia.Paint(
        AntiAlias=True,
        StrokeWidth=options.crosshatch_stroke_width,
        Color=skia.ColorBLACK,
        Style=skia.Paint.kStroke_Style,
    )

class _Cluster:
    """A cluster of crosshatch strokes around a central point."""
    
    def __init__(self, origin: Point, options: Options) -> None:
        self._origin = origin
        self._strokes: List[Line] = []
        self._base_angle: float | None = None
        self._options = options

    def add_stroke(self, stroke: Line) -> None:
        """Add a stroke to this cluster."""
        self._strokes.append(stroke)

    def validate_stroke(self, stroke: Line, neighboring_clusters: List['_Cluster']) -> Line | None:
        """Validate and potentially clip a stroke against neighboring clusters."""
        start, end = stroke
        min_t_start = 0
        max_t_end = 1
        found_intersection = False

        # Check intersections and update t values
        for cluster in neighboring_clusters:
            for existing_stroke in cluster._strokes:
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
        if new_length < self._options.min_crosshatch_stroke_length:
            return None

        return (new_start, new_end)


def _get_neighbouring_clusters(cluster: '_Cluster', clusters: List['_Cluster'], radius: float) -> List['_Cluster']:
    """Get clusters within radius distance of the given cluster."""
    return [
        other_cluster for other_cluster in clusters
        if other_cluster is not cluster 
        and math.dist(cluster.origin, other_cluster.origin) <= radius
    ]

def _draw_crosshatch_with_clusters(
    options: Options,
    points: List[Point],
    center_point: Point,
    canvas: skia.Canvas,
    line_paint: skia.Paint
):
    """Draw crosshatch patterns with clusters of strokes."""
    clusters: List[_Cluster] = []

    # Sort points by distance to the center point
    points.sort(key=lambda p: math.dist(p, center_point))

    for point in points:
        px, py = point
        cluster = _Cluster((px, py), options)
        clusters.append(cluster)

        # Generate a base angle for alignment
        base_angle = None
        max_attempts = 20
        neighbours = _get_neighbouring_clusters(cluster, clusters[:-1], options.crosshatch_neighbor_radius)
        
        for _ in range(max_attempts):
            angle_candidate = random.uniform(0, 2 * math.pi)
            if not any(
                abs(math.cos(angle_candidate - neighbor._base_angle)) > 0.9
                for neighbor in neighbours
                if neighbor._base_angle is not None
            ):
                base_angle = angle_candidate
                break

        if base_angle is None:
            base_angle = random.uniform(0, 2 * math.pi)
            for neighbor in neighbours:
                if neighbor._base_angle is not None:
                    base_angle += options.random_angle_variation

        cluster._base_angle = base_angle
        dx_base = math.cos(base_angle)
        dy_base = math.sin(base_angle)

        # Draw parallel lines for the cluster
        for i in range(options.crosshatch_strokes_per_cluster):
            offset = (i - options.crosshatch_strokes_per_cluster // 2) * options.crosshatch_stroke_spacing
            variation = random.uniform(-options.crosshatch_length_variation, options.crosshatch_length_variation) * options.crosshatch_stroke_length
            dx = dx_base * (options.crosshatch_stroke_length / 2 + variation)
            dy = dy_base * (options.crosshatch_stroke_length / 2 + variation)

            start_x = px + offset * dy_base - dx
            start_y = py - offset * dx_base - dy
            end_x = px + offset * dy_base + dx
            end_y = py - offset * dx_base + dy

            new_stroke = ((start_x, start_y), (end_x, end_y))
            clipped_stroke = cluster.validate_stroke(new_stroke, clusters[:-1])

            if clipped_stroke:
                canvas.drawLine(*clipped_stroke[0], *clipped_stroke[1], line_paint)
                cluster.add_stroke(clipped_stroke)

def draw_crosshatches(
    options: Options,
    include_shapes: Sequence[Rectangle],
    exclude_shapes: Sequence[Rectangle],
    canvas: skia.Canvas
) -> None:
    """Draw crosshatch patterns within the given shapes.
    
    Args:
        options: Drawing configuration options
        include_shapes: Shapes to draw crosshatches within
        exclude_shapes: Shapes to exclude crosshatches from
        canvas: The canvas to draw on
    """
    # Initialize paint for lines
    line_paint = create_line_paint(options)
    
    # Set up the sampler
    sampler = PoissonDiskSampler(options.canvas_width, options.canvas_height, 
                                options.crosshatch_poisson_radius)
    
    # Add shapes to sampler
    for shape in include_shapes:
        sampler.add_include_shape(shape)
    for shape in exclude_shapes:
        sampler.add_exclude_shape(shape)
    
    # Sample points
    points = sampler.sample()
    
    # Calculate center point (using first include shape as reference)
    if include_shapes:
        shape = include_shapes[0]
        center_point = (shape.x + shape.width / 2,
                       shape.y + shape.height / 2)
    else:
        center_point = (options.canvas_width / 2, options.canvas_height / 2)
    
    # Draw the crosshatch patterns
    _draw_crosshatch_with_clusters(
        options,
        points,
        center_point,
        canvas,
        line_paint)
