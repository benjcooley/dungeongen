# DungeonGen Architecture

This document describes the architecture of DungeonGen, a procedural dungeon map generator written in Python.

## Overview

DungeonGen is organized into two main subsystems:

1. **Layout Generation** (`dungeongen.layout`) - Procedurally generates dungeon layouts: rooms, passages, doors, and their spatial relationships
2. **Map Rendering** (`dungeongen.map`) - Renders layouts as high-quality hand-drawn style maps with crosshatch shading, water features, and decorative props

These are intentionally separated: the layout system outputs a data structure that can be rendered by the map system, or serialized, or used by game engines directly.

## Package Structure

```
src/dungeongen/
├── layout/              # Dungeon layout generation
│   ├── generator.py     # Main DungeonGenerator class
│   ├── models.py        # Data models: Room, Passage, Door, Dungeon
│   ├── params.py        # GenerationParams, DungeonSize, SymmetryType
│   ├── spatial.py       # Collision detection, Delaunay triangulation, MST
│   ├── occupancy.py     # Grid-based collision tracking
│   └── validator.py     # Layout validation
│
├── map/                 # Map rendering system
│   ├── map.py           # Main Map class - container and renderer
│   ├── room.py          # Room rendering with numbered labels
│   ├── passage.py       # Passage/corridor rendering
│   ├── door.py          # Door rendering (open/closed)
│   ├── exit.py          # Dungeon entrance/exit rendering
│   ├── water_layer.py   # Water generation using noise fields
│   ├── mapelement.py    # Base class for renderable elements
│   ├── occupancy.py     # Render-time occupancy grid
│   ├── _props/          # Decorative props (columns, altars, etc.)
│   └── _arrange/        # Prop placement algorithms
│
├── drawing/             # Low-level drawing utilities
│   ├── crosshatch.py    # Crosshatch pattern generation
│   ├── crosshatch_tiled.py  # Optimized tiled crosshatch
│   └── water.py         # Water shoreline and ripple rendering
│
├── graphics/            # Graphics primitives
│   ├── shapes.py        # Rectangle, Circle, ShapeGroup
│   ├── noise.py         # Perlin noise, fBM, Gaussian basins
│   ├── math.py          # Point2D, Matrix2D, geometry utilities
│   └── conversions.py   # Grid-to-map coordinate conversions
│
├── algorithms/          # Generic algorithms
│   ├── marching_squares.py  # Contour extraction from scalar fields
│   ├── chaikin.py       # Curve smoothing
│   └── poisson.py       # Poisson disk sampling
│
├── webview/             # Interactive web preview
│   ├── app.py           # Flask application
│   ├── adapter.py       # Layout-to-Map conversion
│   └── templates/       # HTML/JS UI
│
├── options.py           # Rendering options (colors, stroke widths)
├── constants.py         # Global constants (CELL_SIZE)
└── debug_config.py      # Debug visualization flags
```

## Design Principles

### 1. Separation of Concerns

The layout system knows nothing about rendering. It produces abstract data structures:
- Rooms with grid coordinates and dimensions
- Passages as lists of waypoints
- Doors, stairs, and exits with positions and types

The map system converts these into renderable geometry and handles all visual aspects.

### 2. Grid-Based Generation

All layout generation operates on an integer grid. One grid cell = 5 feet in D&D terms. This simplifies collision detection and spatial reasoning.

The map system converts grid coordinates to pixel coordinates using `CELL_SIZE` (default 40 pixels per cell).

### 3. Connection Chains and Regions

Map elements connect in chains that define traversal:
```
Room → Door → Passage → Door → Room
```

**Regions** group connected elements that aren't separated by closed doors. A region contains:
- A combined `Shape` (union of all element shapes)
- References to the contained `MapElement` instances

```python
class Region:
    shape: Shape                    # Combined geometry for clipping
    elements: List[MapElement]      # Rooms, passages in this region
```

Regions are used for:
- **Crosshatch clipping** - The crosshatch pattern is clipped to the inflated union of all region shapes
- **Water clipping** - Water is clipped to stay within floor areas
- **Flood-fill rendering** - All elements in a region share the same fill pass

Closed doors break the connectivity graph, creating separate regions. This allows dungeons with sealed-off areas to render correctly.

### 4. Layered Rendering

The map renders in layers using the `Layers` enum:

```python
class Layers(Enum):
    SHADOW = auto()    # Shadow layer drawn first
    PROPS = auto()     # Base layer for props and general elements
    OVERLAY = auto()   # Overlay layer that draws over room outlines (doors, etc)
    TEXT = auto()      # Text layer for room numbers and labels
```

The full render order:
1. **Crosshatch background** - The dungeon "walls"
2. **Room shadows** (`Layers.SHADOW`) - Drop shadows for depth
3. **Room fills** - The floor areas
4. **Grid** - Optional dot grid overlay
5. **Water** - Procedural water features
6. **Props** (`Layers.PROPS`) - Columns, altars, fountains, etc.
7. **Borders** - Room/passage outlines
8. **Doors** (`Layers.OVERLAY`) - Door overlays drawn on top
9. **Text** (`Layers.TEXT`) - Room numbers

Each `MapElement.draw(canvas, layer)` is called once per layer, allowing props to draw shadows separately from their main content, and overlays to draw on top of borders.

## Key Classes

### Layout System

**`DungeonGenerator`** - Main entry point for layout generation
- Takes `GenerationParams` to configure size, symmetry, archetype
- Uses recursive branching with spatial hashing for collision detection
- Supports symmetry modes: bilateral (mirror), radial-2, radial-4
- Implements "Jaquaying" - adding loops and alternate paths

**`Dungeon`** - Output data structure
- Contains rooms, passages, doors, stairs, exits
- Stores mirror pairs for symmetric layouts
- Includes bounds and metadata

**`GenerationParams`** - Configuration dataclass
- `size`: TINY through XLARGE (affects room count)
- `symmetry`: NONE, BILATERAL, RADIAL_2, RADIAL_4
- `archetype`: CLASSIC, WARREN, TEMPLE, CRYPT, LAIR *(partially implemented - see note)*
- `density`: Controls room spacing (sparse to tight)

> **Note on Archetypes**: Currently only LAIR (tags largest room) and TEMPLE (tags central room) have effects. Other archetypes are defined but do not modify generation. Use `density`, `room_size_bias`, and `loop_factor` manually to achieve different dungeon styles.

### Map System

**`Map`** - Main renderer and element container
- Holds all `MapElement` instances (rooms, passages, doors, exits)
- Manages occupancy grid for prop placement
- Handles water layer generation
- `render(canvas, transform)` - Renders to Skia canvas
- `render_to_png(filename)` / `render_to_svg(filename)` - Convenience methods

**`MapElement`** - Base class for all renderable elements
- Rooms, passages, doors, exits all inherit from this
- Has a `Shape` defining its geometry
- Maintains bidirectional connections to other elements
- Contains a list of `Prop` instances for decorations
- Provides `draw(canvas, layer)` method called per rendering layer

**`Region`** - Group of connected elements
- Represents a contiguous area not separated by closed doors
- Contains combined `Shape` of all elements for flood-fill rendering
- Used to clip crosshatch and water to open areas

**`Room`** - Renderable room
- Rectangular or circular shape
- Draws numbered label
- Contains props (columns, altars, etc.)

**`Passage`** - Renderable corridor
- Defined by grid waypoints
- Handles turns and variable widths
- Can contain stairs props

**`Options`** - Rendering configuration
- Colors for backgrounds, shadows, borders
- Stroke widths and spacing
- Grid style and appearance

### Adapter

**`convert_dungeon(layout_dungeon, water_depth=0.0) → Map`**
- Converts layout output to renderable Map
- Handles coordinate normalization
- Splits crossing passages into segments
- Decorates rooms with props

## Layout Occupancy Grid

The layout generator uses an occupancy grid to track what's at each grid cell during dungeon generation. This prevents overlapping rooms and ensures passages route correctly.

### Cell Types

```python
class CellType(IntEnum):
    EMPTY = 0       # Nothing here - passages can go through
    ROOM = 1        # Interior of a room - impassable
    PASSAGE = 2     # Corridor cell - crossing allowed (once)
    WALL = 3        # Room perimeter (unused in current impl)
    DOOR = 4        # Connection point between room and passage
    RESERVED = 5    # Buffer zone around rooms - limited crossing
    BLOCKED = 6     # Permanently blocked (corners, exit adjacents)
```

### Why RESERVED and BLOCKED?

**RESERVED cells** form a 1-cell buffer around rooms. They serve two purposes:
1. **Spacing** - Prevents rooms from touching directly
2. **Passage routing constraints** - Passages can cross ONE reserved cell (to connect to a room) but not run along the margin (which would hug the wall)

The pattern `RR` (two reserved cells in a row) is invalid for passages longer than 2 cells. This prevents corridors from running parallel to room walls.

**BLOCKED cells** mark positions that should never have passages:
1. **Room corners** - Passages connecting at corners look bad visually
2. **Round room exit adjacents** - For circular rooms, the cells beside each cardinal exit point are blocked to force passages to connect at clean angles

```
Example: Round room with exit to the north

     B . B      B = BLOCKED (beside exit)
     R X R      X = EXIT cell (passage connects here)
   R R # R R    # = ROOM cells
   R # # # R    R = RESERVED cells
   R R # R R
     R R R
```

### Cell Modifiers

Cells can have modifiers independent of type:

```python
class CellModifier(IntEnum):
    NONE = 0        # No modifier
    DOOR = 1        # Has a door
    JUNCTION = 2    # T-junction or crossing
    STAIRS = 3      # Has stairs
    EXIT = 4        # Dungeon entrance/exit
```

Passages with `DOOR` or `STAIRS` modifiers are blocking - other passages cannot cross them.

### Pathfinding Rules

When finding routes for new passages, the A* pathfinder enforces:
- No `ROOM` cells (can't go through rooms)
- No `BLOCKED` cells (corners, exit adjacents)
- No `DOOR` cells (existing doors are blocking)
- No `PP` pattern (can only cross ONE existing passage)
- No `RR` pattern (can't run along room margins)

## Water System

Water uses a noise-based field generation pipeline:

1. **Field Generation** (`WaterLayer`)
   - Gaussian basins create large-scale depth variation
   - fBM noise adds organic detail
   - Resolution scaling for performance

2. **Contour Extraction** (`marching_squares.py`)
   - Extracts isosurfaces at water threshold
   - Produces outer boundaries and inner islands

3. **Smoothing** (`chaikin.py`)
   - Chaikin subdivision for smooth curves
   - Catmull-Rom to Bezier conversion for drawing

4. **Rendering** (`water.py`)
   - Shoreline strokes with organic variation
   - Parallel ripple lines at configurable insets

## Crosshatch System

The hand-drawn aesthetic comes from crosshatch shading:

1. **Tile Generation** (`crosshatch_tiled.py`)
   - Pre-generates a seamless crosshatch tile
   - Uses Poisson disk sampling for natural distribution
   - Clusters of parallel strokes at varied angles

2. **Clipped Tiling**
   - Tiles the pattern across dungeon bounds
   - Clips to the union of all room/passage shapes (inflated)
   - Efficient for large dungeons

## Props System

Props are decorative elements placed in rooms and passages (columns, altars, fountains, etc.).

### Architecture

```
Prop (abstract base class)
├── Column       - Round or square columns
├── Altar        - Rectangular altar tables
├── Fountain     - Circular fountains with water
├── Stairs       - Ascending/descending stairs
├── Door         - Open/closed/secret doors
└── Exit         - Dungeon entrance/exit markers
```

### PropType

Every prop has a `PropType` that defines its behavior:

```python
@dataclass
class PropType:
    is_decoration: bool = False     # True = crosshatch/fill decoration (drawn first)
    is_wall_aligned: bool = False   # True = snaps to walls
    is_grid_aligned: bool = False   # True = snaps to grid intersections
    grid_size: Point | None = None  # Size in grid units (width, height)
    boundary_shape: Shape | None = None  # Collision boundary centered at origin
```

**Decorations** (rocks, debris) don't block other props and are drawn before regular props.

**Grid-aligned** props snap to the CELL_SIZE grid (columns, altars).

**Wall-aligned** props snap to room walls based on rotation (doors, alcoves).

### Creating a New Prop

1. **Define the PropType** with boundary shape and alignment:

```python
from dungeongen.map._props.prop import Prop, PropType
from dungeongen.graphics.shapes import Rectangle, Circle
from dungeongen.constants import CELL_SIZE

# A 2x1 grid-aligned prop (like an altar)
MY_PROP_TYPE = PropType(
    is_grid_aligned=True,
    grid_size=(2, 1),  # 2 cells wide, 1 cell tall
    boundary_shape=Rectangle(
        -CELL_SIZE, -CELL_SIZE/2,  # Centered at origin
        CELL_SIZE * 2, CELL_SIZE
    )
)
```

2. **Subclass Prop** and implement `_draw_content`:

```python
class MyProp(Prop):
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0):
        super().__init__(MY_PROP_TYPE, position, rotation)
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers):
        """Draw prop content in local coordinates (origin at center, facing right)."""
        if layer == Layers.SHADOW:
            # Draw shadow (offset and darker)
            canvas.save()
            canvas.translate(
                self.options.room_shadow_offset_x,
                self.options.room_shadow_offset_y
            )
            shadow_paint = skia.Paint(Color=self.options.room_shadow_color)
            # ... draw shadow shape ...
            canvas.restore()
            
        elif layer == Layers.PROPS:
            # Draw main content
            fill_paint = skia.Paint(Color=self.options.prop_light_color)
            outline_paint = skia.Paint(
                Style=skia.Paint.kStroke_Style,
                StrokeWidth=self.options.border_width,
                Color=self.options.border_color
            )
            # ... draw prop shape ...
```

3. **Position semantics**:
   - For grid-aligned props: `position` is the TOP-LEFT corner of the grid bounds
   - For non-grid props: `position` is the top-left of the boundary shape
   - The `_draw_content` method receives `bounds` centered at origin for easy drawing

### Placing Props

Props are added to `MapElement` containers (rooms, passages):

```python
# Create prop
column = Column((x, y), ColumnType.ROUND)

# Add to room
room.add_prop(column)

# Random placement within container
column.place_random_position(max_attempts=30)
```

### Prop Rotation

Props support 90° rotation increments:

```python
from dungeongen.graphics.rotation import Rotation

column = Column((x, y), ColumnType.SQUARE, rotation=Rotation.ROT_90)
```

The `Rotation` enum provides: `ROT_0`, `ROT_90`, `ROT_180`, `ROT_270`.

## Code Style Guide

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`
- Type hints required for public APIs

### Architecture Rules
- Layout system must not import from map system
- Map system receives layout data via adapter
- Graphics primitives are shared utilities
- Props are self-contained with their own rendering

### Documentation
- All public classes need docstrings
- Complex algorithms need inline comments
- Type hints serve as documentation

### Testing
- Tests live in `/tests/`
- Use pytest
- Test layout generation determinism (same seed = same output)
- Test rendering doesn't crash (visual tests are manual)

## Dependencies

- **skia-python**: Vector graphics rendering (Skia bindings)
- **numpy**: Noise generation, array operations
- **Flask**: Web preview server
- **rich**: Logging with colors

## Inspiration

This project was inspired by [watabou's One Page Dungeon](https://watabou.itch.io/one-page-dungeon) generator. The hand-drawn crosshatch aesthetic and procedural generation concepts draw from that work, though this is a complete Python rewrite with original algorithms.

