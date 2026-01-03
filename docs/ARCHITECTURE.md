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

### 3. Connection Chains

Map elements connect in chains that define traversal:
```
Room → Door → Passage → Door → Room
```

This allows the renderer to:
- Group connected elements into "regions" for flood-fill rendering
- Handle closed doors as region boundaries
- Support exits as terminal elements

### 4. Layered Rendering

The map renders in layers:
1. **Crosshatch background** - The dungeon "walls"
2. **Room shadows** - Drop shadows for depth
3. **Room fills** - The floor areas
4. **Grid** - Optional dot grid overlay
5. **Water** - Procedural water features
6. **Props** - Columns, altars, fountains, etc.
7. **Borders** - Room/passage outlines
8. **Doors** - Door overlays
9. **Text** - Room numbers

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
- `archetype`: CLASSIC, WARREN, TEMPLE, CRYPT, LAIR
- `density`: Controls room spacing (sparse to tight)

### Map System

**`Map`** - Main renderer and element container
- Holds all `MapElement` instances (rooms, passages, doors, exits)
- Manages occupancy grid for prop placement
- Handles water layer generation
- `render(canvas, transform)` - Renders to Skia canvas
- `render_to_png(filename)` / `render_to_svg(filename)` - Convenience methods

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

