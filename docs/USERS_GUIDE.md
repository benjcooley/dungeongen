# DungeonGen User's Guide

This guide covers how to use DungeonGen to generate and render dungeon maps.

## Installation

```bash
pip install dungeongen
```

For development:
```bash
git clone https://github.com/benjcooley/dungeongen.git
cd dungeongen
pip install -e .
```

## Quick Start

### Interactive Web Preview

The fastest way to explore DungeonGen:

```bash
python -m dungeongen.webview.app
```

Open http://localhost:5050 in your browser. Use the controls to adjust parameters and click "Generate" to create dungeons.

### Python API

```python
from dungeongen.layout import DungeonGenerator, GenerationParams, DungeonSize, SymmetryType
from dungeongen.webview.adapter import convert_dungeon
from dungeongen.map.water_layer import WaterDepth

# Configure generation
params = GenerationParams()
params.size = DungeonSize.MEDIUM
params.symmetry = SymmetryType.BILATERAL

# Generate layout
generator = DungeonGenerator(params)
dungeon = generator.generate(seed=42)

# Convert to renderable map
dungeon_map = convert_dungeon(dungeon, water_depth=WaterDepth.POOLS)

# Save as PNG or SVG
dungeon_map.render_to_png('my_dungeon.png')
dungeon_map.render_to_svg('my_dungeon.svg')
```

## Generation Parameters

### Dungeon Size

Controls the number of rooms:

| Size | Room Count |
|------|------------|
| `TINY` | 4-6 rooms |
| `SMALL` | 6-10 rooms |
| `MEDIUM` | 10-16 rooms |
| `LARGE` | 16-24 rooms |
| `XLARGE` | 24-40 rooms |

```python
params.size = DungeonSize.LARGE
```

### Symmetry Types

| Type | Description |
|------|-------------|
| `NONE` | Asymmetric, organic layout |
| `BILATERAL` | Mirror symmetry (left/right) |
| `RADIAL_2` | 180° rotational symmetry |
| `RADIAL_4` | 90° rotational symmetry (4-fold) |

```python
params.symmetry = SymmetryType.BILATERAL
```

### Dungeon Archetypes

> **Note**: Archetypes are currently **partially implemented**. They add semantic tags but don't change generation parameters. Use the manual parameters below to achieve different styles.

| Archetype | Current Effect |
|-----------|----------------|
| `LAIR` | Tags largest room as 'lair'/'boss' |
| `TEMPLE` | Tags central room as 'sanctum' |
| `CLASSIC`, `WARREN`, `CRYPT`, `CAVERN`, `FORTRESS` | No effect (placeholder) |

To achieve different dungeon styles, adjust parameters manually:

```python
# Warren-style (dense maze of small rooms)
params.density = 0.9
params.room_size_bias = -0.8  # Cozy
params.loop_factor = 0.5

# Crypt-style (linear with few branches)
params.linearity = 0.8
params.loop_factor = 0.1

# Temple-style (large symmetric)
params.symmetry = SymmetryType.BILATERAL
params.room_size_bias = 0.5
```

### Room Size Bias

Controls the mix of room sizes:

```python
params.room_size_bias = -0.5  # Cozy: mostly small rooms (max 5x5)
params.room_size_bias = 0.0   # Mixed: small and medium
params.room_size_bias = 0.5   # Grand: includes large rooms
```

### Density

Controls spacing between rooms:

```python
params.density = 0.3  # Sparse: rooms spread apart
params.density = 0.5  # Normal: moderate spacing
params.density = 0.9  # Tight: rooms packed close together
```

### Other Parameters

```python
params.round_room_chance = 0.15  # Chance of circular rooms (0.0-1.0)
params.loop_factor = 0.3         # Extra connections beyond minimum spanning tree
params.passage_width = 1         # Passage width in grid cells
```

## Water Features

Add procedural water to dungeons:

```python
from dungeongen.map.water_layer import WaterDepth

# Water depth presets
dungeon_map = convert_dungeon(dungeon, water_depth=WaterDepth.PUDDLES)  # ~30-40% coverage
dungeon_map = convert_dungeon(dungeon, water_depth=WaterDepth.POOLS)    # ~50-60% coverage
dungeon_map = convert_dungeon(dungeon, water_depth=WaterDepth.LAKES)    # ~70-80% coverage
dungeon_map = convert_dungeon(dungeon, water_depth=WaterDepth.FLOODED)  # ~85-95% coverage
```

### Water Appearance Parameters

```python
dungeon_map = convert_dungeon(
    dungeon,
    water_depth=WaterDepth.POOLS,
    water_scale=0.016,     # Noise scale (larger = larger water bodies)
    water_res=0.3,         # Resolution scale (lower = faster but coarser)
    water_stroke=3.0,      # Shoreline stroke width
    water_ripple=12.0      # Ripple line inset distance
)
```

## Rendering Options

### Output Formats

```python
# PNG (raster, good for web/print)
dungeon_map.render_to_png('dungeon.png', width=1200, height=1200)

# SVG (vector, scalable)
dungeon_map.render_to_svg('dungeon.svg', width=1200, height=1200)
```

### Custom Rendering

For more control, render directly to a Skia canvas:

```python
import skia

# Create canvas
surface = skia.Surface(1200, 1200)
canvas = surface.getCanvas()

# Get transform that fits map to canvas
transform = dungeon_map.calculate_fit_transform(1200, 1200)

# Render
dungeon_map.render(canvas, transform)

# Save
image = surface.makeImageSnapshot()
image.save('dungeon.png', skia.kPNG)
```

### Rendering Style Options

Customize colors and stroke widths via `Options`:

```python
from dungeongen.options import Options

options = Options()
options.border_width = 4.0                    # Room border thickness
options.crosshatch_stroke_width = 1.5         # Crosshatch line thickness
options.room_shadow_offset_x = 6.0            # Shadow offset
options.room_shadow_offset_y = 8.0
options.grid_style = GridStyle.DOTS           # Grid overlay style
```

## Web Preview Interface

The web preview (`python -m dungeongen.webview.app`) provides an interactive UI:

### Controls

| Control | Description |
|---------|-------------|
| **SIZE** | Tiny, Small, Med, Large |
| **SYM** | None, Mirror, Rot2, Rot4 |
| **TYPE** | Classic, Warren, Temple, Crypt, Lair |
| **CROSS** | Crosshatch density (No, Lo, Med, Hi) |
| **PACK** | Room packing density (Sparse, Norm, Tight) |
| **ROOMS** | Room size bias (Cozy, Mixed, Grand) |
| **WATER** | Water depth (Dry, Puddles, Pools, Lakes, Flooded) |
| **Seed** | Random seed (leave blank for random) |

### View Modes

- **Render**: Full quality rendered map with crosshatch shading
- **Map**: Layout-only SVG (faster preview)
- **Debug**: Shows occupancy grid and element indices

### Water Sliders

When water is enabled, fine-tune with sliders:
- **Scale**: Size of water bodies
- **Resolution**: Quality vs speed tradeoff
- **Stroke**: Shoreline thickness
- **Ripple**: Ripple line spacing

## Working with Layout Data

Access the raw layout without rendering:

```python
from dungeongen.layout import DungeonGenerator, GenerationParams

params = GenerationParams()
params.size = DungeonSize.MEDIUM

generator = DungeonGenerator(params)
dungeon = generator.generate(seed=42)

# Access rooms
for room_id, room in dungeon.rooms.items():
    print(f"Room {room.number}: {room.width}x{room.height} at ({room.x}, {room.y})")

# Access passages
for passage_id, passage in dungeon.passages.items():
    print(f"Passage from {passage.start_room} to {passage.end_room}")

# Access doors
for door_id, door in dungeon.doors.items():
    print(f"Door at ({door.x}, {door.y}): {door.door_type}")
```

## Deterministic Generation

Use seeds for reproducible results:

```python
# Same seed = same dungeon
dungeon1 = generator.generate(seed=12345)
dungeon2 = generator.generate(seed=12345)
assert dungeon1.rooms == dungeon2.rooms
```

## Performance Tips

1. **Use appropriate resolution for water**: Lower `water_res` (0.2-0.3) is faster
2. **Generate at target size**: Don't render larger than needed
3. **Reuse generators**: Create one `DungeonGenerator` and call `generate()` multiple times
4. **SVG for print**: Use SVG output for scalable print-quality maps

## Common Patterns

### Generate Multiple Dungeons

```python
generator = DungeonGenerator(params)

for i in range(10):
    dungeon = generator.generate(seed=i)
    dungeon_map = convert_dungeon(dungeon)
    dungeon_map.render_to_png(f'dungeon_{i:03d}.png')
```

### Batch Different Styles

```python
for symmetry in [SymmetryType.NONE, SymmetryType.BILATERAL, SymmetryType.RADIAL_4]:
    params.symmetry = symmetry
    generator = DungeonGenerator(params)
    dungeon = generator.generate(seed=42)
    dungeon_map = convert_dungeon(dungeon)
    dungeon_map.render_to_png(f'dungeon_{symmetry.name.lower()}.png')
```

### Thumbnail Generation

```python
# Small thumbnails for previews
dungeon_map.render_to_png('thumbnail.png', width=300, height=300)
```

