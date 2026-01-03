# Crosshatch System Deep Dive

This document explains how DungeonGen's hand-drawn crosshatch aesthetic is generated.

## Overview

The crosshatch system creates the distinctive "hand-drawn dungeon map" look by filling the area around rooms and passages with clusters of parallel ink strokes. The strokes appear randomly placed but follow rules that prevent overlapping and create natural-looking density variation.

## Architecture

```
crosshatch_tiled.py          # Optimized tiled system (production)
├── generate_hatch_tile()    # Pre-renders a seamless tile
├── draw_crosshatches_tiled()# Stamps tile across shapes
└── HatchTileData            # Cached tile data

crosshatch.py                # Original non-tiled system (reference)
├── draw_crosshatches()      # Direct rendering
└── _Cluster                 # Single cluster of strokes
```

## The Tiled Approach

Rather than generating strokes on-the-fly for each render, the system pre-generates a **seamlessly wrapping tile** that can be stamped across large areas efficiently.

### Why Tiles?

1. **Performance**: Poisson sampling and intersection testing is expensive. Pre-computing once saves time.
2. **Consistency**: Same tile produces identical patterns across renders.
3. **Seams**: Using UV-wrapping, strokes near edges match strokes from the opposite edge.

## Tile Generation Pipeline

### Step 1: Poisson Disk Sampling (Toroidal)

Points are distributed using **Poisson disk sampling** with a minimum distance constraint. This creates an even but random-looking distribution.

```python
def _generate_wrapping_poisson_points(tile_size, min_distance, seed):
    # Uses toroidal distance - points near edges consider 
    # wrapped neighbors from opposite edge
    
    # Seed with multiple starting points for coverage
    for i in range(4):
        for j in range(4):
            # Grid of seed points with jitter
            ...
    
    # Standard dart-throwing with toroidal distance check
    while spawn_points:
        # Pick random point, try to spawn neighbors
        # New points must be min_distance from ALL existing (including wrapped)
        ...
```

**Toroidal distance**: When checking if a candidate point is too close to existing points, we consider all 9 positions (original + 8 wrapped copies). This ensures points near edges don't cluster when tiles are repeated.

### Step 2: Angle Assignment

Each point gets a base angle for its stroke cluster. Adjacent clusters are encouraged to have different angles to create visual variety.

```python
# For each point:
# 1. Find neighbors within crosshatch_neighbor_radius
# 2. Try random angles, reject if too similar to neighbors
# 3. If all attempts fail, use angle + variation

for _ in range(20):  # Try to find unique angle
    angle_candidate = random.uniform(0, 2 * math.pi)
    if not any(
        abs(math.cos(angle_candidate - neighbor_angle)) > 0.9
        for neighbor_angle in neighbors_with_angles
    ):
        base_angle = angle_candidate
        break
```

### Step 3: Stroke Generation

Each point generates a cluster of parallel strokes at its assigned angle.

```python
# For each point:
for i in range(strokes_per_cluster):  # Usually 4-6 strokes
    # Calculate offset perpendicular to base angle
    offset = (i - strokes_per_cluster // 2) * stroke_spacing
    
    # Add length variation
    variation = random.uniform(-length_variation, length_variation)
    
    # Create stroke endpoints
    dx = dx_base * (stroke_length / 2 + variation)
    dy = dy_base * (stroke_length / 2 + variation)
    
    stroke = ((px + offset * dy_base - dx, py - offset * dx_base - dy),
              (px + offset * dy_base + dx, py - offset * dx_base + dy))
```

### Step 4: Intersection Clipping

New strokes are checked against all existing strokes (including wrapped copies). If they intersect, the stroke is clipped to end at the intersection point.

```python
def _validate_stroke_against_mirrored(stroke, all_point_strokes, tile_size):
    # For each existing point's strokes:
    for other_strokes in all_point_strokes:
        # Check all 9 wrapped positions
        for wx in [-tile_size, 0, tile_size]:
            for wy in [-tile_size, 0, tile_size]:
                for existing in other_strokes:
                    mirrored = translate(existing, wx, wy)
                    intersection = intersect_lines(stroke, mirrored)
                    if intersection:
                        # Clip stroke at intersection
                        ...
    
    # Discard if clipped too short
    if new_length < min_stroke_length:
        return None
```

This clipping is what creates the organic "stopping before collision" look.

### Step 5: Grid Bucketing

Points are bucketed into a grid (e.g., 4x4) for fast spatial lookup during rendering.

```python
cell_point_indices: Dict[Tuple[int, int], List[int]]

for i, (px, py) in enumerate(real_points):
    cell_x = int(px / cell_size)
    cell_y = int(py / cell_size)
    cell_point_indices[(cell_x, cell_y)].append(i)
```

## Tile Rendering

When rendering, the pre-computed tile is stamped across the target shape.

### Optimization Layers

1. **Coarse Mask** (1 pixel per cell)
   - Rasterize shape at low resolution
   - Skip cells that are fully outside (coverage = 0)
   - Mark cells as fully inside (coverage = 1) or partial

2. **Cell Processing**
   - For each tile copy overlapping the shape bounds:
     - For each grid cell in the tile:
       - Sample coarse mask to get coverage
       - If fully outside: skip
       - If fully inside: draw all points in cell
       - If partial: check each point against full-res mask

3. **Full-Res Mask** (1:1 pixels)
   - Only created for partial cells
   - Point + endpoints checked against mask

4. **Batched Drawing**
   - All selected lines accumulated into single `skia.Path`
   - One `drawPath()` call for entire shape

```python
def draw_crosshatches_tiled(canvas, shape, tile, options):
    # Create masks
    coarse_mask = rasterize_at_low_res(shape)
    full_mask = rasterize_at_full_res(shape)
    
    path = skia.Path()
    
    # For each tile position covering shape bounds:
    for tile_y in range(min_tile_y, max_tile_y + 1):
        for tile_x in range(min_tile_x, max_tile_x + 1):
            # For each cell in tile:
            for cell_y_idx in range(grid_cells):
                for cell_x_idx in range(grid_cells):
                    coverage = sample_coarse_mask(cell_x, cell_y)
                    
                    if coverage < 0.01:
                        continue  # Skip outside
                    
                    for point_idx in cell_point_indices[(cell_x_idx, cell_y_idx)]:
                        if coverage > 0.99 or point_in_full_mask(point):
                            # Add all strokes for this point
                            for line in tile.point_lines[point_idx]:
                                path.moveTo(...)
                                path.lineTo(...)
    
    canvas.drawPath(path, line_paint)
```

## Configuration Options

Key parameters in `Options`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `crosshatch_poisson_radius` | 60 | Min distance between cluster centers |
| `crosshatch_stroke_length` | 55 | Base length of each stroke |
| `crosshatch_stroke_spacing` | 8 | Distance between parallel strokes |
| `crosshatch_strokes_per_cluster` | 4 | Strokes per cluster |
| `crosshatch_stroke_width` | 1.5 | Line thickness |
| `crosshatch_neighbor_radius` | 90 | Radius for angle neighbor check |
| `crosshatch_angle_variation` | 0.4 | Angle adjustment when avoiding neighbors |
| `crosshatch_length_variation` | 0.2 | Random length variation (±20%) |
| `min_crosshatch_stroke_length` | 10 | Discard strokes shorter than this |
| `crosshatch_border_size` | 24 | How far crosshatch extends beyond room edges |

## Visual Effect

The combination of:
- **Poisson sampling** → Even but random distribution
- **Angle variation** → Organic "hand-drawn" feel
- **Intersection clipping** → Strokes don't overlap
- **Cluster grouping** → Directional patches like real crosshatching

Creates the distinctive "inked dungeon map" aesthetic inspired by watabou's One Page Dungeon.

## Performance

Tile generation: ~50-100ms (once per session)
Tile rendering: ~5-20ms per shape depending on size

The tiled approach is 10-50x faster than regenerating strokes for each render.

