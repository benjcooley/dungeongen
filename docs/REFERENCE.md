# DungeonGen Reference

A reference guide to the key classes and methods in DungeonGen.

## Layout Generation

### `DungeonGenerator`

Main class for generating dungeon layouts.

```python
from dungeongen.layout import DungeonGenerator, GenerationParams
```

#### Constructor

```python
DungeonGenerator(params: GenerationParams = None)
```

Creates a generator with the given parameters. If `params` is None, uses defaults.

#### Methods

**`generate(seed: int = None) → Dungeon`**

Generates a complete dungeon layout. If `seed` is provided, generation is deterministic.

```python
generator = DungeonGenerator(params)
dungeon = generator.generate(seed=42)
```

---

### `GenerationParams`

Configuration dataclass for dungeon generation.

```python
from dungeongen.layout import GenerationParams, DungeonSize, SymmetryType, DungeonArchetype
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `size` | `DungeonSize` | `MEDIUM` | Overall dungeon size |
| `symmetry` | `SymmetryType` | `NONE` | Symmetry mode |
| `archetype` | `DungeonArchetype` | `CLASSIC` | Structural pattern |
| `room_size_bias` | `float` | `0.0` | -1.0 (small) to 1.0 (large) |
| `round_room_chance` | `float` | `0.15` | Chance of circular rooms |
| `density` | `float` | `0.5` | 0.0 (sparse) to 1.0 (tight) |
| `loop_factor` | `float` | `0.3` | Extra connections beyond MST |
| `passage_width` | `int` | `1` | Passage width in grid units |

---

### `Dungeon`

Output data structure from generation.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `rooms` | `Dict[str, Room]` | Room instances by ID |
| `passages` | `Dict[str, Passage]` | Passage instances by ID |
| `doors` | `Dict[str, Door]` | Door instances by ID |
| `stairs` | `Dict[str, Stair]` | Stair instances by ID |
| `exits` | `Dict[str, Exit]` | Exit instances by ID |
| `seed` | `int` | Seed used for generation |
| `bounds` | `Tuple[int,int,int,int]` | Bounding box (x, y, width, height) |
| `mirror_pairs` | `Dict[str, str]` | Room ID pairs for symmetric layouts |

---

### Enums

**`DungeonSize`**: `TINY`, `SMALL`, `MEDIUM`, `LARGE`, `XLARGE`

**`SymmetryType`**: `NONE`, `BILATERAL`, `RADIAL_2`, `RADIAL_4`

**`DungeonArchetype`**: `CLASSIC`, `WARREN`, `TEMPLE`, `CRYPT`, `CAVERN`, `FORTRESS`, `LAIR`

---

## Map Rendering

### `Map`

Main container and renderer for dungeon maps.

```python
from dungeongen.map.map import Map
```

#### Constructor

```python
Map(options: Options)
```

Creates an empty map with the given rendering options.

#### Methods

**`render(canvas: skia.Canvas, transform: skia.Matrix = None) → None`**

Renders the map to a Skia canvas. If `transform` is None, calculates a fit transform automatically.

**`render_to_png(filename: str, width: int = 1200, height: int = 1200) → None`**

Convenience method to render directly to a PNG file.

```python
dungeon_map.render_to_png('output.png')
dungeon_map.render_to_png('large.png', width=2400, height=2400)
```

**`render_to_svg(filename: str, width: int = 1200, height: int = 1200) → None`**

Convenience method to render directly to an SVG file.

```python
dungeon_map.render_to_svg('output.svg')
```

**`calculate_fit_transform(canvas_width: int, canvas_height: int) → skia.Matrix`**

Calculates a transform matrix that scales and centers the map to fit within the given canvas dimensions. Includes padding based on `options.map_border_cells`.

```python
transform = dungeon_map.calculate_fit_transform(1200, 1200)
```

**`set_water(depth: float, seed: int = 42, ...) → None`**

Enables water generation with the given parameters.

```python
dungeon_map.set_water(
    depth=WaterDepth.POOLS,
    seed=42,
    lf_scale=0.018,         # Noise scale
    resolution_scale=0.2,    # Resolution (lower = faster)
    stroke_width=3.5,        # Shoreline thickness
    ripple_inset=8.0         # Ripple spacing
)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `bounds` | `Rectangle` | Bounding box of all elements |
| `rooms` | `Iterator[Room]` | All room elements |
| `passages` | `Iterator[Passage]` | All passage elements |
| `doors` | `Iterator[Door]` | All door elements |
| `exits` | `Iterator[Exit]` | All exit elements |
| `options` | `Options` | Rendering options |

---

### `Options`

Rendering configuration dataclass.

```python
from dungeongen.options import Options
```

#### Key Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `canvas_width` | `int` | `2000` | Default canvas width |
| `canvas_height` | `int` | `2000` | Default canvas height |
| `border_width` | `float` | `6.0` | Room/passage border thickness |
| `border_color` | `int` | `0xFF000000` | Border color (ARGB) |
| `room_color` | `int` | `0xFFFFFFFF` | Room fill color |
| `room_shadow_color` | `int` | `0xFFD0D0D0` | Shadow color |
| `room_shadow_offset_x` | `float` | `6.0` | Shadow X offset |
| `room_shadow_offset_y` | `float` | `8.0` | Shadow Y offset |
| `crosshatch_stroke_width` | `float` | `1.5` | Crosshatch line thickness |
| `crosshatch_border_size` | `float` | `24.0` | Crosshatch area around rooms |
| `grid_style` | `GridStyle` | `DOTS` | Grid overlay style |
| `grid_color` | `int` | `0xFF202020` | Grid color |
| `map_border_cells` | `float` | `4.0` | Padding around map in grid cells |

---

### `WaterDepth`

Preset water depth levels.

```python
from dungeongen.map.water_layer import WaterDepth
```

| Constant | Value | Coverage |
|----------|-------|----------|
| `DRY` | `0.0` | No water |
| `PUDDLES` | `0.75` | ~30-40% |
| `POOLS` | `0.60` | ~50-60% |
| `LAKES` | `0.45` | ~70-80% |
| `FLOODED` | `0.30` | ~85-95% |

---

## Adapter

### `convert_dungeon`

Converts a layout `Dungeon` to a renderable `Map`.

```python
from dungeongen.webview.adapter import convert_dungeon
```

**`convert_dungeon(layout_dungeon: Dungeon, water_depth: float = 0.0, ...) → Map`**

```python
dungeon_map = convert_dungeon(
    layout_dungeon,
    water_depth=WaterDepth.POOLS,  # Water level
    water_scale=0.016,              # Noise scale
    water_res=0.3,                  # Resolution scale
    water_stroke=3.0,               # Shoreline width
    water_ripple=12.0               # Ripple inset
)
```

This function:
- Creates a new `Map` with default `Options`
- Converts all rooms, passages, doors, stairs, and exits
- Handles coordinate normalization
- Splits crossing passages into segments
- Decorates rooms with props (columns, altars, etc.)
- Configures water generation if enabled

---

## Layout Models

These are the data models output by the layout generator.

### `Room` (layout)

```python
from dungeongen.layout import Room, RoomShape
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier |
| `x`, `y` | `int` | Grid position (top-left) |
| `width`, `height` | `int` | Dimensions in grid units |
| `shape` | `RoomShape` | `RECTANGLE` or `CIRCLE` |
| `number` | `int` | Display number (1, 2, 3...) |

### `Passage` (layout)

```python
from dungeongen.layout import Passage, PassageStyle
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier |
| `waypoints` | `List[Tuple[int,int]]` | Grid coordinates (corners) |
| `start_room` | `str` | Starting room ID |
| `end_room` | `str` | Ending room ID |
| `style` | `PassageStyle` | Rendering style |

### `Door` (layout)

```python
from dungeongen.layout import Door, DoorType
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique identifier |
| `x`, `y` | `int` | Grid position |
| `door_type` | `DoorType` | `OPEN`, `CLOSED`, `SECRET` |

---

## Graphics Primitives

### `Rectangle`

```python
from dungeongen.graphics.shapes import Rectangle
```

```python
rect = Rectangle(x, y, width, height)
rect.contains(px, py)  # Point containment test
rect.intersects(other) # Rectangle intersection test
rect.inflated(amount)  # Return expanded copy
```

### `Circle`

```python
from dungeongen.graphics.shapes import Circle
```

```python
circle = Circle(center_x, center_y, radius)
circle.contains(px, py)
circle.bounds  # Bounding Rectangle
```

### `ShapeGroup`

Composite shape that can combine rectangles and circles.

```python
from dungeongen.graphics.shapes import ShapeGroup

group = ShapeGroup.combine([rect1, rect2, circle1])
group.contains(px, py)  # True if any shape contains point
group.to_path()         # Convert to Skia path for rendering
```

---

## Constants

```python
from dungeongen.constants import CELL_SIZE

CELL_SIZE = 40  # Pixels per grid cell
```

All grid coordinates are multiplied by `CELL_SIZE` for rendering. One grid cell represents 5 feet in D&D scale.

---

## Grid/Map Coordinate Conversion

```python
from dungeongen.graphics.conversions import grid_to_map, map_to_grid

# Grid (5, 10) → Map pixels (200, 400)
map_x, map_y = grid_to_map(5, 10)

# Map pixels (200, 400) → Grid (5, 10)
grid_x, grid_y = map_to_grid(200, 400)
```

