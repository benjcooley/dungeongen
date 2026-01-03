# Water System Deep Dive

This document explains how DungeonGen generates and renders procedural water features.

## Overview

The water system creates flooded areas, pools, and puddles within dungeon rooms using a **noise-based field generation** approach. Water regions are extracted as contours, smoothed, and rendered with shoreline and ripple effects.

## Architecture

```
water_layer.py               # Field generation and contour extraction
├── WaterLayer               # Main generation class
├── WaterShape               # Output: outer contour + islands
├── WaterFieldParams         # Configuration
└── WaterDepth               # Preset depth levels

water.py                     # Rendering (Skia and SVG)
├── render_water()           # Draw contours to canvas
├── render_water_shapes()    # Draw WaterShapes
├── WaterStyle               # Visual configuration
└── offset_polygon()         # Inset for ripple lines
```

## Water Depth Presets

Water coverage is controlled by a threshold parameter:

```python
class WaterDepth:
    DRY = 0.0        # No water
    PUDDLES = 0.75   # ~30-40% coverage
    POOLS = 0.60     # ~50-60% coverage  
    LAKES = 0.45     # ~70-80% coverage
    FLOODED = 0.30   # ~85-95% coverage
```

Higher threshold = less water (more selective about what counts as "deep enough").

## Field Generation Pipeline

Water regions are generated in 5 steps at **reduced resolution** for performance.

### Step 1: Gaussian Basins

Large-scale depth variation from randomly placed "basins":

```python
def gaussian_basins(width, height, seed, num_basins, sigma_range):
    field = np.zeros((height, width))
    rng = np.random.default_rng(seed)
    
    for _ in range(num_basins):
        # Random center and radius
        cx = rng.uniform(0, width)
        cy = rng.uniform(0, height)
        sigma = rng.uniform(sigma_range[0], sigma_range[1])
        
        # Create Gaussian blob
        for y in range(height):
            for x in range(width):
                dist_sq = (x - cx)**2 + (y - cy)**2
                field[y, x] += math.exp(-dist_sq / (2 * sigma**2))
    
    return normalize(field)  # Scale to 0-1
```

This creates broad, smooth depth variations - some areas naturally deeper than others.

### Step 2: Low-Frequency fBM Noise

Add organic detail using **fractional Brownian motion** (fBM):

```python
# Sample Perlin noise at low frequency
perlin = Perlin2D(seed)
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
x = xx * lf_scale  # lf_scale ≈ 0.018 for grid-scale blobs
y = yy * lf_scale

lf = fbm(perlin, x, y, octaves=3, gain=0.55)
lf = box_blur(lf, radius=2, passes=1)  # Smooth
lf = normalize(lf)
```

fBM combines multiple octaves of Perlin noise to create natural-looking variation:
- Low frequencies: large-scale shape
- High frequencies: fine detail (reduced by `gain < 1`)

### Step 3: Mix and Post-Process

Combine basins and noise:

```python
# Weighted mix (basins dominate for broad structure)
field = normalize(
    basins * 0.60 + lf * 0.40
)

# Smooth edges
field = box_blur(field, radius=1, passes=1)
field = normalize(field)

# Gamma adjustment (contrast)
field = apply_gamma(field, 1.20)

# INVERT so water pools grow from centers
field = 1.0 - field
```

The inversion is crucial: without it, water would appear at peaks; we want it in valleys.

### Step 4: Floor Masking

Water should only appear on floor areas (rooms/passages):

```python
def _apply_floor_mask(field, floor_mask_fn):
    masked = field.copy()
    for y in range(height):
        for x in range(width):
            # Convert scaled coords to map coords
            map_x = x * scale_factor
            map_y = y * scale_factor
            
            if not floor_mask_fn(map_x, map_y):
                masked[y, x] = 1.0  # Force "dry" outside floor
    
    return masked
```

### Step 5: Contour Extraction (Marching Squares)

Extract water boundaries at the depth threshold:

```python
from dungeongen.algorithms.marching_squares import extract_contours

contours = extract_contours(
    field=field,
    threshold=depth,  # e.g., 0.60 for POOLS
    origin=(0.0, 0.0),
    cell_size=1.0
)
```

**Marching squares** walks through the field grid, identifying cells where the threshold is crossed, and traces the boundary as a polygon.

## Contour Processing

Raw contours from marching squares are jagged. They're processed in two steps:

### Thinning

Remove excessive points while preserving shape:

```python
def thin_points(contour, min_distance=2.0):
    result = [contour[0]]
    for point in contour[1:]:
        if distance(point, result[-1]) >= min_distance:
            result.append(point)
    return result
```

### Chaikin Smoothing

Iteratively smooth the polygon:

```python
def smooth_polygon(points, iterations=2, boundary_rect=None):
    for _ in range(iterations):
        new_points = []
        for i in range(len(points)):
            p0 = points[i]
            p1 = points[(i + 1) % len(points)]
            
            # Chaikin: replace edge with two points at 25% and 75%
            new_points.append((
                0.75 * p0[0] + 0.25 * p1[0],
                0.75 * p0[1] + 0.25 * p1[1]
            ))
            new_points.append((
                0.25 * p0[0] + 0.75 * p1[0],
                0.25 * p0[1] + 0.75 * p1[1]
            ))
        
        points = new_points
    
    return points
```

Chaikin subdivision creates smooth curves while maintaining the general shape.

## Island Grouping

Contours inside other contours are **islands** (dry areas within water):

```python
def _group_contours(contours):
    # Sort by area descending
    sorted_contours = sorted(contours, key=lambda x: -x.area)
    
    # For each contour, find smallest containing contour
    parent = [-1] * len(sorted_contours)
    
    for i, contour_i in enumerate(sorted_contours):
        test_point = contour_i[0]  # Sample point
        
        for j in range(i):  # Check larger contours
            contour_j = sorted_contours[j]
            if point_in_polygon(test_point, contour_j):
                parent[i] = j  # contour_i is inside contour_j
    
    # Build WaterShapes: root contours + their direct children (islands)
    shapes = []
    for i, contour in enumerate(sorted_contours):
        if parent[i] == -1:  # Root = water boundary
            islands = [sorted_contours[j] for j in range(len(sorted_contours))
                      if parent[j] == i]
            shapes.append(WaterShape(outer=contour, islands=islands))
```

This enables the **even-odd fill rule**: the outermost contour is water, the next level in is dry (island), the next is water again (pond on island), etc.

## Rendering

### Fill and Stroke

```python
def render_water(canvas, contours, style):
    # Build combined path with even-odd fill
    combined_path = skia.Path()
    combined_path.setFillType(skia.PathFillType.kEvenOdd)
    
    for contour in contours:
        add_contour_to_path(combined_path, contour)
    
    # Draw fill (semi-transparent gray)
    fill_paint = skia.Paint(
        Color=style.fill_color,  # (80, 80, 80, 100) - transparent gray
        Style=skia.Paint.kFill_Style
    )
    canvas.drawPath(combined_path, fill_paint)
    
    # Draw shoreline stroke
    stroke_paint = skia.Paint(
        Color=style.stroke_color,  # (40, 40, 40, 255) - dark gray
        Style=skia.Paint.kStroke_Style,
        StrokeWidth=style.stroke_width  # ~3.5
    )
    canvas.drawPath(combined_path, stroke_paint)
```

### Ripple Lines

Inset contours create parallel ripple lines:

```python
for inset in style.ripple_insets:  # e.g., (8.0, 16.0)
    inset_contour = offset_polygon(contour, -inset)
    draw_ripple_line(canvas, inset_contour, style)
```

#### Polygon Offset

Shrink the contour inward using vertex normals:

```python
def offset_polygon(contour, distance):
    result = []
    for i in range(len(contour)):
        p_prev = contour[(i - 1) % n]
        p_curr = contour[i]
        p_next = contour[(i + 1) % n]
        
        # Edge vectors and normals
        e1 = (p_curr - p_prev)
        e2 = (p_next - p_curr)
        n1 = normalize(perpendicular(e1))
        n2 = normalize(perpendicular(e2))
        
        # Average normal (bisector)
        avg_n = normalize((n1 + n2) / 2)
        
        # Offset, clamped at sharp angles
        factor = 1.0 / max(dot(n1, avg_n), 0.1)
        factor = min(factor, 3.0)  # Prevent extreme offsets
        
        new_point = p_curr + avg_n * distance * factor
        result.append(new_point)
    
    return result
```

#### Curvature-Aware Dashing

Ripple lines have gaps, but gaps only appear in straight sections to avoid crossing artifacts:

```python
def _draw_ripple_line(canvas, contour, style, seed):
    # Compute curvature at each vertex
    curvatures = compute_curvatures(contour)
    
    # Find low-curvature (straight) regions where gaps are allowed
    gap_allowed_regions = find_low_curvature_regions(contour, curvatures, threshold=0.15)
    
    pos = random_phase_offset()
    while pos < total_length:
        # Dash length
        dash_len = random(min_dash, max_dash)
        end_pos = pos + dash_len
        
        # EXTEND through corners (don't break in curved sections)
        while end_pos < total_length and not can_gap_at(end_pos, gap_allowed_regions):
            end_pos += 3.0  # Keep extending
        
        # Draw this segment
        draw_curved_segment(pos, end_pos)
        
        # Skip to next valid gap position
        gap_len = random(min_gap, max_gap)
        pos = end_pos + gap_len
        
        # Skip past any corners to find valid start
        while not can_gap_at(pos, gap_allowed_regions):
            pos += 2.0
```

## Configuration

### WaterFieldParams

| Parameter | Default | Description |
|-----------|---------|-------------|
| `resolution_scale` | 0.2 | Generate at 20% res (faster, coarser) |
| `num_basins` | 6 | Number of Gaussian depth basins |
| `sigma_range` | (15, 40) | Basin radius range in scaled pixels |
| `lf_scale` | 0.018 | Noise sample scale |
| `lf_octaves` | 3 | fBM octave count |
| `basins_weight` | 0.60 | Weight of basins vs noise |
| `depth` | 0.60 | Water threshold (use WaterDepth) |
| `smooth_iterations` | 2 | Chaikin smoothing passes |
| `min_area` | 25.0 | Discard tiny contours |

### WaterStyle

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fill_color` | (80, 80, 80, 100) | Semi-transparent gray |
| `stroke_color` | (40, 40, 40, 255) | Dark gray shoreline |
| `stroke_width` | 3.5 | Shoreline thickness |
| `ripple_color` | (40, 40, 40, 200) | Ripple line color |
| `ripple_width` | 1.75 | Ripple line thickness |
| `ripple_insets` | (8.0, 16.0) | Distance from shore for each ripple |
| `ripple_dash_range` | (8.0, 40.0) | Dash lengths |
| `ripple_gap_range` | (16.0, 80.0) | Gap lengths |

## Performance

- Field generation at 20% scale: ~10-30ms
- Contour extraction: ~5-15ms
- Rendering via Picture: ~5ms (first), ~1ms (cached)

The `WaterLayer.get_picture()` method pre-records all water drawing into a Skia Picture that can be replayed efficiently when the map is re-rendered with different clips.

