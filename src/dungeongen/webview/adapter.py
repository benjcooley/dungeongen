"""
Adapter to convert layout output to dungeongen renderer format.

Key constraints in dungeongen:
- Passages cannot overlap doors or other passages
- Crossing passages must be split into multiple non-crossing segments
- Elements connect in chains: room -> door -> passage -> door -> room
- At crossing points, all meeting passage segments connect to each other
"""
from typing import Optional, Dict, Tuple, List, Set
from collections import defaultdict

from dungeongen.layout import Dungeon, Room as LayoutRoom, Passage as LayoutPassage, Door as LayoutDoor
from dungeongen.layout import RoomShape, DoorType as LayoutDoorType, Exit as LayoutExit, Stair as LayoutStair


def convert_dungeon(layout_dungeon: Dungeon, water_depth: float = 0.0, 
                    water_scale: float = 0.016, water_res: float = 0.3,
                    water_stroke: float = 3.0, water_ripple: float = 12.0,
                    show_numbers: bool = True) -> 'Map':
    """Convert a dungeonlayout Dungeon to a dungeongen Map.
    
    Args:
        layout_dungeon: The dungeonlayout Dungeon to convert
        water_depth: Water depth level (0 = dry, use WaterDepth constants)
        water_scale: Noise scale for water features (larger = larger blobs)
        water_res: Resolution scale for water (smaller = faster, coarser)
        water_stroke: Shoreline stroke width
        water_ripple: Ripple inset distance
        show_numbers: Whether to display room numbers
    """
    from dungeongen.map.map import Map
    from dungeongen.map.room import Room
    from dungeongen.options import Options
    
    options = Options()
    dungeon_map = Map(options)
    
    # Set water if enabled
    if water_depth > 0:
        dungeon_map.set_water(
            water_depth, 
            seed=layout_dungeon.seed,
            lf_scale=water_scale,
            resolution_scale=water_res,
            stroke_width=water_stroke,
            ripple_inset=water_ripple
        )
    
    # Calculate offset to normalize coordinates
    bounds = layout_dungeon.bounds
    offset_x = -bounds[0]
    offset_y = -bounds[1]
    
    # Track mappings
    room_map: Dict[str, Room] = {}
    
    # Get symmetry info for prop decoration
    mirror_pairs = layout_dungeon.mirror_pairs
    spine_direction = layout_dungeon.spine_direction
    props_seed = layout_dungeon.props_seed
    
    # Calculate spine axis position for determining room orientation
    # For bilateral symmetry, spine is at x=0 in layout coords
    spine_axis_x = 0
    
    # Convert rooms first
    for room_id, layout_room in layout_dungeon.rooms.items():
        room = _convert_room(layout_room, dungeon_map, offset_x, offset_y, show_numbers)
        if room:
            room_map[room_id] = room
            
            # For symmetric props, use consistent seed for mirror pairs
            # Use the lower room_id of the pair so both get the same seed
            if room_id in mirror_pairs:
                mirror_id = mirror_pairs[room_id]
                base_id = min(room_id, mirror_id)  # Use lower ID for consistency
            else:
                base_id = room_id
            
            # Create deterministic seed from props_seed and room base_id
            room_seed = hash((props_seed, base_id)) & 0x7FFFFFFF
            
            # Determine room's orientation relative to spine
            # For bilateral (mirror) symmetry with vertical spine:
            # - Rooms left of spine: toward_spine = 'east'
            # - Rooms right of spine: toward_spine = 'west'  
            # - Rooms on spine: toward_spine = spine_direction (use global)
            room_center_x = layout_room.x + layout_room.width / 2
            
            if room_center_x < spine_axis_x - 1:
                # Room is to the left of spine
                room_orientation = 'east'  # Toward spine is east
            elif room_center_x > spine_axis_x + 1:
                # Room is to the right of spine
                room_orientation = 'west'  # Toward spine is west
            else:
                # Room is on the spine - use spine grow direction
                room_orientation = spine_direction
            
            # Decorate room with props (columns, altars, dais, rocks)
            # Same seed + opposite orientation = mirrored decorations
            _decorate_room(room, room_seed, room_orientation)
    
    # Build door lookup by position
    door_at_pos: Dict[Tuple[int, int], LayoutDoor] = {}
    for door_id, layout_door in layout_dungeon.doors.items():
        pos = (layout_door.x + offset_x, layout_door.y + offset_y)
        door_at_pos[pos] = layout_door
    
    # Build exit lookup by position (need this BEFORE passages)
    exit_at_pos: Dict[Tuple[int, int], LayoutExit] = {}
    for exit_id, layout_exit in layout_dungeon.exits.items():
        pos = (layout_exit.x + offset_x, layout_exit.y + offset_y)
        exit_at_pos[pos] = layout_exit
    
    # Build a map of all passage cells to find crossings
    passage_cells: Dict[Tuple[int, int], List[str]] = defaultdict(list)
    
    for passage_id, layout_passage in layout_dungeon.passages.items():
        waypoints = layout_passage.waypoints
        if not waypoints or len(waypoints) < 2:
            continue
        # Get all cells this passage occupies
        grid_points = [(int(x) + offset_x, int(y) + offset_y) for x, y in waypoints]
        full_path = _expand_to_full_path(grid_points)
        for cell in full_path:
            passage_cells[cell].append(passage_id)
    
    # Find crossing points (cells where multiple passages meet)
    crossing_points: Set[Tuple[int, int]] = set()
    for cell, pids in passage_cells.items():
        if len(pids) > 1:
            crossing_points.add(cell)
    
    # Convert passages, splitting at crossing points
    # Pass exit positions so passages can exclude exit cells (like they exclude door cells)
    all_segments: List['Passage'] = []
    crossing_segments: Dict[Tuple[int, int], List['Passage']] = defaultdict(list)
    
    for passage_id, layout_passage in layout_dungeon.passages.items():
        segments = _convert_passage(
            layout_passage,
            door_at_pos,
            exit_at_pos,  # NEW: pass exit positions
            crossing_points,
            dungeon_map,
            room_map,
            offset_x,
            offset_y
        )
        all_segments.extend(segments)
        
        # Track which segments meet at each crossing
        for seg in segments:
            for cell in crossing_points:
                if cell in seg.grid_points:
                    crossing_segments[cell].append(seg)
    
    # Connect segments at crossing points
    for cell, segs in crossing_segments.items():
        for i, s1 in enumerate(segs):
            for s2 in segs[i+1:]:
                if s1 != s2:
                    s1.connect_to(s2)
    
    # Convert exits (dungeon entrances/exits) and track by position
    exit_map: Dict[Tuple[int, int], 'Exit'] = {}
    for exit_id, layout_exit in layout_dungeon.exits.items():
        exit_elem = _convert_exit(layout_exit, dungeon_map, room_map, offset_x, offset_y)
        if exit_elem:
            exit_pos = (layout_exit.x + offset_x, layout_exit.y + offset_y)
            exit_map[exit_pos] = exit_elem
    
    # Connect passages to exits at their endpoints
    # The passage should END one cell before the exit (exit cell excluded from passage)
    # So we check the cell ADJACENT to the passage endpoint
    for seg in all_segments:
        if hasattr(seg, 'grid_points') and seg.grid_points:
            # Check if an exit is adjacent to start point
            start_pos = seg.grid_points[0]
            for adj in _adjacent_cells(start_pos):
                if adj in exit_map:
                    seg.connect_to(exit_map[adj])
            # Check if an exit is adjacent to end point
            end_pos = seg.grid_points[-1]
            for adj in _adjacent_cells(end_pos):
                if adj in exit_map:
                    seg.connect_to(exit_map[adj])
    
    # Convert stairs
    for stair_id, layout_stair in layout_dungeon.stairs.items():
        _convert_stair(layout_stair, dungeon_map, offset_x, offset_y)
    
    return dungeon_map


def _adjacent_cells(pos: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Return the 4 adjacent cells to a position."""
    x, y = pos
    return [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]


def _convert_room(layout_room: LayoutRoom, dungeon_map: 'Map', offset_x: int, offset_y: int, 
                  show_numbers: bool = True) -> Optional['Room']:
    """Convert a layout room to a dungeongen room."""
    from dungeongen.map.room import Room, RoomType
    
    room_type = RoomType.CIRCULAR if layout_room.shape == RoomShape.CIRCLE else RoomType.RECTANGULAR
    
    room = Room.from_grid(
        grid_x=layout_room.x + offset_x,
        grid_y=layout_room.y + offset_y,
        grid_width=layout_room.width,
        grid_height=layout_room.height,
        room_type=room_type,
        number=layout_room.number if show_numbers else 0
    )
    
    dungeon_map.add_element(room)
    return room


def _convert_exit(layout_exit: LayoutExit, dungeon_map: 'Map', room_map: Dict[str, 'Room'], 
                  offset_x: int, offset_y: int) -> Optional['Exit']:
    """Convert a layout exit to a dungeongen Exit element."""
    from dungeongen.map.exit import Exit
    from dungeongen.map.enums import RoomDirection
    
    # Map direction string to RoomDirection enum
    dir_map = {
        'north': RoomDirection.NORTH,
        'south': RoomDirection.SOUTH,
        'east': RoomDirection.EAST,
        'west': RoomDirection.WEST
    }
    
    direction = dir_map.get(layout_exit.direction, RoomDirection.NORTH)
    
    # Create exit at the position (adjusted by offset)
    exit_elem = Exit.from_grid(
        grid_x=layout_exit.x + offset_x,
        grid_y=layout_exit.y + offset_y,
        direction=direction
    )
    
    dungeon_map.add_element(exit_elem)
    
    # Connect to the room if we have one
    if layout_exit.room_id and layout_exit.room_id in room_map:
        room = room_map[layout_exit.room_id]
        room.connect_to(exit_elem)
    
    return exit_elem


def _convert_passage(
    layout_passage: LayoutPassage,
    door_at_pos: Dict[Tuple[int, int], LayoutDoor],
    exit_at_pos: Dict[Tuple[int, int], LayoutExit],
    crossing_points: Set[Tuple[int, int]],
    dungeon_map: 'Map',
    room_map: Dict[str, 'Room'],
    offset_x: int,
    offset_y: int
) -> List['Passage']:
    """Convert a passage, splitting at crossing points if needed.
    
    Passages exclude cells occupied by doors or exits - those elements
    handle their own floor rendering (door chips, exit chips).
    """
    from dungeongen.map.passage import Passage
    from dungeongen.map.door import Door, DoorType, DoorOrientation
    from dungeongen.map.enums import RoomDirection
    
    waypoints = layout_passage.waypoints
    if not waypoints or len(waypoints) < 2:
        return []
    
    # Convert waypoints with offset
    grid_points = [(int(x) + offset_x, int(y) + offset_y) for x, y in waypoints]
    
    # Get full path (all cells, not just corners)
    full_path = _expand_to_full_path(grid_points)
    
    # Get rooms
    start_room = room_map.get(layout_passage.start_room) if layout_passage.start_room else None
    end_room = room_map.get(layout_passage.end_room) if layout_passage.end_room else None
    
    # Check for doors at start/end of passage
    start_door_layout = door_at_pos.get(full_path[0])
    end_door_layout = door_at_pos.get(full_path[-1])
    
    # Check for exits at start/end of passage
    # Exits are like doors - they have their own floor chip, so exclude from passage
    start_exit = exit_at_pos.get(full_path[0])
    end_exit = exit_at_pos.get(full_path[-1])
    
    # Find split indices (crossing points in the middle of the path)
    split_indices = []
    for i, cell in enumerate(full_path):
        if cell in crossing_points and 0 < i < len(full_path) - 1:
            split_indices.append(i)
    
    # If no splits, create single passage with doors/exits
    if not split_indices:
        return _create_passage_with_doors(
            full_path, start_room, end_room,
            start_door_layout, end_door_layout,
            start_exit, end_exit,  # NEW: pass exit info
            dungeon_map, offset_x, offset_y
        )
    
    # Split at crossings
    segments = []
    boundaries = [0] + split_indices + [len(full_path) - 1]
    
    for i in range(len(boundaries) - 1):
        seg_start = boundaries[i]
        seg_end = boundaries[i + 1]
        
        seg_path = full_path[seg_start:seg_end + 1]
        if len(seg_path) < 2:
            continue
        
        # Determine room connections for this segment
        is_first = (seg_start == 0)
        is_last = (seg_end == len(full_path) - 1)
        
        seg_start_room = start_room if is_first else None
        seg_end_room = end_room if is_last else None
        seg_start_door = start_door_layout if is_first else None
        seg_end_door = end_door_layout if is_last else None
        seg_start_exit = start_exit if is_first else None
        seg_end_exit = end_exit if is_last else None
        
        # Pass the full segment path - _create_passage_with_doors will simplify it
        seg_passages = _create_passage_with_doors(
            seg_path, seg_start_room, seg_end_room,
            seg_start_door, seg_end_door,
            seg_start_exit, seg_end_exit,  # NEW: pass exit info
            dungeon_map, offset_x, offset_y
        )
        segments.extend(seg_passages)
    
    return segments


def _create_passage_with_doors(
    path: List[Tuple[int, int]],
    start_room: Optional['Room'],
    end_room: Optional['Room'],
    start_door_layout: Optional[LayoutDoor],
    end_door_layout: Optional[LayoutDoor],
    start_exit: Optional[LayoutExit],
    end_exit: Optional[LayoutExit],
    dungeon_map: 'Map',
    offset_x: int,
    offset_y: int
) -> List['Passage']:
    """Create a passage with doors/exits at its ends if applicable.
    
    Key rules for dungeongen:
    - Door IS a passage element with open/closed state
    - Exit is like a one-sided door - has its own floor chip
    - Passages should NOT include door/exit cells - those elements render their own floors
    - For short connections (1-2 cells with door), just use the Door as the passage
    - For longer passages: room -> door -> passage -> door -> room
    """
    from dungeongen.map.passage import Passage
    from dungeongen.map.enums import RoomDirection
    
    if len(path) < 1:
        return []
    
    # Handle single-point passages (where start == end)
    if len(path) == 1:
        from dungeongen.map.passage import Passage
        from dungeongen.map.enums import RoomDirection
        
        # Determine direction based on room positions
        if start_room and end_room:
            sr_bounds = start_room.bounds
            er_bounds = end_room.bounds
            sr_cx = sr_bounds.x + sr_bounds.width / 2
            er_cx = er_bounds.x + er_bounds.width / 2
            if abs(er_cx - sr_cx) > abs((er_bounds.y + er_bounds.height/2) - (sr_bounds.y + sr_bounds.height/2)):
                direction = RoomDirection.EAST if er_cx > sr_cx else RoomDirection.WEST
            else:
                direction = RoomDirection.SOUTH if (er_bounds.y + er_bounds.height/2) > (sr_bounds.y + sr_bounds.height/2) else RoomDirection.NORTH
        else:
            direction = RoomDirection.EAST  # Default
        
        door_layout = start_door_layout or end_door_layout
        elements = []
        if start_room:
            elements.append(start_room)
        
        if door_layout:
            # Create door as the passage
            door = _create_door(path[0], direction, door_layout.door_type, dungeon_map)
            if door:
                elements.append(door)
        else:
            # Create single-point passage (no door)
            try:
                passage = Passage(
                    grid_points=[path[0], path[0]],
                    start_direction=direction,
                    end_direction=direction.get_opposite(),
                    allow_dead_end=(start_room is None and end_room is None)
                )
                dungeon_map.add_element(passage)
                elements.append(passage)
            except ValueError as e:
                print(f"Warning: Could not create single-point passage: {e}")
        
        if end_room:
            elements.append(end_room)
        
        # Connect
        for i in range(len(elements) - 1):
            elements[i].connect_to(elements[i + 1])
        return []
    
    working_path = list(path)
    elements = []
    passages_created = []
    
    # Get directions based on the full path (handle 1-cell case)
    if len(path) >= 2:
        start_dir = _direction_from_points(path[0], path[1])
        end_dir = _direction_from_points(path[-1], path[-2])
    else:
        # Single point - determine direction from rooms if available
        start_dir = RoomDirection.EAST  # Default
        end_dir = RoomDirection.WEST
        if start_room and end_room:
            sr_bounds = start_room.bounds
            er_bounds = end_room.bounds
            sr_cx = sr_bounds.x + sr_bounds.width / 2
            er_cx = er_bounds.x + er_bounds.width / 2
            sr_cy = sr_bounds.y + sr_bounds.height / 2
            er_cy = er_bounds.y + er_bounds.height / 2
            if abs(er_cx - sr_cx) > abs(er_cy - sr_cy):
                start_dir = RoomDirection.EAST if er_cx > sr_cx else RoomDirection.WEST
                end_dir = start_dir.get_opposite()
            else:
                start_dir = RoomDirection.SOUTH if er_cy > sr_cy else RoomDirection.NORTH
                end_dir = start_dir.get_opposite()
    
    # Add start room
    if start_room:
        elements.append(start_room)
    
    # Handle doors - Door IS the passage element for that cell
    start_door = None
    end_door = None
    
    # Create start door if present - this IS the passage for that cell
    if start_door_layout and len(working_path) >= 1:
        start_door = _create_door(working_path[0], start_dir, start_door_layout.door_type, dungeon_map)
        if start_door:
            elements.append(start_door)
            working_path = working_path[1:]  # Door covers this cell
    
    # Create end door if present - this IS the passage for that cell
    # But only if it's a different cell than the start door
    if end_door_layout and len(working_path) >= 1:
        end_door = _create_door(path[-1], end_dir, end_door_layout.door_type, dungeon_map)
        if end_door:
            working_path = working_path[:-1]  # Door covers this cell
    
    # Handle exits - Exit has its own floor chip, so exclude from passage
    if start_exit and len(working_path) >= 1:
        working_path = working_path[1:]
    if end_exit and len(working_path) >= 1:
        working_path = working_path[:-1]
    
    # Create passage for remaining cells (0+ cells is fine - may have no passage if all covered by doors)
    passage = None
    if len(working_path) >= 2:
        # Multi-cell passage - simplify to corners
        simplified = _simplify_path(working_path)
        if len(simplified) >= 2:
            new_start_dir = _direction_from_points(simplified[0], simplified[1])
            new_end_dir = _direction_from_points(simplified[-1], simplified[-2])
            
            try:
                passage = Passage(
                    grid_points=simplified,
                    start_direction=new_start_dir,
                    end_direction=new_end_dir,
                    allow_dead_end=(start_room is None and end_room is None)
                )
                dungeon_map.add_element(passage)
                elements.append(passage)
                passages_created.append(passage)
            except ValueError as e:
                print(f"Warning: Could not create passage: {e}")
    elif len(working_path) == 1:
        # Single-cell passage
        cell = working_path[0]
        try:
            passage = Passage(
                grid_points=[cell, cell],
                start_direction=start_dir,
                end_direction=end_dir,
                allow_dead_end=(start_room is None and end_room is None)
            )
            dungeon_map.add_element(passage)
            elements.append(passage)
            passages_created.append(passage)
        except ValueError as e:
            print(f"Warning: Could not create single-cell passage: {e}")
    # len(working_path) == 0: No passage needed - doors/exits cover all cells
    
    # Add end door (must come after passage in the chain)
    if end_door:
        elements.append(end_door)
    
    # Add end room
    if end_room:
        elements.append(end_room)
    
    # Connect the chain of elements: room -> door -> passage -> door -> room
    for i in range(len(elements) - 1):
        elements[i].connect_to(elements[i + 1])
    
    return passages_created


def _expand_to_full_path(grid_points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Expand corner points to full path including all intermediate cells."""
    if len(grid_points) < 2:
        return list(grid_points)
    
    full_path = [grid_points[0]]
    
    for i in range(len(grid_points) - 1):
        x1, y1 = grid_points[i]
        x2, y2 = grid_points[i + 1]
        
        dx = 1 if x2 > x1 else (-1 if x2 < x1 else 0)
        dy = 1 if y2 > y1 else (-1 if y2 < y1 else 0)
        
        x, y = x1, y1
        while (x, y) != (x2, y2):
            x += dx
            y += dy
            full_path.append((x, y))
    
    return full_path


def _simplify_path(full_path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Simplify a full path to just corner points."""
    if len(full_path) <= 2:
        return list(full_path)
    
    result = [full_path[0]]
    
    for i in range(1, len(full_path) - 1):
        prev = full_path[i - 1]
        curr = full_path[i]
        next_pt = full_path[i + 1]
        
        dx1, dy1 = curr[0] - prev[0], curr[1] - prev[1]
        dx2, dy2 = next_pt[0] - curr[0], next_pt[1] - curr[1]
        
        if (dx1, dy1) != (dx2, dy2):
            result.append(curr)
    
    result.append(full_path[-1])
    return result


def _create_door(
    point: Tuple[int, int],
    passage_dir: 'RoomDirection',
    layout_door_type: LayoutDoorType,
    dungeon_map: 'Map'
) -> Optional['Door']:
    """Create a door at a grid point."""
    from dungeongen.map.door import Door, DoorType, DoorOrientation
    from dungeongen.map.enums import RoomDirection
    
    door_type = DoorType.OPEN if layout_door_type in (LayoutDoorType.OPEN, LayoutDoorType.SECRET) else DoorType.CLOSED
    
    # Door orientation based on passage direction
    orientation = DoorOrientation.HORIZONTAL if passage_dir in (RoomDirection.EAST, RoomDirection.WEST) else DoorOrientation.VERTICAL
    
    try:
        door = Door.from_grid(point[0], point[1], orientation, door_type)
        dungeon_map.add_element(door)
        return door
    except Exception as e:
        print(f"Warning: Could not create door at {point}: {e}")
        return None


def _direction_from_points(p1: Tuple[int, int], p2: Tuple[int, int]) -> 'RoomDirection':
    """Get direction from p1 to p2."""
    from dungeongen.map.enums import RoomDirection
    
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    if abs(dx) > abs(dy):
        return RoomDirection.EAST if dx > 0 else RoomDirection.WEST
    return RoomDirection.SOUTH if dy > 0 else RoomDirection.NORTH


def _convert_stair(layout_stair: LayoutStair, dungeon_map: 'Map', offset_x: int, offset_y: int) -> None:
    """Convert a layout stair to a dungeongen StairsProp and add it to a passage."""
    from dungeongen.map.props import StairsProp
    from dungeongen.graphics.rotation import Rotation
    from dungeongen.constants import CELL_SIZE
    
    # Map direction string to Rotation
    # The stairs point in the direction they ascend
    dir_map = {
        'north': Rotation.ROT_0,    # Steps go up toward north
        'south': Rotation.ROT_180,  # Steps go up toward south
        'east': Rotation.ROT_90,    # Steps go up toward east
        'west': Rotation.ROT_270    # Steps go up toward west
    }
    
    rotation = dir_map.get(layout_stair.direction, Rotation.ROT_0)
    
    # Grid position with offset
    grid_x = layout_stair.x + offset_x
    grid_y = layout_stair.y + offset_y
    
    # Create stairs prop at the grid position (position is top-left of cell)
    stairs_prop = StairsProp.at_grid(grid_x, grid_y, rotation)
    
    # Find a passage that contains this grid cell and add stairs as a prop
    map_x = grid_x * CELL_SIZE + CELL_SIZE / 2  # Center of cell
    map_y = grid_y * CELL_SIZE + CELL_SIZE / 2
    
    # Try to find the passage at this location
    for passage in dungeon_map.passages:
        if passage.shape.contains(map_x, map_y):
            passage.add_prop(stairs_prop)
            return
    
    # Fallback: try rooms (stairs might be in a room entrance)
    for room in dungeon_map.rooms:
        if room.shape.contains(map_x, map_y):
            room.add_prop(stairs_prop)
            return
    
    # Last resort: add to first passage if we couldn't find a match
    passages = list(dungeon_map.passages)
    if passages:
        passages[0].add_prop(stairs_prop)


def _decorate_room(room: 'Room', seed: int, toward_spine: str) -> None:
    """Decorate a room with props based on seed and orientation.
    
    Same seed + opposite toward_spine = mirrored decorations for symmetric rooms.
    
    Args:
        room: The dungeongen Room to decorate
        seed: Random seed for reproducible decoration (same seed = same choices)
        toward_spine: Direction toward the spine/center ('north', 'south', 'east', 'west')
    """
    import random
    from dungeongen.constants import CELL_SIZE
    from dungeongen.map.enums import Direction
    from dungeongen.map.props import ColumnType, Altar, Dias, Fountain
    from dungeongen.map.arrange import ColumnArrangement, arrange_columns, arrange_random_props, PropType
    from dungeongen.map.room import RoomType
    
    rng = random.Random(seed)
    
    # Calculate room dimensions
    room_width = int(room.bounds.width / CELL_SIZE)
    room_height = int(room.bounds.height / CELL_SIZE)
    room_area = room_width * room_height
    
    # Columns perpendicular to toward_spine for symmetric alignment
    # east/west toward_spine -> vertical columns, north/south -> horizontal
    if toward_spine in ('east', 'west'):
        preferred_arrangement = ColumnArrangement.VERTICAL_ROWS
    else:
        preferred_arrangement = ColumnArrangement.HORIZONTAL_ROWS
    
    # Dais goes on wall AWAY from spine (opposite of toward_spine)
    dais_wall = {
        'north': Direction.SOUTH,
        'south': Direction.NORTH,
        'east': Direction.WEST,
        'west': Direction.EAST
    }.get(toward_spine, Direction.NORTH)
    
    # Add columns for rooms larger than 3x3
    column_chance = 0.4 if room.room_type != RoomType.RECTANGULAR else 0.2
    if rng.random() < column_chance and room_area > 9:
        if room.room_type == RoomType.RECTANGULAR:
            # Use preferred arrangement more often for symmetry
            weights = [1, 1, 1, 1]
            if preferred_arrangement == ColumnArrangement.VERTICAL_ROWS:
                weights = [1, 4, 1, 1]  # Prefer vertical
            else:
                weights = [4, 1, 1, 1]  # Prefer horizontal
            arrangement = rng.choices(
                [ColumnArrangement.HORIZONTAL_ROWS,
                 ColumnArrangement.VERTICAL_ROWS,
                 ColumnArrangement.CIRCLE,
                 ColumnArrangement.GRID],
                weights=weights
            )[0]
        else:
            arrangement = ColumnArrangement.CIRCLE
        
        column_type = ColumnType.SQUARE if rng.random() < 0.5 else ColumnType.ROUND
        arrange_columns(room, arrangement, column_type=column_type)
    
    # Dais placement - prefer wall opposite spine direction
    if room.room_type == RoomType.RECTANGULAR:
        candidate_walls = []
        
        if room_width % 2 == 1 and room_width >= 3:
            candidate_walls.append((Direction.NORTH, room_width))
            candidate_walls.append((Direction.SOUTH, room_width))
        if room_height % 2 == 1 and room_height >= 3:
            candidate_walls.append((Direction.EAST, room_height))
            candidate_walls.append((Direction.WEST, room_height))
        
        # Sort: prefer dais_wall first, then by length (shorter preferred)
        def wall_priority(w):
            wall, length = w
            is_preferred = 1 if wall == dais_wall else 0
            return (-is_preferred, length)
        
        candidate_walls.sort(key=wall_priority)
        
        if candidate_walls and rng.random() < 0.2:
            wall, _ = candidate_walls[0]
            
            center_x = room.bounds.left + room.bounds.width / 2
            center_y = room.bounds.top + room.bounds.height / 2
            
            if wall == Direction.NORTH:
                dias = Dias.on_wall('north', center_x, room.bounds.top)
            elif wall == Direction.SOUTH:
                dias = Dias.on_wall('south', center_x, room.bounds.bottom)
            elif wall == Direction.EAST:
                dias = Dias.on_wall('east', room.bounds.right, center_y)
            else:
                dias = Dias.on_wall('west', room.bounds.left, center_y)
            
            room.add_prop(dias)
            
            if rng.random() < 0.5:
                altar = Altar(dias.placement_point)
                room.add_prop(altar)
    
    # Fountain in center of larger rooms
    if room_area > 16 and rng.random() < 0.10:
        center_x = room.bounds.left + room.bounds.width / 2
        center_y = room.bounds.top + room.bounds.height / 2
        fountain = Fountain.create(center_x, center_y)
        room.add_prop(fountain)
    
    # Random altars
    altar_roll = rng.random()
    if altar_roll < 0.05:
        arrange_random_props(room, [PropType.ALTAR], min_count=1, max_count=1)
    elif altar_roll < 0.07:
        arrange_random_props(room, [PropType.ALTAR], min_count=2, max_count=2)
    
    # Add rocks
    arrange_random_props(room, [PropType.SMALL_ROCK], min_count=0, max_count=5)
    arrange_random_props(room, [PropType.MEDIUM_ROCK], min_count=0, max_count=3)


def render_dungeon_to_png(layout_dungeon: Dungeon, output_path: str = 'dungeon_output.png',
                          canvas_width: int = 1200, canvas_height: int = 1200) -> None:
    """Render a dungeonlayout Dungeon to PNG using dungeongen."""
    import skia
    
    dungeon_map = convert_dungeon(layout_dungeon)
    
    surface = skia.Surface(canvas_width, canvas_height)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color(255, 255, 255))
    
    transform = dungeon_map._calculate_default_transform(canvas_width, canvas_height)
    dungeon_map.render(canvas, transform)
    
    image = surface.makeImageSnapshot()
    image.save(output_path, skia.kPNG)
    print(f"Rendered dungeon to {output_path}")


if __name__ == "__main__":
    from dungeongen.layout import DungeonGenerator, GenerationParams, DungeonSize, SymmetryType
    
    params = GenerationParams()
    params.size = DungeonSize.SMALL
    params.symmetry = SymmetryType.BILATERAL
    
    generator = DungeonGenerator(params)
    dungeon = generator.generate(seed=42)
    
    print(f"Generated: {len(dungeon.rooms)} rooms, {len(dungeon.passages)} passages")
    render_dungeon_to_png(dungeon, 'dungeon_rendered.png')
