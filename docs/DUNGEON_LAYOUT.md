# Dungeon Layout Generation Deep Dive

This document explains how DungeonGen procedurally creates dungeon layouts.

## Overview

The layout generator creates the spatial structure of a dungeon: rooms, passages, doors, stairs, and exits. It operates entirely on an integer grid (one cell = 5 feet in D&D terms) and outputs a data structure that can be rendered or used by game engines.

## Generation Pipeline

```
Phase 1: Room Placement      → Place rooms using symmetry mode
Phase 2: Passage Connection  → Connect rooms via MST
Phase 3: Extra Connections   → Add loops (Jaquaying)
Phase 4: Orphan Rooms        → Connect any isolated rooms
Phase 5: Door Generation     → Place doors at room entrances
Phase 6: Stair Generation    → Add stairs to passages
Phase 7: Exit Generation     → Add dungeon entrances/exits
Phase 8: Archetype Styling   → Apply TEMPLE, CRYPT, etc. tweaks
Phase 9: Room Numbering      → Assign display numbers
Phase 10: Water Features     → Optional water generation
```

## Symmetry Modes

### Bilateral (Mirror)

Creates dungeons with left-right symmetry using a **spine-based** approach:

```
             N
             │
    ┌────────┴────────┐
    │    WEST WING    │    EAST WING    │
    │      ←          SPINE         →   │
    │                 │                 │
    └────────┬────────┘
             │
             S (Entrance)
```

The algorithm:
1. Create a central **spine** of rooms going north-south
2. At each spine room, branch left (west) and right (east)
3. Left and right branches use the **same placement seed** for identical room sizes/shapes
4. Branches use **different termination seeds** for slight asymmetry

```python
def _generate_spine_with_context(dungeon, start_x, start_y, length, ctx, parent_room=None):
    for i in range(actual_length):
        room = create_spine_room()
        
        # Position room adjacent to previous
        if ctx.is_tight and prev_room:
            place_room_adjacent(prev_room, direction, room)
        else:
            position_at_center(room, current_x, current_y)
        
        # Branch perpendicular to spine direction
        if branch_chance < BRANCH_CHANCE:
            # LEFT branch
            left_ctx = ctx.clone(
                direction='west',
                depth=ctx.depth + 1,
                placement_seed=branch_seed,      # Same seed
                termination_seed=left_term_seed  # Different
            )
            generate_spine_with_context(..., left_ctx, parent_room=room)
            
            # RIGHT branch (mirrors left)
            right_ctx = ctx.clone(
                direction='east',
                placement_seed=branch_seed,       # Same seed = same rooms
                termination_seed=right_term_seed
            )
            generate_spine_with_context(..., right_ctx, parent_room=room)
```

### Radial (2-fold and 4-fold) - *Future*

> **Note**: Radial symmetry modes are defined but not fully implemented yet.

The planned approach:
1. Place rooms in one quadrant (or half)
2. Rotate placed rooms 180° (RADIAL_2) or 90°/180°/270° (RADIAL_4)
3. Apply symmetry break chance to skip some rotations

### Asymmetric

Random placement without constraints:
1. Start with base radius around origin
2. Try random positions until room fits
3. Expand search radius on failures

## The Occupancy Grid

The occupancy grid tracks what's at each grid cell during generation.

### Cell Types

```python
class CellType(IntEnum):
    EMPTY = 0       # Available for anything
    ROOM = 1        # Inside a room
    PASSAGE = 2     # Corridor cell
    WALL = 3        # Room perimeter (unused)
    DOOR = 4        # Connection point
    RESERVED = 5    # Buffer zone around rooms
    BLOCKED = 6     # Permanently blocked (corners, exit adjacents)
```

### Why RESERVED?

RESERVED cells form a 1-cell buffer around rooms:

```
     R R R R R        R = RESERVED
     R # # # R        # = ROOM
     R # # # R
     R # # # R
     R R R R R
```

**Purpose**:
- Prevents rooms from touching directly
- Passages can cross ONE reserved cell (to connect to room)
- Pattern `RR` invalid for long passages (prevents hugging walls)

### Why BLOCKED?

BLOCKED cells prevent ugly passage connections:

1. **Room Corners**: Passages entering corners look bad
2. **Round Room Exits**: For circular rooms, cells beside each exit point are blocked to force clean 90° connections

```
Example: Round room with N/S/E/W exits

     B . B        B = BLOCKED beside N exit
     R X R        X = Exit cell
   R R O R R      O = ROOM (circle interior)
   R O O O R
   R R O R R
     R X R        X = Exit cell  
     B . B        B = BLOCKED beside S exit
```

### Passage Validation

When pathfinding for new passages, the grid enforces:

```python
def is_valid_passage_string(cell_string):
    # 'O' = Room cell → INVALID (can't go through rooms)
    # 'B' = Blocked → INVALID (corners, exit adjacents)
    # 'D' = Door → INVALID (existing doors block)
    # 'S' = Stairs → INVALID (stairs block)
    # 'PP' = Two passages → INVALID (can only cross ONE)
    # 'RR' in long passage → INVALID (can't hug walls)
```

## Room Placement

### Tight/Compact Mode (density ≥ 0.8)

Rooms are placed **edge-to-edge** with 1-cell passages:

```python
def _place_room_adjacent(anchor, direction, new_room, dungeon):
    ax, ay = anchor.center_grid
    
    if direction == 'south':
        new_room.x = ax - new_room.width // 2
        new_room.y = anchor.y + anchor.height + 1  # 1 cell gap
        passage_cells = [(ax, anchor.y + anchor.height)]  # Single cell
```

This creates dungeons where rooms nearly touch.

### Normal/Sparse Mode

Rooms placed with configurable spacing:

```python
# Spacing ranges by density
if density >= 0.8: spacing = (1, 2)   # Tight
elif density >= 0.4: spacing = (3, 5)  # Normal
else: spacing = (6, 10)                # Sparse
```

## Passage Generation

### Phase 2: Minimum Spanning Tree

After rooms are placed, connect them minimally:

1. Build **Delaunay triangulation** of room centers
2. Extract **Minimum Spanning Tree** (MST) - ensures all rooms reachable
3. For each MST edge, create a passage

```python
def _connect_rooms(dungeon):
    rooms = list(dungeon.rooms.values())
    points = [room.center_grid for room in rooms]
    
    # Delaunay → all possible connections
    triangulation = delaunay_triangulation(points)
    
    # MST → minimal connected graph
    mst_edges = minimum_spanning_tree(triangulation)
    
    for edge in mst_edges:
        passage = create_passage(rooms[edge[0]], rooms[edge[1]])
        add_validated_passage(dungeon, passage)
```

### Phase 3: Jaquaying (Extra Connections)

Add **loops and alternate paths** beyond the MST. This creates more interesting gameplay:

```python
def _add_extra_connections(dungeon):
    # Get all Delaunay edges not in MST
    extra_edges = delaunay_edges - mst_edges
    
    # Add some based on loop_factor parameter
    for edge in extra_edges:
        if random() < loop_factor:
            # Only add if doesn't create too many connections
            if len(room1.connections) < 3 and len(room2.connections) < 3:
                passage = create_passage(room1, room2)
                add_validated_passage(dungeon, passage)
```

### A* Pathfinding

Passages use A* to find routes around obstacles:

```python
def find_path(start, end, allowed_rooms, max_iterations):
    # State = (position, direction, prev_category)
    # Cost includes: distance + turn penalty + cell penalty
    
    for direction in ['N', 'S', 'E', 'W']:
        neighbor = current + direction_offset
        
        # Check pattern rules
        can_move, category = can_move_to(neighbor, prev_category)
        
        # Penalize turns and non-empty cells
        turn_cost = 0.5 if is_turn else 0
        cell_cost = 0.2 if category in ('R', 'P') else 0
```

## Door Generation

Doors are placed at room-passage boundaries:

```python
def _generate_doors(dungeon):
    for passage in dungeon.passages.values():
        start_room = dungeon.rooms[passage.start_room]
        end_room = dungeon.rooms[passage.end_room]
        
        # Find where passage enters each room
        start_entry = find_entry_point(passage, start_room)
        end_entry = find_entry_point(passage, end_room)
        
        # Create doors at entry points
        for entry in [start_entry, end_entry]:
            door_type = choose_door_type()  # OPEN, CLOSED, SECRET
            door = Door(x=entry.x, y=entry.y, door_type=door_type)
            dungeon.add_door(door)
```

## Archetype Effects

> **Note**: Archetypes are currently **partially implemented**. They add semantic tags to rooms but do not yet modify generation parameters.

### Currently Implemented

| Archetype | Effect |
|-----------|--------|
| **LAIR** | Tags the largest room as 'lair' and 'boss' |
| **TEMPLE** | Tags the most central room as 'sanctum' |

### Planned (Not Yet Implemented)

The following archetypes are defined but have no effect (yet) on generation:

| Archetype | Intended Effect |
|-----------|-----------------|
| **CLASSIC** | Default balanced settings |
| **WARREN** | Smaller rooms, higher density, more loops |
| **CRYPT** | Linear layout, more dead ends |
| **CAVERN** | Irregular shapes, organic passages |
| **FORTRESS** | Regular grid, defensive layout |

To achieve these effects manually, adjust `GenerationParams`:

```python
# Warren-style (dense maze)
params.density = 0.9
params.room_size_bias = -0.8  # Cozy/small rooms
params.loop_factor = 0.5       # More loops

# Crypt-style (linear)
params.linearity = 0.8
params.loop_factor = 0.1       # Few loops

# Temple-style
params.symmetry = SymmetryType.BILATERAL
params.room_size_bias = 0.5    # Larger rooms
```

## Room Numbering

Rooms are numbered using a **branch-cluster algorithm** that assigns contiguous number blocks to each branch at junctions. This produces more intuitive numbering for players exploring the dungeon.

### Algorithm Overview

1. **Start from entrance room** (room #1)
2. **At each junction**, order exits **clockwise** from the incoming direction
3. **Process each branch as a cluster** - all rooms in a branch get contiguous numbers before moving to the next branch
4. **Spine direction priority** - the spine continuation (straight ahead) is numbered before side branches

### Why Clockwise Clustering?

Simple BFS/DFS would interleave rooms from different branches:
```
BFS: 1 → 2,3,4 → 5,6,7...  (mixed branches)
```

Branch-cluster keeps branches together:
```
Branch-cluster: 1 → 2,3,4 (left branch) → 5,6 (right branch) → 7,8,9 (spine)
```

This matches how players typically explore - finishing one area before moving to the next.

### Implementation

```python
class _DungeonNumberer:
    def _process_junction_room(self, u, parent):
        # Order exits clockwise from incoming direction
        exits = self._ordered_exits(u, parent)
        
        for v in exits:
            if v in self.visited:
                continue
            
            # Find all rooms reachable through v (blocking u)
            component = self._component_without_node(v, blocked=u)
            
            # Number entire branch as contiguous cluster
            self._number_component_clustered(root=u, entry=v, component=component)
    
    def _sort_by_clockwise(self, u, parent, neighbors):
        # Reference direction: from parent→u, or spine direction at entrance
        if parent:
            ref_dir = normalize(u_pos - parent_pos)
        else:
            ref_dir = self.spine_direction  # (0, 1) for south-going spine
        
        # Sort by clockwise angle from reference
        return sorted(neighbors, key=lambda v: clockwise_angle(ref_dir, u→v))
```

### Spine Direction

For symmetric spine layouts, the spine direction (typically south) determines which branch is numbered first. The room straight ahead along the spine gets priority over side branches.

## Output Data Structure

```python
@dataclass
class Dungeon:
    rooms: Dict[str, Room]           # room_id → Room
    passages: Dict[str, Passage]     # passage_id → Passage
    doors: Dict[str, Door]           # door_id → Door
    stairs: Dict[str, Stair]         # stair_id → Stair
    exits: Dict[str, Exit]           # exit_id → Exit
    seed: int                        # Generation seed
    bounds: Tuple[int, int, int, int]  # (x, y, width, height)
    mirror_pairs: Dict[str, str]     # room_id → mirrored_room_id
    spine_start_room: Optional[str]  # Entrance room for spine layouts
```

## Determinism

Using the same seed produces identical dungeons:

```python
generator = DungeonGenerator(params)
dungeon1 = generator.generate(seed=42)
dungeon2 = generator.generate(seed=42)
assert dungeon1.rooms == dungeon2.rooms  # Identical
```

This is achieved by:
- Seeding all RNG instances
- Processing in deterministic order
- Separating placement and termination seeds for symmetry

