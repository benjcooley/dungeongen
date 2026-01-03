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

> **Note**: Only `LAIR` and `TEMPLE` currently have effects (tagging rooms). Other values are placeholders.

---

## Map Rendering

### `MapElement`

Base class for all renderable map elements (rooms, passages, doors, exits).

```python
from dungeongen.map.mapelement import MapElement
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `bounds` | `Rectangle` | Bounding box of the element |
| `shape` | `Shape` | Geometric shape of the element |
| `connections` | `Sequence[MapElement]` | Connected elements |
| `props` | `Sequence[Prop]` | Props contained in this element |
| `map` | `Map` | Parent map this element belongs to |

#### Methods

**`add_prop(prop: Prop) → None`**

Add a prop to this element.

**`remove_prop(prop: Prop) → None`**

Remove a prop from this element.

**`connect_to(other: MapElement) → None`**

Create a bidirectional connection to another element.

**`contains_point(x: float, y: float) → bool`**

Check if a point is inside this element's shape.

**`draw(canvas: skia.Canvas, layer: Layers) → None`**

Draw this element on the specified layer.

---

### `Region`

A group of connected map elements not separated by closed doors.

```python
from dungeongen.map.region import Region
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `shape` | `Shape` | Combined shape of all elements |
| `elements` | `List[MapElement]` | Elements in this region |

#### Methods

**`inflated(amount: float) → Region`**

Return a new region with inflated shape (for crosshatch clipping).

**`to_path() → skia.Path`**

Convert the region's shape to a Skia path for rendering.

---

### `Layers`

Enum defining the rendering layer order.

```python
from dungeongen.map.enums import Layers
```

| Value | Description |
|-------|-------------|
| `SHADOW` | Shadow layer, drawn first |
| `PROPS` | Main prop layer |
| `OVERLAY` | Overlay layer (doors drawn on top of borders) |
| `TEXT` | Text layer (room numbers) |

---

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

## Props

### `Prop`

Abstract base class for decorative map props.

```python
from dungeongen.map._props.prop import Prop, PropType
```

#### Constructor

```python
Prop(prop_type: PropType, position: Point, rotation: Rotation = Rotation.ROT_0,
     boundary_shape: Shape = None, grid_size: Point = None)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `position` | `Point` | Top-left of grid bounds (or bounds for non-grid) |
| `center` | `Point` | Center of the prop |
| `bounds` | `Rectangle` | Bounding rectangle |
| `grid_bounds` | `Rectangle` | Grid-aligned bounds (if grid-aligned) |
| `grid_size` | `Point` | Size in grid units (if grid-aligned) |
| `rotation` | `Rotation` | Current rotation |
| `shape` | `Shape` | Collision boundary |
| `container` | `MapElement` | Element containing this prop |
| `prop_type` | `PropType` | Type configuration |

#### Methods

**`draw(canvas: skia.Canvas, layer: Layers) → None`**

Draw the prop. Handles coordinate transforms and calls `_draw_content`.

**`place_random_position(max_attempts: int = 30) → Point | None`**

Try to place prop at a valid random position within its container. Returns position if successful, None if all attempts fail.

**`is_valid_position(x: float, y: float, rotation: Rotation = ROT_0) → bool`**

Check if a position is valid (inside container, not overlapping other props).

**`snap_valid_position(x: float, y: float) → Point | None`**

Snap coordinates to nearest valid position for this prop type.

---

### `PropType`

Configuration dataclass for prop behavior.

```python
from dungeongen.map._props.prop import PropType
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `is_decoration` | `bool` | `False` | Decorations don't block other props |
| `is_wall_aligned` | `bool` | `False` | Snaps to walls based on rotation |
| `is_grid_aligned` | `bool` | `False` | Snaps to grid cell intersections |
| `grid_size` | `Point` | `None` | Size in grid units (width, height) |
| `boundary_shape` | `Shape` | `None` | Collision shape centered at origin |

---

### `Rotation`

Enum for 90° rotation increments.

```python
from dungeongen.graphics.rotation import Rotation
```

| Value | Degrees | Radians |
|-------|---------|---------|
| `ROT_0` | 0° | 0 |
| `ROT_90` | 90° | π/2 |
| `ROT_180` | 180° | π |
| `ROT_270` | 270° | 3π/2 |

---

### Built-in Props

```python
from dungeongen.map._props.column import Column, ColumnType
from dungeongen.map._props.altar import Altar
from dungeongen.map._props.stairs import Stairs
from dungeongen.map.door import Door, DoorState
from dungeongen.map.exit import Exit
```

| Class | Description |
|-------|-------------|
| `Column` | Round or square columns (1/3 cell size) |
| `Altar` | Rectangular altar tables |
| `Stairs` | Up/down stairs with directional rendering |
| `Door` | Open, closed, or secret doors |
| `Exit` | Dungeon entrance/exit markers |

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

## Layout Occupancy Grid

The layout generator uses an occupancy grid for collision detection and pathfinding.

### `OccupancyGrid`

```python
from dungeongen.layout.occupancy import OccupancyGrid, CellType, CellModifier
```

#### Methods

**`is_empty(x: int, y: int) → bool`**

Check if a cell is empty.

**`get_type(x: int, y: int) → CellType`**

Get the cell type at a position.

**`can_place_room(x: int, y: int, width: int, height: int, margin: int = 1) → bool`**

Check if a room can be placed at position with given margin.

**`can_place_passage(cells: List[Tuple[int, int]]) → bool`**

Check if a passage can occupy the given cells.

**`mark_room(room_id: str, x: int, y: int, width: int, height: int, ...) → None`**

Mark cells as occupied by a room (interior = ROOM, buffer = RESERVED, corners = BLOCKED).

**`mark_passage(passage_id: str, cells: List[Tuple[int, int]], margin: int = 1) → None`**

Mark cells as occupied by a passage with reserved buffer.

**`find_path(start: Tuple[int, int], end: Tuple[int, int], ...) → List[Tuple[int, int]] | None`**

A* pathfinding that avoids obstacles. Returns waypoints (turns only).

---

### `CellType`

Enum for what occupies a grid cell.

```python
from dungeongen.layout.occupancy import CellType
```

| Value | Description | Passable? |
|-------|-------------|-----------|
| `EMPTY` | Nothing here | Yes |
| `ROOM` | Room interior | No |
| `PASSAGE` | Corridor cell | Yes (once) |
| `WALL` | Room perimeter | No |
| `DOOR` | Connection point | No |
| `RESERVED` | Buffer around rooms | Yes (once) |
| `BLOCKED` | Corners, exit adjacents | No |

---

### `CellModifier`

Additional flags on cells.

```python
from dungeongen.layout.occupancy import CellModifier
```

| Value | Description |
|-------|-------------|
| `NONE` | No modifier |
| `DOOR` | Cell has a door (blocks crossing) |
| `JUNCTION` | T-junction or crossing |
| `STAIRS` | Cell has stairs (blocks crossing) |
| `EXIT` | Dungeon entrance/exit |

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

