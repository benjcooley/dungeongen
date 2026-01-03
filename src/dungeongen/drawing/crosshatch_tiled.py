"""
Tiled crosshatch pattern generator using pre-rendered wrapping textures.

This module provides an optimized crosshatch system that pre-generates a 
seamlessly-wrapping hatch tile. The tile can then be stamped repeatedly
over large areas without re-running the expensive poisson sampling and
line intersection calculations.

The hatch-tile uses UV wrapping: points near edges have their hatch lines
computed with "virtual" neighbor points mirrored from the opposite edge,
creating seamless tiling.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
import math
import random

from dungeongen.graphics.aliases import Point, Line
from dungeongen.graphics.lines import intersect_lines
from dungeongen.options import Options


@dataclass
class HatchTileData:
    """Pre-rendered crosshatch tile data for efficient tiled rendering.
    
    Contains all points and their associated hatch lines, bucketed by
    grid cell position for fast spatial lookup.
    
    Attributes:
        tile_size: Size of the tile in world units (width and height are equal)
        grid_cells: Number of grid cells per side (e.g., 3 for a 3x3 tile)
        cell_size: Size of each grid cell in world units
        points: All hatch center points in local tile coordinates [0, tile_size)
        point_lines: Lines for each point (parallel array to points)
        cell_point_indices: Maps (cell_x, cell_y) to list of point indices in that cell
    """
    tile_size: float
    grid_cells: int
    cell_size: float
    points: List[Point] = field(default_factory=list)
    point_lines: List[List[Line]] = field(default_factory=list)
    cell_point_indices: Dict[Tuple[int, int], List[int]] = field(default_factory=dict)
    
    def get_points_in_cell(self, cell_x: int, cell_y: int) -> List[Tuple[int, Point]]:
        """Get all points in a specific grid cell.
        
        Returns:
            List of (point_index, point) tuples for points in this cell
        """
        indices = self.cell_point_indices.get((cell_x, cell_y), [])
        return [(i, self.points[i]) for i in indices]
    
    def get_lines_for_point(self, point_index: int) -> List[Line]:
        """Get the hatch lines for a specific point."""
        return self.point_lines[point_index]


class _TileCluster:
    """A cluster of crosshatch strokes around a central point during tile generation."""
    
    def __init__(self, origin: Point, options: Options, is_virtual: bool = False) -> None:
        """
        Args:
            origin: Center point of this cluster
            options: Drawing options
            is_virtual: True if this is a mirrored/virtual point (outside tile bounds)
        """
        self._origin = origin
        self._strokes: List[Line] = []
        self._base_angle: Optional[float] = None
        self._options = options
        self._is_virtual = is_virtual

    def _add_stroke(self, stroke: Line) -> None:
        """Add a stroke to this cluster."""
        self._strokes.append(stroke)

    def _validate_stroke(self, stroke: Line, neighboring_clusters: List['_TileCluster']) -> Optional[Line]:
        """Validate and potentially clip a stroke against neighboring clusters."""
        start, end = stroke
        min_t_start = 0.0
        max_t_end = 1.0
        found_intersection = False

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

        if not found_intersection:
            return stroke

        dx, dy = end[0] - start[0], end[1] - start[1]
        new_start = (start[0] + dx * min_t_start, start[1] + dy * min_t_start)
        new_end = (start[0] + dx * max_t_end, start[1] + dy * max_t_end)

        new_length = math.sqrt((new_end[0] - new_start[0])**2 + (new_end[1] - new_start[1])**2)
        if new_length < self._options.min_crosshatch_stroke_length:
            return None

        return (new_start, new_end)


def _get_neighboring_clusters(cluster: _TileCluster, clusters: List[_TileCluster], radius: float) -> List[_TileCluster]:
    """Get clusters within radius distance of the given cluster."""
    return [
        other for other in clusters
        if other is not cluster 
        and math.dist(cluster._origin, other._origin) <= radius
    ]


def _toroidal_distance(p1: Point, p2: Point, tile_size: float) -> float:
    """Calculate the shortest distance between two points on a torus (wrapping tile).
    
    This considers all 9 possible wrapped positions and returns the minimum distance.
    """
    min_dist_sq = float('inf')
    x1, y1 = p1
    x2, y2 = p2
    
    for wx in [-tile_size, 0, tile_size]:
        for wy in [-tile_size, 0, tile_size]:
            dx = (x2 + wx) - x1
            dy = (y2 + wy) - y1
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
    
    return math.sqrt(min_dist_sq)


def _generate_wrapping_poisson_points(
    tile_size: float,
    min_distance: float,
    max_attempts: int = 30,
    seed: Optional[int] = None
) -> Tuple[List[Point], List[Point]]:
    """Generate poisson disk points with UV-wrapping at tile edges.
    
    Uses toroidal distance checking so points near opposite edges are properly
    spaced from each other. Then mirrors ALL points into a 3x3 grid for hatch
    line generation.
    
    Args:
        tile_size: Size of the square tile
        min_distance: Minimum distance between points
        max_attempts: Max attempts per spawn point
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (real_points, virtual_points) where:
        - real_points are inside the tile bounds [0, tile_size)
        - virtual_points are ALL points mirrored to surrounding 8 tiles
    """
    if seed is not None:
        random.seed(seed)
    
    cell_size = min_distance / math.sqrt(2)
    grid_dim = int(tile_size / cell_size) + 1
    
    # Use a dict for the grid to handle wrapping more easily
    grid: Dict[Tuple[int, int], Point] = {}
    
    real_points: List[Point] = []
    spawn_points: List[Point] = []
    
    def grid_key(x: float, y: float) -> Tuple[int, int]:
        """Get grid cell key, wrapping around tile boundaries."""
        gx = int((x % tile_size) / cell_size)
        gy = int((y % tile_size) / cell_size)
        return (gx % grid_dim, gy % grid_dim)
    
    def is_valid_point(x: float, y: float) -> bool:
        """Check if point is valid using toroidal distance."""
        # Check against all existing points using toroidal distance
        for existing in real_points:
            if _toroidal_distance((x, y), existing, tile_size) < min_distance:
                return False
        return True
    
    # Seed with multiple starting points spread across the tile for better coverage
    num_seeds = 4
    for i in range(num_seeds):
        for j in range(num_seeds):
            # Offset slightly from grid to avoid patterns
            sx = (i + 0.5) * tile_size / num_seeds + random.uniform(-5, 5)
            sy = (j + 0.5) * tile_size / num_seeds + random.uniform(-5, 5)
            sx = sx % tile_size
            sy = sy % tile_size
            
            if is_valid_point(sx, sy):
                real_points.append((sx, sy))
                spawn_points.append((sx, sy))
                grid[grid_key(sx, sy)] = (sx, sy)
    
    # If no seeds worked, force one in the center
    if not real_points:
        sx, sy = tile_size / 2, tile_size / 2
        real_points.append((sx, sy))
        spawn_points.append((sx, sy))
        grid[grid_key(sx, sy)] = (sx, sy)
    
    # Poisson disk sampling with toroidal distance
    while spawn_points:
        sp_index = random.randint(0, len(spawn_points) - 1)
        spawn_point = spawn_points.pop(sp_index)
        
        for _ in range(max_attempts):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(min_distance, 2 * min_distance)
            candidate_x = spawn_point[0] + math.cos(angle) * radius
            candidate_y = spawn_point[1] + math.sin(angle) * radius
            
            # Wrap into tile bounds
            candidate_x = candidate_x % tile_size
            candidate_y = candidate_y % tile_size
            
            if is_valid_point(candidate_x, candidate_y):
                real_points.append((candidate_x, candidate_y))
                spawn_points.append((candidate_x, candidate_y))
                grid[grid_key(candidate_x, candidate_y)] = (candidate_x, candidate_y)
                break
    
    # Generate virtual points: mirror ALL real points to ALL 8 surrounding tiles
    # This ensures hatch lines at edges are computed with full neighbor context
    virtual_points: List[Point] = []
    
    for px, py in real_points:
        for wx in [-tile_size, 0, tile_size]:
            for wy in [-tile_size, 0, tile_size]:
                if wx == 0 and wy == 0:
                    continue  # Skip the original (it's in real_points)
                virtual_points.append((px + wx, py + wy))
    
    return real_points, virtual_points


def _mirror_line(line: Line, offset_x: float, offset_y: float) -> Line:
    """Translate a line by the given offset."""
    (x1, y1), (x2, y2) = line
    return ((x1 + offset_x, y1 + offset_y), (x2 + offset_x, y2 + offset_y))


def _get_all_mirrored_lines(lines: List[Line], tile_size: float) -> List[Line]:
    """Get all 9 copies of a set of lines (original + 8 mirrored positions)."""
    all_lines = []
    for wx in [-tile_size, 0, tile_size]:
        for wy in [-tile_size, 0, tile_size]:
            for line in lines:
                all_lines.append(_mirror_line(line, wx, wy))
    return all_lines


def _validate_stroke_against_mirrored(
    stroke: Line,
    point_origin: Point,
    all_point_strokes: List[List[Line]],
    all_points: List[Point],
    current_point_idx: int,
    tile_size: float,
    options: Options
) -> Optional[Line]:
    """Validate and clip a stroke against all mirrored copies of all other strokes.
    
    For proper tiling, each stroke must be checked against:
    - All strokes from all other points (at all 9 mirrored positions)
    - All strokes from the current point's other mirrored copies (8 positions)
    """
    start, end = stroke
    min_t_start = 0.0
    max_t_end = 1.0
    found_intersection = False
    
    # Check against all other points' strokes (mirrored to all 9 positions)
    for other_idx, other_strokes in enumerate(all_point_strokes):
        if other_idx == current_point_idx:
            # For our own point, check against mirrored copies (not the original)
            for wx in [-tile_size, 0, tile_size]:
                for wy in [-tile_size, 0, tile_size]:
                    if wx == 0 and wy == 0:
                        continue  # Skip self
                    for other_stroke in other_strokes:
                        mirrored = _mirror_line(other_stroke, wx, wy)
                        intersection = intersect_lines(stroke, mirrored)
                        if intersection:
                            found_intersection = True
                            _, t = intersection
                            if t < 0.5:
                                min_t_start = max(min_t_start, t)
                            else:
                                max_t_end = min(max_t_end, t)
        else:
            # For other points, check all 9 mirrored positions
            for wx in [-tile_size, 0, tile_size]:
                for wy in [-tile_size, 0, tile_size]:
                    for other_stroke in other_strokes:
                        mirrored = _mirror_line(other_stroke, wx, wy)
                        intersection = intersect_lines(stroke, mirrored)
                        if intersection:
                            found_intersection = True
                            _, t = intersection
                            if t < 0.5:
                                min_t_start = max(min_t_start, t)
                            else:
                                max_t_end = min(max_t_end, t)
    
    if not found_intersection:
        return stroke
    
    dx, dy = end[0] - start[0], end[1] - start[1]
    new_start = (start[0] + dx * min_t_start, start[1] + dy * min_t_start)
    new_end = (start[0] + dx * max_t_end, start[1] + dy * max_t_end)
    
    new_length = math.sqrt((new_end[0] - new_start[0])**2 + (new_end[1] - new_start[1])**2)
    if new_length < options.min_crosshatch_stroke_length:
        return None
    
    return (new_start, new_end)


def _generate_hatch_lines_for_tile(
    options: Options,
    real_points: List[Point],
    virtual_points: List[Point],  # Not used anymore, kept for API compatibility
    tile_size: float,
    seed: Optional[int] = None
) -> List[List[Line]]:
    """Generate crosshatch lines for center tile points with proper wrapping.
    
    Lines are generated only for real (center tile) points, but intersections
    are checked against all 9 mirrored copies of all lines. This ensures
    strokes at tile edges are clipped identically to their wrapped counterparts.
    
    Args:
        options: Drawing options
        real_points: Points inside tile bounds
        virtual_points: (Unused - kept for API compatibility)
        tile_size: Size of the tile
        seed: Random seed
        
    Returns:
        List of line lists, one per real point (parallel to real_points)
    """
    if seed is not None:
        random.seed(seed)
    
    # First pass: determine base angles for each point
    # Use toroidal neighbor checking
    point_angles: List[float] = []
    
    for i, (px, py) in enumerate(real_points):
        # Find neighbors using toroidal distance
        neighbors_with_angles = []
        for j, (ox, oy) in enumerate(real_points):
            if j < i:  # Only consider already-processed points
                dist = _toroidal_distance((px, py), (ox, oy), tile_size)
                if dist <= options.crosshatch_neighbor_radius:
                    neighbors_with_angles.append(point_angles[j])
        
        # Find base angle avoiding neighbors
        base_angle = None
        for _ in range(20):
            angle_candidate = random.uniform(0, 2 * math.pi)
            if not any(
                abs(math.cos(angle_candidate - neighbor_angle)) > 0.9
                for neighbor_angle in neighbors_with_angles
            ):
                base_angle = angle_candidate
                break
        
        if base_angle is None:
            base_angle = random.uniform(0, 2 * math.pi)
            for neighbor_angle in neighbors_with_angles:
                base_angle += options.crosshatch_angle_variation
        
        point_angles.append(base_angle)
    
    # Second pass: generate strokes for each point
    # We need to do this iteratively so each point can check against previous points' strokes
    all_point_strokes: List[List[Line]] = [[] for _ in real_points]
    
    # Sort points by distance to center for consistent processing
    tile_center = (tile_size / 2, tile_size / 2)
    process_order = sorted(range(len(real_points)),
                          key=lambda i: _toroidal_distance(real_points[i], tile_center, tile_size))
    
    for point_idx in process_order:
        px, py = real_points[point_idx]
        base_angle = point_angles[point_idx]
        dx_base = math.cos(base_angle)
        dy_base = math.sin(base_angle)
        
        # Generate strokes for this point
        for i in range(options.crosshatch_strokes_per_cluster):
            offset = (i - options.crosshatch_strokes_per_cluster // 2) * options.crosshatch_stroke_spacing
            variation = random.uniform(
                -options.crosshatch_length_variation,
                options.crosshatch_length_variation
            ) * options.crosshatch_stroke_length
            
            dx = dx_base * (options.crosshatch_stroke_length / 2 + variation)
            dy = dy_base * (options.crosshatch_stroke_length / 2 + variation)
            
            start_x = px + offset * dy_base - dx
            start_y = py - offset * dx_base - dy
            end_x = px + offset * dy_base + dx
            end_y = py - offset * dx_base + dy
            
            new_stroke: Line = ((start_x, start_y), (end_x, end_y))
            
            # Validate against all mirrored copies of all strokes
            clipped_stroke = _validate_stroke_against_mirrored(
                new_stroke,
                (px, py),
                all_point_strokes,
                real_points,
                point_idx,
                tile_size,
                options
            )
            
            if clipped_stroke:
                all_point_strokes[point_idx].append(clipped_stroke)
    
    return all_point_strokes


def generate_hatch_tile(
    options: Options,
    grid_cells: int = 3,
    seed: Optional[int] = None
) -> HatchTileData:
    """Generate a pre-rendered crosshatch tile for efficient tiled rendering.
    
    Creates a seamlessly-wrapping hatch tile with points and lines bucketed
    by grid cell for fast spatial lookup during rendering.
    
    Args:
        options: Drawing options (controls stroke spacing, count, etc.)
        grid_cells: Number of grid cells per side (default 3 for 3x3 tile)
        seed: Random seed for reproducibility
        
    Returns:
        HatchTileData containing all points and lines, bucketed by grid cell
    """
    # Calculate tile size based on crosshatch parameters
    # Use poisson radius as the base unit
    cell_size = options.crosshatch_poisson_radius * 2  # Each cell should fit ~1-2 clusters
    tile_size = cell_size * grid_cells
    
    # Generate wrapping poisson points
    real_points, virtual_points = _generate_wrapping_poisson_points(
        tile_size=tile_size,
        min_distance=options.crosshatch_poisson_radius,
        seed=seed
    )
    
    # Generate hatch lines
    point_lines = _generate_hatch_lines_for_tile(
        options=options,
        real_points=real_points,
        virtual_points=virtual_points,
        tile_size=tile_size,
        seed=seed
    )
    
    # Bucket points by grid cell
    cell_point_indices: Dict[Tuple[int, int], List[int]] = {}
    for i, (px, py) in enumerate(real_points):
        cell_x = min(int(px / cell_size), grid_cells - 1)
        cell_y = min(int(py / cell_size), grid_cells - 1)
        key = (cell_x, cell_y)
        if key not in cell_point_indices:
            cell_point_indices[key] = []
        cell_point_indices[key].append(i)
    
    return HatchTileData(
        tile_size=tile_size,
        grid_cells=grid_cells,
        cell_size=cell_size,
        points=real_points,
        point_lines=point_lines,
        cell_point_indices=cell_point_indices
    )


def draw_crosshatches_tiled(
    canvas: 'skia.Canvas',
    shape: 'Shape',
    tile: HatchTileData,
    options: Options,
    line_paint: Optional['skia.Paint'] = None,
    debug_points: bool = False
) -> None:
    """Draw crosshatch pattern over a shape using pre-rendered tile data.
    
    This is the optimized replacement for draw_crosshatches(). Instead of
    generating poisson points and computing intersections at render time,
    it tiles a pre-computed hatch pattern over the shape.
    
    Optimization levels:
    1. Coarse mask (1px/cell) - skip cells fully outside shape
    2. Coverage detection - cells fully inside skip point checks
    3. Full-res mask - precise point selection for edge cells
    4. Batched drawing - all lines drawn in single path
    
    Args:
        canvas: Skia canvas to draw on
        shape: Shape defining the crosshatch area
        tile: Pre-rendered hatch tile data
        options: Drawing options
        line_paint: Optional custom paint (defaults to black strokes)
    """
    import skia
    
    # Default paint if not provided
    if line_paint is None:
        line_paint = skia.Paint(
            AntiAlias=True,
            StrokeWidth=options.crosshatch_stroke_width,
            Color=skia.ColorBLACK,
            Style=skia.Paint.kStroke_Style,
        )
    
    # Get shape bounds
    bounds = shape.bounds
    
    # Expand bounds to tile-aligned coordinates
    tile_size = tile.tile_size
    cell_size = tile.cell_size
    grid_cells = tile.grid_cells
    
    # Calculate tile range that covers the shape bounds
    min_tile_x = int(math.floor(bounds.x / tile_size))
    min_tile_y = int(math.floor(bounds.y / tile_size))
    max_tile_x = int(math.ceil((bounds.x + bounds.width) / tile_size))
    max_tile_y = int(math.ceil((bounds.y + bounds.height) / tile_size))
    
    # Create coarse mask (1 pixel per cell)
    # This tells us: 0=outside, 255=fully inside, gray=partial
    # IMPORTANT: Align offset to cell_size grid so mask pixels align with tile cells
    coarse_offset_x = math.floor((bounds.x - cell_size) / cell_size) * cell_size
    coarse_offset_y = math.floor((bounds.y - cell_size) / cell_size) * cell_size
    coarse_width = int(math.ceil((bounds.x + bounds.width - coarse_offset_x) / cell_size)) + 1
    coarse_height = int(math.ceil((bounds.y + bounds.height - coarse_offset_y) / cell_size)) + 1
    
    # Rasterize shape to coarse mask
    # Use explicit matrix to avoid transform order confusion
    # We want: pixel = (world - offset) / cell_size
    coarse_surface = skia.Surface(coarse_width, coarse_height)
    coarse_canvas = coarse_surface.getCanvas()
    coarse_canvas.clear(skia.ColorBLACK)
    
    
    # Build explicit matrix: pixel = (world - offset) / cell_size
    # Matrix form: [1/cell_size, 0, -offset_x/cell_size]
    #              [0, 1/cell_size, -offset_y/cell_size]
    transform = skia.Matrix()
    transform.setScale(1.0 / cell_size, 1.0 / cell_size)
    transform.preTranslate(-coarse_offset_x, -coarse_offset_y)
    
    coarse_canvas.save()
    coarse_canvas.concat(transform)
    
    # Draw shape with white fill - anti-aliasing will create gray edge pixels
    fill_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kFill_Style,
        Color=skia.ColorWHITE,
    )
    shape.draw(coarse_canvas, fill_paint)
    coarse_canvas.restore()
    
    # Get coarse mask pixels as numpy array for fast access
    coarse_image = coarse_surface.makeImageSnapshot()
    coarse_array = coarse_image.toarray()  # Shape: (height, width, 4) RGBA
    
    
    # Create full-res mask for precise point checking (only for partial cells)
    full_width = int(bounds.width) + 2
    full_height = int(bounds.height) + 2
    full_surface = skia.Surface(full_width, full_height)
    full_canvas = full_surface.getCanvas()
    full_canvas.clear(skia.ColorBLACK)
    full_canvas.save()
    full_canvas.translate(-bounds.x + 1, -bounds.y + 1)
    shape.draw(full_canvas, fill_paint)
    full_canvas.restore()
    full_image = full_surface.makeImageSnapshot()
    full_array = full_image.toarray()  # Shape: (height, width, 4) RGBA
    
    # Collect all lines to draw into a single path for batched rendering
    path = skia.Path()
    
    # Debug: collect points for visualization
    debug_selected_points: List[Point] = [] if debug_points else None
    debug_rejected_points: List[Point] = [] if debug_points else None
    
    # Iterate through all tile positions that might overlap
    for tile_y in range(min_tile_y, max_tile_y + 1):
        for tile_x in range(min_tile_x, max_tile_x + 1):
            tile_origin_x = tile_x * tile_size
            tile_origin_y = tile_y * tile_size
            
            # Quick AABB check - does this tile overlap shape bounds at all?
            if (tile_origin_x + tile_size < bounds.x or 
                tile_origin_x > bounds.x + bounds.width or
                tile_origin_y + tile_size < bounds.y or 
                tile_origin_y > bounds.y + bounds.height):
                continue
            
            # Check each cell in the tile
            for cell_y_idx in range(grid_cells):
                for cell_x_idx in range(grid_cells):
                    # World coordinates of this cell
                    cell_world_x = tile_origin_x + cell_x_idx * cell_size
                    cell_world_y = tile_origin_y + cell_y_idx * cell_size
                    
                    # Map to coarse mask coordinates
                    coarse_x = int((cell_world_x - coarse_offset_x) / cell_size)
                    coarse_y = int((cell_world_y - coarse_offset_y) / cell_size)
                    
                    # Bounds check for coarse mask
                    if coarse_x < 0 or coarse_x >= coarse_width or coarse_y < 0 or coarse_y >= coarse_height:
                        continue
                    
                    # Sample coarse mask to get coverage (R channel, 0-255)
                    coverage = coarse_array[coarse_y, coarse_x, 0] / 255.0  # 0.0 to 1.0
                    
                    if coverage < 0.01:
                        # Fully outside - skip cell entirely
                        continue
                    
                    # Get points in this cell
                    cell_key = (cell_x_idx, cell_y_idx)
                    point_indices = tile.cell_point_indices.get(cell_key, [])
                    if not point_indices:
                        continue
                    
                    fully_inside = coverage > 0.99
                    
                    # Process points in this cell
                    for point_idx in point_indices:
                        point = tile.points[point_idx]
                        world_point_x = tile_origin_x + point[0]
                        world_point_y = tile_origin_y + point[1]
                        
                        # Check if point is inside shape
                        if fully_inside:
                            # Cell fully inside - no need to check
                            point_inside = True
                        else:
                            # Partial cell - sample full-res mask at point and 4 neighbors
                            # Use half stroke length as offset to catch edge points whose lines reach inside
                            point_inside = False
                            sample_offset = options.crosshatch_stroke_length / 2
                            for dx, dy in [(0, 0), (-sample_offset, 0), (sample_offset, 0), 
                                           (0, -sample_offset), (0, sample_offset)]:
                                mask_x = int(world_point_x - bounds.x + 1 + dx)
                                mask_y = int(world_point_y - bounds.y + 1 + dy)
                                if 0 <= mask_x < full_width and 0 <= mask_y < full_height:
                                    pixel_value = full_array[mask_y, mask_x, 0] / 255.0
                                    if pixel_value > 0.5:
                                        point_inside = True
                                        break
                        
                        if point_inside:
                            # Add all lines for this point to the path
                            for line in tile.point_lines[point_idx]:
                                (x1, y1), (x2, y2) = line
                                path.moveTo(tile_origin_x + x1, tile_origin_y + y1)
                                path.lineTo(tile_origin_x + x2, tile_origin_y + y2)
                            if debug_selected_points is not None:
                                debug_selected_points.append((world_point_x, world_point_y))
                        else:
                            if debug_rejected_points is not None:
                                debug_rejected_points.append((world_point_x, world_point_y))
    
    # Draw all lines in a single call
    canvas.drawPath(path, line_paint)
    
    # Debug: draw selected/rejected points
    if debug_points and debug_selected_points is not None:
        selected_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=skia.Color(0, 200, 0),  # Green = selected
        )
        rejected_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=skia.Color(255, 0, 0),  # Red = rejected
        )
        for px, py in debug_selected_points:
            canvas.drawCircle(px, py, 4, selected_paint)
        for px, py in debug_rejected_points:
            canvas.drawCircle(px, py, 4, rejected_paint)


def get_tile_stats(tile: HatchTileData) -> Dict[str, any]:
    """Get statistics about a hatch tile for debugging."""
    total_lines = sum(len(lines) for lines in tile.point_lines)
    points_per_cell = {k: len(v) for k, v in tile.cell_point_indices.items()}
    
    return {
        'tile_size': tile.tile_size,
        'grid_cells': tile.grid_cells,
        'cell_size': tile.cell_size,
        'total_points': len(tile.points),
        'total_lines': total_lines,
        'avg_lines_per_point': total_lines / len(tile.points) if tile.points else 0,
        'points_per_cell': points_per_cell,
    }


# For testing the module directly
if __name__ == "__main__":
    import skia
    
    opts = Options()
    
    # Generate tile - seed 4242 selected for good even distribution
    # Alternative seeds (all produce good results):
    # - 1001: Good density, varied angles
    # - 2023: Most coverage, some longer strokes  
    # - 7777: Dense coverage, good variation
    test_seeds = [4242]  # [1001, 2023, 4242, 7777]
    
    for seed in test_seeds:
        print(f"\nGenerating hatch tile with seed {seed}...")
        tile = generate_hatch_tile(opts, grid_cells=4, seed=seed)
        
        stats = get_tile_stats(tile)
        print(f"Tile stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        
        # Render a test image showing:
        # - Single tile in lower-left for clarity
        # - 3x3 tiled version in upper-right to verify wrapping
        tiles_shown = 3
        single_tile_margin = 20
        canvas_size = int(tile.tile_size * tiles_shown + tile.tile_size + single_tile_margin * 3)
        surface = skia.Surface(canvas_size, canvas_size)
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        
        line_paint = skia.Paint(
            AntiAlias=True,
            StrokeWidth=opts.crosshatch_stroke_width,
            Color=skia.ColorBLACK,
            Style=skia.Paint.kStroke_Style,
        )
        
        point_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=skia.ColorRED,
        )
        
        # Semi-transparent colors for grid cells (buckets)
        cell_colors = [
            skia.Color4f(1.0, 0.0, 0.0, 0.1),  # Red
            skia.Color4f(0.0, 1.0, 0.0, 0.1),  # Green
            skia.Color4f(0.0, 0.0, 1.0, 0.1),  # Blue
            skia.Color4f(1.0, 1.0, 0.0, 0.1),  # Yellow
            skia.Color4f(1.0, 0.0, 1.0, 0.1),  # Magenta
            skia.Color4f(0.0, 1.0, 1.0, 0.1),  # Cyan
            skia.Color4f(1.0, 0.5, 0.0, 0.1),  # Orange
            skia.Color4f(0.5, 0.0, 1.0, 0.1),  # Purple
            skia.Color4f(0.0, 0.5, 0.5, 0.1),  # Teal
        ]
        
        # Tile boundary colors (more visible)
        tile_boundary_colors = [
            skia.Color(255, 100, 100),  # Light red
            skia.Color(100, 255, 100),  # Light green
            skia.Color(100, 100, 255),  # Light blue
            skia.Color(255, 255, 100),  # Light yellow
        ]
        
        # Helper function to draw a single tile instance
        def draw_tile_instance(offset_x: float, offset_y: float, tile_color_idx: int, show_cells: bool = True):
            # Draw semi-transparent grid cell backgrounds (buckets)
            if show_cells:
                for cx in range(tile.grid_cells):
                    for cy in range(tile.grid_cells):
                        cell_idx = cy * tile.grid_cells + cx
                        cell_paint = skia.Paint(
                            AntiAlias=True,
                            Style=skia.Paint.kFill_Style,
                            Color4f=cell_colors[cell_idx % len(cell_colors)],
                        )
                        cell_x = offset_x + cx * tile.cell_size
                        cell_y = offset_y + cy * tile.cell_size
                        canvas.drawRect(
                            skia.Rect(cell_x, cell_y, 
                                      cell_x + tile.cell_size, 
                                      cell_y + tile.cell_size),
                            cell_paint
                        )
            
            # Draw hatch lines
            for point_idx, lines in enumerate(tile.point_lines):
                for (x1, y1), (x2, y2) in lines:
                    canvas.drawLine(
                        x1 + offset_x, y1 + offset_y,
                        x2 + offset_x, y2 + offset_y,
                        line_paint
                    )
            
            # Draw points
            for px, py in tile.points:
                canvas.drawCircle(px + offset_x, py + offset_y, 3, point_paint)
            
            # Draw tile boundary (thick colored line)
            tile_border_paint = skia.Paint(
                AntiAlias=True,
                StrokeWidth=3,
                Color=tile_boundary_colors[tile_color_idx % len(tile_boundary_colors)],
                Style=skia.Paint.kStroke_Style,
            )
            canvas.drawRect(
                skia.Rect(offset_x + 1, offset_y + 1, 
                          offset_x + tile.tile_size - 1, 
                          offset_y + tile.tile_size - 1),
                tile_border_paint
            )
            
            # Draw grid cell boundaries (thin lines)
            if show_cells:
                cell_boundary_paint = skia.Paint(
                    AntiAlias=True,
                    StrokeWidth=1,
                    Color=skia.Color(180, 180, 180),
                    Style=skia.Paint.kStroke_Style,
                )
                for cx in range(1, tile.grid_cells):
                    x = offset_x + cx * tile.cell_size
                    canvas.drawLine(x, offset_y, x, offset_y + tile.tile_size, cell_boundary_paint)
                for cy in range(1, tile.grid_cells):
                    y = offset_y + cy * tile.cell_size
                    canvas.drawLine(offset_x, y, offset_x + tile.tile_size, y, cell_boundary_paint)
        
        # Draw single tile in lower-left
        single_x = single_tile_margin
        single_y = canvas_size - tile.tile_size - single_tile_margin
        draw_tile_instance(single_x, single_y, 0, show_cells=True)
        
        # Label for single tile
        label_paint = skia.Paint(
            AntiAlias=True,
            Color=skia.ColorBLACK,
        )
        font = skia.Font(None, 14)
        canvas.drawString(f"Single Tile (4x4 buckets) - seed {seed}", single_x, single_y - 5, font, label_paint)
        
        # Draw 3x3 tiled version in upper-right
        tiled_base_x = tile.tile_size + single_tile_margin * 2
        tiled_base_y = single_tile_margin
        
        for tx in range(tiles_shown):
            for ty in range(tiles_shown):
                offset_x = tiled_base_x + tx * tile.tile_size
                offset_y = tiled_base_y + ty * tile.tile_size
                tile_idx = (ty * tiles_shown + tx)
                draw_tile_instance(offset_x, offset_y, tile_idx, show_cells=True)
        
        # Label for tiled version
        canvas.drawString("3x3 Tiled (verifies wrapping)", tiled_base_x, tiled_base_y - 5, font, label_paint)
        
        # Save test image
        image = surface.makeImageSnapshot()
        output_path = f'/Users/benjamincooley/projects/dungeongen/hatch_tile_seed_{seed}.png'
        image.save(output_path, skia.kPNG)
        print(f"Saved test image to {output_path}")
    
    print(f"\nGenerated {len(test_seeds)} tile preview images")
    
    # Test the actual tiled drawing function with various shapes
    print("\nTesting tiled crosshatch drawing with various shapes...")
    from dungeongen.graphics.shapes import Rectangle, Circle, ShapeGroup
    import time
    
    # Generate tile with the chosen seed
    tile = generate_hatch_tile(opts, grid_cells=4, seed=4242)
    
    line_paint = skia.Paint(
        AntiAlias=True,
        StrokeWidth=opts.crosshatch_stroke_width,
        Color=skia.ColorBLACK,
        Style=skia.Paint.kStroke_Style,
    )
    
    outline_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kStroke_Style,
        Color=skia.Color(150, 150, 150),
        StrokeWidth=2,
    )
    
    fill_paint = skia.Paint(
        AntiAlias=True,
        Style=skia.Paint.kFill_Style,
        Color=skia.Color(230, 230, 235),
    )
    
    # Test 1: Simple rectangle (with debug points)
    print("\n1. Rectangle test (debug)...")
    test_shape = Rectangle(50, 50, 400, 300)
    test_surface = skia.Surface(500, 400)
    test_canvas = test_surface.getCanvas()
    test_canvas.clear(skia.ColorWHITE)
    test_canvas.drawRect(skia.Rect(50, 50, 450, 350), fill_paint)
    test_canvas.drawRect(skia.Rect(50, 50, 450, 350), outline_paint)
    
    start = time.perf_counter()
    draw_crosshatches_tiled(test_canvas, test_shape, tile, opts, line_paint, debug_points=True)
    elapsed = time.perf_counter() - start
    print(f"   Rectangle: {elapsed*1000:.2f}ms")
    
    test_surface.makeImageSnapshot().save('/Users/benjamincooley/projects/dungeongen/hatch_test_rectangle.png', skia.kPNG)
    
    # Test 2: Circle
    print("2. Circle test...")
    test_shape = Circle(250, 200, 150)
    test_surface = skia.Surface(500, 400)
    test_canvas = test_surface.getCanvas()
    test_canvas.clear(skia.ColorWHITE)
    test_canvas.drawCircle(250, 200, 150, fill_paint)
    test_canvas.drawCircle(250, 200, 150, outline_paint)
    
    start = time.perf_counter()
    draw_crosshatches_tiled(test_canvas, test_shape, tile, opts, line_paint)
    elapsed = time.perf_counter() - start
    print(f"   Circle: {elapsed*1000:.2f}ms")
    
    test_surface.makeImageSnapshot().save('/Users/benjamincooley/projects/dungeongen/hatch_test_circle.png', skia.kPNG)
    
    # Test 3: L-shaped region (two rectangles combined)
    print("3. L-shape test...")
    rect1 = Rectangle(50, 50, 150, 300)
    rect2 = Rectangle(50, 250, 350, 100)
    test_shape = ShapeGroup.combine([rect1, rect2])
    test_surface = skia.Surface(500, 400)
    test_canvas = test_surface.getCanvas()
    test_canvas.clear(skia.ColorWHITE)
    test_shape.draw(test_canvas, fill_paint)
    test_shape.draw(test_canvas, outline_paint)
    
    start = time.perf_counter()
    draw_crosshatches_tiled(test_canvas, test_shape, tile, opts, line_paint)
    elapsed = time.perf_counter() - start
    print(f"   L-shape: {elapsed*1000:.2f}ms")
    
    test_surface.makeImageSnapshot().save('/Users/benjamincooley/projects/dungeongen/hatch_test_lshape.png', skia.kPNG)
    
    # Test 4: Multiple rooms (simulating dungeon layout)
    print("4. Multi-room test...")
    rooms = [
        Rectangle(50, 50, 120, 100),
        Rectangle(220, 50, 100, 150),
        Rectangle(370, 100, 80, 100),
        Rectangle(100, 200, 150, 120),
        Rectangle(300, 250, 120, 100),
    ]
    # Inflate each room slightly to create the crosshatch border effect
    inflated = [r.inflated(25) for r in rooms]
    test_shape = ShapeGroup.combine(inflated)
    
    test_surface = skia.Surface(500, 400)
    test_canvas = test_surface.getCanvas()
    test_canvas.clear(skia.ColorWHITE)
    
    # Draw inflated region (gray background)
    test_shape.draw(test_canvas, fill_paint)
    
    # Draw crosshatch on the inflated region
    start = time.perf_counter()
    draw_crosshatches_tiled(test_canvas, test_shape, tile, opts, line_paint)
    elapsed = time.perf_counter() - start
    print(f"   Multi-room: {elapsed*1000:.2f}ms")
    
    # Draw room interiors (white, on top of crosshatch)
    room_fill = skia.Paint(AntiAlias=True, Style=skia.Paint.kFill_Style, Color=skia.ColorWHITE)
    room_stroke = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, Color=skia.ColorBLACK, StrokeWidth=2)
    for room in rooms:
        room.draw(test_canvas, room_fill)
        room.draw(test_canvas, room_stroke)
    
    test_surface.makeImageSnapshot().save('/Users/benjamincooley/projects/dungeongen/hatch_test_multiroom.png', skia.kPNG)
    
    # Test 5: Large area stress test
    print("5. Large area stress test...")
    test_shape = Rectangle(20, 20, 760, 560)
    test_surface = skia.Surface(800, 600)
    test_canvas = test_surface.getCanvas()
    test_canvas.clear(skia.ColorWHITE)
    test_canvas.drawRect(skia.Rect(20, 20, 780, 580), fill_paint)
    
    start = time.perf_counter()
    draw_crosshatches_tiled(test_canvas, test_shape, tile, opts, line_paint)
    elapsed = time.perf_counter() - start
    print(f"   Large area (760x560): {elapsed*1000:.2f}ms")
    
    test_surface.makeImageSnapshot().save('/Users/benjamincooley/projects/dungeongen/hatch_test_large.png', skia.kPNG)
    
    print("\nAll test images saved!")

