"""Main dungeon generation orchestrator."""
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Set
from .models import Room, Passage, Dungeon, RoomShape, PassageStyle, Door, DoorType, Stair, StairDirection, Exit, ExitType, WaterRegion
from .params import GenerationParams, DungeonSize, SymmetryType, DungeonArchetype, ROOM_TEMPLATES
from .spatial import Point, Rect, SpatialHash, delaunay_triangulation, minimum_spanning_tree
from .occupancy import OccupancyGrid, PassageModifier, CellType
from .numbering import number_dungeon


@dataclass
class GenerationContext:
    """
    Context passed through recursive generation.
    Can be cloned and modified at each recursion level.
    """
    # Packing mode: 'tight' (adjacent), 'normal', 'sparse'
    packing: str = 'normal'
    
    # Passage length for tight mode (1 = rooms almost touching)
    passage_length: int = 1
    
    # Current recursion depth
    depth: int = 0
    max_depth: int = 3
    
    # Seeds for deterministic generation
    placement_seed: int = 0
    termination_seed: int = 0
    
    # Direction of current spine
    direction: str = 'south'
    
    # Room templates and sizes available
    templates: List = field(default_factory=list)
    circle_radii: List = field(default_factory=list)
    
    # Spacing range (min, max) for non-tight modes
    spacing_range: Tuple[int, int] = (3, 5)
    
    def clone(self, **overrides) -> 'GenerationContext':
        """Create a copy with optional overrides."""
        import copy
        ctx = copy.copy(self)
        for key, value in overrides.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
        return ctx
    
    @property
    def is_tight(self) -> bool:
        """Check if using tight/compact packing."""
        return self.packing == 'tight'
    
    def get_spacing(self, rng: random.Random) -> int:
        """Get spacing for current packing mode."""
        if self.is_tight:
            return self.passage_length
        return rng.randint(self.spacing_range[0], self.spacing_range[1])


class DungeonGenerator:
    """Generates dungeon layouts based on parameters."""
    
    # Don't allow additional connections if existing connection is longer than this
    MAX_CONNECTION_LENGTH_FOR_EXTRA = 3
    
    def __init__(self, params: Optional[GenerationParams] = None):
        self.params = params or GenerationParams()
        self.rng = random.Random()
        self.occupancy = OccupancyGrid()
        # Track connected room pairs: {(room_id1, room_id2): passage_length}
        self._connected_pairs: dict = {}
    
    def _create_context(self) -> GenerationContext:
        """Create initial generation context from params."""
        # Determine packing mode from density
        if self.params.density >= 0.8:
            packing = 'tight'
            spacing_range = (1, 2)
        elif self.params.density >= 0.4:
            packing = 'normal'
            spacing_range = (3, 5)
        else:
            packing = 'sparse'
            spacing_range = (6, 10)
        
        return GenerationContext(
            packing=packing,
            passage_length=1,  # 1-cell passages for tight mode
            spacing_range=spacing_range,
            templates=self.params.get_room_templates(),
            circle_radii=self.params.get_circle_radii(),
            placement_seed=self.rng.randint(0, 2**31),
            termination_seed=self.rng.randint(0, 2**31),
        )
        
    def generate(self, seed: Optional[int] = None) -> Dungeon:
        """Generate a complete dungeon."""
        # Set up RNG
        if seed is not None:
            self.rng.seed(seed)
        elif self.params.seed is not None:
            self.rng.seed(self.params.seed)
        else:
            seed = random.randint(0, 2**31)
            self.rng.seed(seed)
        
        dungeon = Dungeon(seed=seed or 0)
        self.occupancy.clear()
        self._connected_pairs = {}  # Reset connection tracking
        self._mirror_pairs = {}  # Reset mirror pair tracking
        self._mirror_axis_x = 0  # Mirror axis
        
        # Phase 1: Generate and place rooms incrementally
        # Each room is placed and immediately marked in the occupancy grid
        self._place_rooms_incrementally(dungeon)
        
        # Phase 2: Connect rooms with passages (using occupancy for collision avoidance)
        # Passages are validated and added by _add_validated_passage during connection
        self._connect_rooms(dungeon)
        
        # Phase 3: Second pass - add extra connections (Jaquaying)
        # Passages are validated and added by _add_validated_passage during connection
        self._add_extra_connections(dungeon)
        
        # Phase 4: Connect orphan rooms (rooms with no passages)
        self._connect_orphan_rooms(dungeon)
        
        # Phase 5: Detect crossings and prune redundant passages
        # NOTE: Disabled for now - serendipitous crossings are advantageous
        # self._prune_redundant_crossings(dungeon)
        
        # Phase 6: Generate doors at room entrances
        self._generate_doors(dungeon)
        
        # Phase 7: Generate stairs in passages
        self._generate_stairs(dungeon)
        
        # Phase 8: Generate dungeon exits/entrances
        self._generate_exits(dungeon)
        
        # Phase 9: Apply archetype-specific adjustments
        self._apply_archetype(dungeon)
        
        # Phase 10: Number rooms using branch-cluster algorithm
        self._number_rooms(dungeon)
        
        # Phase 11: Copy symmetry info to dungeon for prop decoration
        dungeon.mirror_pairs = dict(self._mirror_pairs)
        dungeon.spine_direction = getattr(self, '_spine_direction', 'south')
        dungeon.props_seed = self.rng.randint(0, 2**31)  # Generate props seed
        
        # Phase 12: Generate water features
        if self.params.water_enabled:
            self._generate_water(dungeon)
        
        return dungeon
    
    def _place_rooms_incrementally(self, dungeon: Dungeon) -> None:
        """
        Place rooms one at a time, checking and marking the occupancy grid.
        For symmetric layouts, creates a central spine with mirrored branches.
        """
        if self.params.symmetry == SymmetryType.BILATERAL:
            self._place_rooms_bilateral(dungeon)
        elif self.params.symmetry in (SymmetryType.RADIAL_2, SymmetryType.RADIAL_4):
            self._place_rooms_radial(dungeon)
        else:
            self._place_rooms_asymmetric(dungeon)
    
    def _place_rooms_bilateral(self, dungeon: Dungeon) -> None:
        """
        Place rooms with bilateral (mirror) symmetry using spine-based generation.
        A spine is a line of rooms connected at centers, with branches left/right.
        
        For spine layouts, mark that we need an entrance on the first spine room.
        """
        min_count, max_count = self.params.get_room_count_range()
        target_count = self.rng.randint(min_count, max_count)
        
        # Create generation context with packing settings
        ctx = self._create_context()
        
        # Scale spine length and max depth based on target room count
        if target_count <= 12:
            spine_length = 2
            max_depth = 2
        elif target_count <= 25:
            spine_length = 3
            max_depth = 3
        elif target_count <= 50:
            spine_length = 4
            max_depth = 4
        else:
            spine_length = 5
            max_depth = 5
        
        # Store target for use in branching decisions
        self._target_room_count = target_count
        
        # Mark that this is a spine-based layout needing entrance on first room
        dungeon.is_spine_layout = True
        
        # Track spine direction for prop placement (daises go on opposite wall)
        self._spine_direction = 'south'
        
        # Configure context for main spine
        spine_ctx = ctx.clone(
            direction='south',
            depth=0,
            max_depth=max_depth,
        )
        
        # Generate main spine going SOUTH (positive Y direction)
        # This is the central corridor with branches left/right
        self._generate_spine_with_context(dungeon, start_x=0, start_y=-8, 
                                          length=spine_length, ctx=spine_ctx)
        
        # Fallback: If we didn't reach minimum room count, add more rooms
        current_count = len(dungeon.rooms)
        if current_count < min_count:
            self._add_fallback_rooms(dungeon, min_count - current_count, ctx)
    
    # Spine generation constants
    MAX_SPINE_LENGTH = 4  # Max rooms per spine
    BRANCH_CHANCE = 0.75  # High chance to branch for more recursion
    
    def _get_spacing_range(self) -> Tuple[int, int]:
        """Get min/max spacing between rooms based on density parameter.
        
        Watabou-style spacing:
        - Compact/Tight: Rooms nearly end-to-end, just 1-2 cells for passage
        - Normal: Some breathing room, 3-5 cells
        - Sparse: Rooms spread apart, 6-10 cells
        """
        density = self.params.density
        
        if density >= 0.8:
            return (1, 2)  # Tight/Compact: rooms almost touching, 1-cell passages
        elif density >= 0.6:
            return (2, 3)
        elif density >= 0.4:
            return (3, 5)  # Normal: moderate spacing
        elif density >= 0.2:
            return (6, 10)  # Sparse: spread out
        else:
            return (8, 14)  # Very sparse
    
    def _place_room_adjacent(self, anchor: Room, direction: str, 
                              new_room: Room, dungeon: Dungeon) -> bool:
        """
        Adjacent room growth strategy: place a room directly at an exit of another room.
        
        This creates rooms that are edge-to-edge with just 1 cell for the passage.
        Centers are aligned on the perpendicular axis.
        Also creates the 1-cell passage between them immediately.
        
        Args:
            anchor: The existing room to grow from
            direction: Which side of anchor ('north', 'south', 'east', 'west')
            new_room: The room to place (will be positioned)
            dungeon: Dungeon to add room to if successful
            
        Returns:
            True if room was placed and added, False if blocked
        """
        ax, ay = anchor.center_grid
        
        # Position new room edge-to-edge with anchor, 1 cell gap for passage
        # Align centers on the perpendicular axis
        if direction == 'north':
            new_room.x = ax - new_room.width // 2
            new_room.y = anchor.y - 1 - new_room.height
            # Passage cell is at the gap
            passage_x, passage_y = ax, anchor.y - 1
        elif direction == 'south':
            new_room.x = ax - new_room.width // 2
            new_room.y = anchor.y + anchor.height + 1
            passage_x, passage_y = ax, anchor.y + anchor.height
        elif direction == 'west':
            new_room.x = anchor.x - 1 - new_room.width
            new_room.y = ay - new_room.height // 2
            passage_x, passage_y = anchor.x - 1, ay
        elif direction == 'east':
            new_room.x = anchor.x + anchor.width + 1
            new_room.y = ay - new_room.height // 2
            passage_x, passage_y = anchor.x + anchor.width, ay
        else:
            return False
        
        # Check placement with margin=0 since we intentionally want adjacent
        if not self._can_place_room_adjacent(new_room, anchor):
            return False
        
        # Place the room
        dungeon.add_room(new_room)
        self._mark_room_in_grid(new_room)
        
        # Create 1-cell passage between rooms immediately
        # Waypoints: exit from anchor -> exit into new_room (2 points for 1-cell passage)
        nx, ny = new_room.center_grid
        if direction == 'north':
            waypoints = [(ax, anchor.y - 1), (nx, new_room.y + new_room.height)]
        elif direction == 'south':
            waypoints = [(ax, anchor.y + anchor.height), (nx, new_room.y - 1)]
        elif direction == 'west':
            waypoints = [(anchor.x - 1, ay), (new_room.x + new_room.width, ny)]
        elif direction == 'east':
            waypoints = [(anchor.x + anchor.width, ay), (new_room.x - 1, ny)]
        
        # Create and add passage (with validation)
        passage = Passage(
            start_room=anchor.id,
            end_room=new_room.id,
            waypoints=waypoints,
            width=1
        )
        return self._add_validated_passage(dungeon, passage)
    
    def _can_place_room_adjacent(self, room: Room, adjacent_to: Room) -> bool:
        """
        Check if room can be placed adjacent to another room.
        Same as _can_place_room - room cells must be EMPTY.
        """
        return self._can_place_room(room)
    
    def _create_passage_between(self, room1: Room, room2: Room, dungeon: Dungeon) -> bool:
        """
        Create a passage between two rooms using the standard passage creation logic.
        Used when adjacent placement fails but we still need to connect rooms.
        """
        passage = self._create_passage(room1, room2, dungeon)
        if passage:
            return self._add_validated_passage(dungeon, passage)
        return False
    
    # Legacy method for compatibility
    def _place_room_at_exit(self, anchor: Room, direction: str, 
                             new_room: Room, passage_length: int = 1) -> bool:
        """Legacy method - use _place_room_adjacent for adjacent growth strategy."""
        ax, ay = anchor.center_grid
        
        if direction == 'north':
            new_room.x = ax - new_room.width // 2
            new_room.y = anchor.y - passage_length - new_room.height
        elif direction == 'south':
            new_room.x = ax - new_room.width // 2
            new_room.y = anchor.y + anchor.height + passage_length
        elif direction == 'west':
            new_room.x = anchor.x - passage_length - new_room.width
            new_room.y = ay - new_room.height // 2
        elif direction == 'east':
            new_room.x = anchor.x + anchor.width + passage_length
            new_room.y = ay - new_room.height // 2
        else:
            return False
        
        return self._can_place_room(new_room)
    
    def _add_fallback_rooms(self, dungeon: Dungeon, count: int, ctx: GenerationContext) -> None:
        """Add additional rooms when spine generation didn't meet minimum count.
        
        Uses context to determine placement mode:
        - tight: adjacent exit placement with 1-cell passages
        - normal/sparse: offset-based placement with spacing from context
        """
        existing_rooms = list(dungeon.rooms.values())
        if not existing_rooms:
            return
        
        placed = 0
        max_attempts = count * 20
        attempt = 0
        directions = ['north', 'south', 'east', 'west']
        
        while placed < count and attempt < max_attempts:
            attempt += 1
            
            # Create a room template using context
            room = self._create_room_template(ctx.templates, ctx.circle_radii)
            
            # Pick a random existing room to place near
            anchor = self.rng.choice(existing_rooms)
            
            # For tight/compact mode: try adjacent exit placement
            if ctx.is_tight:
                self.rng.shuffle(directions)
                for direction in directions:
                    if self._place_room_at_exit(anchor, direction, room, 
                                                passage_length=ctx.passage_length):
                        if self._can_place_room(room):
                            dungeon.add_room(room)
                            self._mark_room_in_grid(room)
                            existing_rooms.append(room)
                            placed += 1
                            break
            else:
                # Offset-based placement using context spacing
                min_spacing, max_spacing = ctx.spacing_range
                min_offset = min_spacing + 2
                max_offset = max_spacing + 5
                
                ax, ay = anchor.center_grid
                
                for _ in range(10):
                    offset_x = self.rng.randint(-max_offset, max_offset)
                    offset_y = self.rng.randint(-max_offset, max_offset)
                    
                    if abs(offset_x) < min_offset and abs(offset_y) < min_offset:
                        offset_x = min_offset if offset_x >= 0 else -min_offset
                    
                    room.x = ax + offset_x
                    room.y = ay + offset_y
                    
                    if self._can_place_room(room):
                        dungeon.add_room(room)
                        self._mark_room_in_grid(room)
                        existing_rooms.append(room)
                        placed += 1
                        break
    
    def _generate_spine_with_context(self, dungeon: Dungeon, 
                                      start_x: int, start_y: int,
                                      length: int, ctx: GenerationContext,
                                      parent_room: Room = None) -> List[Room]:
        """
        Generate a spine using generation context.
        Context is cloned and modified for recursive branch calls.
        
        Args:
            parent_room: For tight mode branches, the room this spine branches from.
                        First room will be placed adjacent to parent with passage.
        """
        if ctx.depth >= ctx.max_depth or length <= 0:
            return []
        
        placement_rng = random.Random(ctx.placement_seed)
        termination_rng = random.Random(ctx.termination_seed)
        
        spine_rooms = []
        current_x, current_y = start_x, start_y
        actual_length = min(length, self.MAX_SPINE_LENGTH)
        
        # Direction vectors
        direction = ctx.direction
        dx, dy = {'south': (0, 1), 'north': (0, -1), 
                  'east': (1, 0), 'west': (-1, 0)}[direction]
        
        # For tight mode with parent, first room connects to parent
        prev_room = parent_room if ctx.is_tight else None
        
        for i in range(actual_length):
            # Create room optimized for spine
            room = self._create_spine_room(ctx.templates, ctx.circle_radii, 
                                           placement_rng, direction, i == 0)
            
            # Position room - tight mode uses adjacent growth strategy
            placed = False
            if ctx.is_tight and prev_room is not None:
                # Adjacent room growth: place directly at exit of previous room
                placed = self._place_room_adjacent(prev_room, direction, room, dungeon)
                if placed:
                    spine_rooms.append(room)
                    prev_room = room
            
            if not placed:
                # Standard center-based positioning (first room or non-tight mode)
                room.x = current_x - room.width // 2
                room.y = current_y - room.height // 2
                
                if self._can_place_room(room):
                    dungeon.add_room(room)
                    self._mark_room_in_grid(room)
                    spine_rooms.append(room)
                    
                    # Mark first room of main spine as entrance point
                    if ctx.depth == 0 and i == 0 and dungeon.spine_start_room is None:
                        dungeon.spine_start_room = room.id
                    
                    # If we have a parent but adjacent placement failed, 
                    # still create a passage to the parent
                    if ctx.is_tight and parent_room is not None and i == 0:
                        self._create_passage_between(parent_room, room, dungeon)
                    
                    prev_room = room
                    placed = True
            
            # Only do branching if room was placed
            if placed:
                # Branch perpendicular to spine direction
                if direction in ('south', 'north'):
                    left_dir, right_dir = 'west', 'east'
                else:
                    left_dir, right_dir = 'north', 'south'
                
                # Decide whether to branch
                branch_chance = placement_rng.random()
                if branch_chance < self.BRANCH_CHANCE and ctx.depth < ctx.max_depth - 1:
                    # Get branch spacing from context
                    branch_gap = ctx.get_spacing(placement_rng) if not ctx.is_tight else 1
                    
                    # Generate seeds for branches
                    branch_placement_seed = placement_rng.randint(0, 2**31)
                    left_term_seed = termination_rng.randint(0, 2**31)
                    right_term_seed = termination_rng.randint(0, 2**31)
                    
                    # Calculate branch start positions - for tight mode, start at room edge
                    room_cx, room_cy = room.center_grid
                    if left_dir == 'west':
                        left_start = (room.x - branch_gap, room_cy)
                    elif left_dir == 'east':
                        left_start = (room.x + room.width + branch_gap, room_cy)
                    elif left_dir == 'north':
                        left_start = (room_cx, room.y - branch_gap)
                    else:  # south
                        left_start = (room_cx, room.y + room.height + branch_gap)
                    
                    # Clone context for left branch
                    left_ctx = ctx.clone(
                        direction=left_dir,
                        depth=ctx.depth + 1,
                        placement_seed=branch_placement_seed,
                        termination_seed=left_term_seed,
                    )
                    
                    sub_length = max(2, actual_length - 1)
                    # Pass current room as parent for tight mode (creates passage)
                    self._generate_spine_with_context(dungeon, left_start[0], left_start[1],
                                                      sub_length, left_ctx,
                                                      parent_room=room if ctx.is_tight else None)
                    
                    # Mirror branch on right side (same placement seed, different termination)
                    if right_dir == 'east':
                        right_start = (room.x + room.width + branch_gap, room_cy)
                    elif right_dir == 'west':
                        right_start = (room.x - branch_gap, room_cy)
                    elif right_dir == 'south':
                        right_start = (room_cx, room.y + room.height + branch_gap)
                    else:  # north
                        right_start = (room_cx, room.y - branch_gap)
                    
                    right_ctx = ctx.clone(
                        direction=right_dir,
                        depth=ctx.depth + 1,
                        placement_seed=branch_placement_seed,  # SAME seed for symmetry
                        termination_seed=right_term_seed,
                    )
                    
                    self._generate_spine_with_context(dungeon, right_start[0], right_start[1],
                                                      sub_length, right_ctx,
                                                      parent_room=room if ctx.is_tight else None)
            
            # Move to next position - for tight mode, we'll position next room adjacent
            # For other modes, use spacing-based positioning
            if not ctx.is_tight:
                base_size = room.height if direction in ('south', 'north') else room.width
                spacing = base_size + ctx.get_spacing(placement_rng)
                current_x += dx * spacing
                current_y += dy * spacing
            else:
                # For tight mode: position will be set when we create the next room
                # Move current position to the edge of this room + 1 cell passage
                if direction == 'south':
                    current_y = room.y + room.height + 1
                elif direction == 'north':
                    current_y = room.y - 1
                elif direction == 'east':
                    current_x = room.x + room.width + 1
                else:  # west
                    current_x = room.x - 1
        
        return spine_rooms
    
    # Legacy method - kept for compatibility
    def _generate_spine(self, dungeon: Dungeon,
                        start_x: int, start_y: int,
                        direction: str, length: int,
                        templates, circle_radii,
                        placement_seed: int, termination_seed: int,
                        depth: int, max_depth: int) -> List[Room]:
        """
        Generate a spine - a line of rooms connected at centers.
        At each room, can branch LEFT and RIGHT with sub-spines.
        Left and right branches use SAME placement_seed, DIFFERENT termination_seeds.
        """
        if depth >= max_depth or length <= 0:
            return []
        
        placement_rng = random.Random(placement_seed)
        termination_rng = random.Random(termination_seed)
        
        spine_rooms = []
        current_x, current_y = start_x, start_y
        
        # Limit spine length
        actual_length = min(length, self.MAX_SPINE_LENGTH)
        
        # Direction vectors
        if direction == 'south':
            dx, dy = 0, 1
        elif direction == 'north':
            dx, dy = 0, -1
        elif direction == 'east':
            dx, dy = 1, 0
        else:  # west
            dx, dy = -1, 0
        
        for i in range(actual_length):
            # Create room - prefer odd sizes and circles for spine rooms
            room = self._create_spine_room(templates, circle_radii, placement_rng, direction, i == 0)
            
            # Position room so its center aligns with spine
            room.x = current_x - room.width // 2
            room.y = current_y - room.height // 2
            
            if self._can_place_room(room):
                dungeon.add_room(room)
                self._mark_room_in_grid(room)
                spine_rooms.append(room)
                
                # Branch left and right (perpendicular to spine direction)
                if direction in ('south', 'north'):
                    left_dir, right_dir = 'west', 'east'
                else:
                    left_dir, right_dir = 'north', 'south'
                
                # Higher branch chance, ensure recursion continues
                branch_chance = placement_rng.random()
                if branch_chance < self.BRANCH_CHANCE and depth < max_depth - 1:
                    # Generate sub-seeds for branches
                    branch_placement_seed = placement_rng.randint(0, 2**31)
                    left_term_seed = termination_rng.randint(0, 2**31)
                    right_term_seed = termination_rng.randint(0, 2**31)
                    
                    # Spacing for branch start
                    # For tight mode: adjacent placement with 1-cell passage
                    if self.params.density >= 0.8:
                        branch_gap = 1  # Adjacent with 1-cell passage
                    else:
                        min_spacing, max_spacing = self._get_spacing_range()
                        branch_gap = placement_rng.randint(min_spacing, max_spacing)
                    
                    # LEFT branch
                    if left_dir == 'west':
                        left_start_x = room.x - branch_gap
                        left_start_y = current_y
                    elif left_dir == 'east':
                        left_start_x = room.x + room.width + branch_gap
                        left_start_y = current_y
                    elif left_dir == 'north':
                        left_start_x = current_x
                        left_start_y = room.y - branch_gap
                    else:  # south
                        left_start_x = current_x
                        left_start_y = room.y + room.height + branch_gap
                    
                    # Sub-spine length decreases but stays reasonable
                    sub_length = max(2, actual_length - 1)
                    
                    self._generate_spine(
                        dungeon, left_start_x, left_start_y,
                        left_dir, sub_length,
                        templates, circle_radii,
                        branch_placement_seed, left_term_seed,
                        depth + 1, max_depth
                    )
                    
                    # RIGHT branch - same placement seed, different termination
                    terminate_right = random.Random(right_term_seed).random() < self.params.symmetry_break
                    
                    if not terminate_right:
                        if right_dir == 'east':
                            right_start_x = room.x + room.width + branch_gap
                            right_start_y = current_y
                        elif right_dir == 'west':
                            right_start_x = room.x - branch_gap
                            right_start_y = current_y
                        elif right_dir == 'south':
                            right_start_x = current_x
                            right_start_y = room.y + room.height + branch_gap
                        else:  # north
                            right_start_x = current_x
                            right_start_y = room.y - branch_gap
                        
                        self._generate_spine(
                            dungeon, right_start_x, right_start_y,
                            right_dir, sub_length,
                            templates, circle_radii,
                            branch_placement_seed,  # SAME seed as left
                            right_term_seed,
                            depth + 1, max_depth
                        )
            
            # Move to next position along spine - spacing based on density
            base_size = room.height if direction in ('south', 'north') else room.width
            
            # For tight/compact mode: adjacent placement with just 1-cell passage
            if self.params.density >= 0.8:
                # Room edge to room edge = 1 cell (for passage)
                # So next room center = current center + half current room + 1 + half next room
                # Since we don't know next room size yet, use base_size as estimate
                spacing = base_size + 1  # Adjacent with 1-cell passage
            else:
                min_spacing, max_spacing = self._get_spacing_range()
                extra_spacing = placement_rng.randint(min_spacing, max_spacing)
                spacing = base_size + extra_spacing
            
            current_x += dx * spacing
            current_y += dy * spacing
        
        return spine_rooms
    
    def _create_spine_room(self, templates, circle_radii, rng: random.Random, 
                           direction: str, is_first: bool) -> Room:
        """
        Create a room optimized for spine placement.
        Uses templates from params (respects cozy/grand settings).
        - Can be regular room or circle
        - Prefers odd-sized rooms for center alignment
        
        Note: Junction meta-rooms (T, cross, Y-split) are passage configurations,
        not actual rooms - they're handled during passage generation.
        """
        # Circle chance - higher for first room of branch
        circle_chance = 0.3 if is_first else 0.15
        
        # Try circle
        if rng.random() < circle_chance and circle_radii:
            radius = rng.choice(circle_radii)
            diameter = 2 * radius + 1
            return Room(x=0, y=0, width=diameter, height=diameter, shape=RoomShape.CIRCLE)
        
        # Default: regular rectangular room from templates
        if not templates:
            templates = [(3, 3)]
        
        w, h = rng.choice(templates)
        
        # Orient room so longer dimension aligns with spine direction
        if direction in ('south', 'north'):
            if w > h:
                w, h = h, w
        else:
            if h > w:
                w, h = h, w
        
        # Ensure odd dimensions for center passage alignment
        if direction in ('south', 'north'):
            if h % 2 == 0:
                h += 1
            if w % 2 == 0:
                w += 1
        else:
            if w % 2 == 0:
                w += 1
            if h % 2 == 0:
                h += 1
        
        return Room(x=0, y=0, width=w, height=h, shape=RoomShape.RECT)
    
    def _create_junction_room(self, rng: random.Random, direction: str) -> Optional[Room]:
        """
        Junction meta-rooms are NOT actual rooms - they're passage configurations.
        Return None here; junctions are handled separately via _create_junction_passages.
        """
        # Junctions are passage-based, not room-based
        # They'll be created during passage generation, not room generation
        return None
    
    def _create_room_template_with_rng(self, templates, circle_radii, rng: random.Random) -> Room:
        """Create a room template using specific RNG (for deterministic replay).
        Uses templates from params (respects cozy/grand settings).
        """
        if rng.random() < self.params.round_room_chance and circle_radii:
            radius = rng.choice(circle_radii)
            # Diameter = 2*radius + 1 for odd-sized circles (3x3, 5x5, 7x7)
            diameter = 2 * radius + 1
            return Room(x=0, y=0, width=diameter, height=diameter, shape=RoomShape.CIRCLE)
        else:
            # Regular room from templates (already respects cozy/grand)
            w, h = rng.choice(templates)
            return Room(x=0, y=0, width=w, height=h, shape=RoomShape.RECT)
    
    def _place_rooms_radial(self, dungeon: Dungeon) -> None:
        """
        Place rooms with radial symmetry (2-fold or 4-fold rotation).
        Creates rooms in one quadrant then rotates them.
        """
        min_count, max_count = self.params.get_room_count_range()
        
        if self.params.symmetry == SymmetryType.RADIAL_4:
            target_count = self.rng.randint(min_count, max_count) // 4 + 1
        else:  # RADIAL_2
            target_count = self.rng.randint(min_count, max_count) // 2 + 1
        
        templates = self.params.get_room_templates()
        circle_radii = self.params.get_circle_radii()
        
        max_placement_attempts = 50
        placed_count = 0
        failed_count = 0
        max_failures = target_count
        
        rooms_to_rotate = []
        
        # Scale placement area based on target room count
        if target_count <= 5:
            area_size = 10
        elif target_count <= 12:
            area_size = 15
        elif target_count <= 25:
            area_size = 22
        else:
            area_size = 30
        
        # Place rooms in one quadrant (positive x, positive y for radial4, or positive y for radial2)
        while placed_count < target_count and failed_count < max_failures:
            room = self._create_room_template(templates, circle_radii)
            
            placed = False
            for attempt in range(max_placement_attempts):
                if self.params.symmetry == SymmetryType.RADIAL_4:
                    # First quadrant only
                    x = self.rng.randint(2, area_size)
                    y = self.rng.randint(2, area_size)
                else:
                    # Top half only
                    x = self.rng.randint(-area_size // 2, area_size // 2)
                    y = self.rng.randint(2, area_size)
                
                room.x = x
                room.y = y
                
                if self._can_place_room(room):
                    dungeon.add_room(room)
                    self._mark_room_in_grid(room)
                    rooms_to_rotate.append(room)
                    placed_count += 1
                    failed_count = 0
                    placed = True
                    break
            
            if not placed:
                failed_count += 1
        
        # Rotate rooms
        rotations = [2] if self.params.symmetry == SymmetryType.RADIAL_2 else [1, 2, 3]
        
        for room in rooms_to_rotate:
            for rot in rotations:
                if self.rng.random() < self.params.symmetry_break:
                    continue
                
                # Rotate around origin
                cx, cy = room.x + room.width // 2, room.y + room.height // 2
                
                if rot == 1:  # 90°
                    new_cx, new_cy = -cy, cx
                    new_w, new_h = room.height, room.width
                elif rot == 2:  # 180°
                    new_cx, new_cy = -cx, -cy
                    new_w, new_h = room.width, room.height
                else:  # 270°
                    new_cx, new_cy = cy, -cx
                    new_w, new_h = room.height, room.width
                
                rotated = Room(
                    x=int(new_cx - new_w // 2),
                    y=int(new_cy - new_h // 2),
                    width=new_w,
                    height=new_h,
                    shape=room.shape,
                    z=room.z
                )
                
                if self._can_place_room(rotated):
                    dungeon.add_room(rotated)
                    self._mark_room_in_grid(rotated)
    
    def _place_rooms_asymmetric(self, dungeon: Dungeon) -> None:
        """Place rooms without symmetry constraints."""
        min_count, max_count = self.params.get_room_count_range()
        target_count = self.rng.randint(min_count, max_count)
        
        templates = self.params.get_room_templates()
        circle_radii = self.params.get_circle_radii()
        
        max_placement_attempts = 50
        placed_count = 0
        failed_count = 0
        max_failures = target_count
        
        # Scale initial placement area based on target count
        if target_count <= 12:
            base_radius = 5
        elif target_count <= 25:
            base_radius = 8
        elif target_count <= 50:
            base_radius = 12
        else:
            base_radius = 18
        
        while placed_count < target_count and failed_count < max_failures:
            room = self._create_room_template(templates, circle_radii)
            
            placed = False
            for attempt in range(max_placement_attempts):
                if attempt < 10:
                    x = self.rng.randint(-base_radius, base_radius)
                    y = self.rng.randint(-base_radius, base_radius)
                else:
                    radius = base_radius + (attempt - 10) // 5 * 3
                    x = self.rng.randint(-radius, radius)
                    y = self.rng.randint(-radius, radius)
                
                room.x = x
                room.y = y
                
                if self._can_place_room(room):
                    dungeon.add_room(room)
                    self._mark_room_in_grid(room)
                    placed_count += 1
                    failed_count = 0
                    placed = True
                    break
            
            if not placed:
                failed_count += 1
    
    def _create_room_template(self, templates, circle_radii) -> Room:
        """Create a room with random size/shape but position 0,0.
        Uses templates from params (respects cozy/grand settings).
        """
        if self.rng.random() < self.params.round_room_chance and circle_radii:
            # Circular room - diameter = 2*radius + 1 for odd-sized circles
            radius = self.rng.choice(circle_radii)
            diameter = 2 * radius + 1
            return Room(x=0, y=0, width=diameter, height=diameter, shape=RoomShape.CIRCLE)
        else:
            # Regular room from templates (already respects cozy/grand)
            w, h = self.rng.choice(templates)
            return Room(x=0, y=0, width=w, height=h, shape=RoomShape.RECT)
    
    def _can_place_room(self, room: Room, allow_reserved: bool = False) -> bool:
        """
        Check if a room can be placed at its current position.
        
        Room OCCUPIED cells must be on completely EMPTY cells.
        Reserve/margin cells can overlap existing RESERVED cells (they merge).
        
        Args:
            room: The room to check
            allow_reserved: If True, also allow margin to be on RESERVED (for tight/adjacent)
        """
        if room.shape == RoomShape.CIRCLE:
            radius = room.width / 2.0
            center_x = room.x + radius
            center_y = room.y + radius
            
            # Only check room cells - they must be EMPTY
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    cell_cx = x + 0.5
                    cell_cy = y + 0.5
                    dx = cell_cx - center_x
                    dy = cell_cy - center_y
                    dist_sq = dx * dx + dy * dy
                    
                    # Inside the circle = room cell, must be EMPTY
                    if dist_sq <= radius * radius:
                        cell_type = self.occupancy.get_cell(x, y)
                        if cell_type != 'EMPTY':
                            return False
        else:
            # Rectangular room - room cells must be EMPTY
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    cell_type = self.occupancy.get_cell(x, y)
                    if cell_type != 'EMPTY':
                        return False
        return True
    
    def _mark_room_in_grid(self, room: Room) -> None:
        """Mark a room in the occupancy grid."""
        if room.shape == RoomShape.CIRCLE:
            radius = room.width // 2
            self.occupancy.mark_room(
                room.id, room.x, room.y,
                room.width, room.height,
                margin=1, is_circle=True, radius=radius
            )
        else:
            self.occupancy.mark_room(
                room.id, room.x, room.y,
                room.width, room.height,
                margin=1
            )
    
    def _separate_rooms(self, rooms: List[Room], margin: int = 3, max_iterations: int = 100) -> List[Room]:
        """Separate overlapping rooms using iterative pushing."""
        if len(rooms) < 2:
            return rooms
        
        for _ in range(max_iterations):
            moved = False
            
            for i, room1 in enumerate(rooms):
                rect1 = Rect(room1.x, room1.y, room1.width, room1.height)
                
                for j, room2 in enumerate(rooms):
                    if i >= j:
                        continue
                    
                    rect2 = Rect(room2.x, room2.y, room2.width, room2.height)
                    
                    if rect1.overlaps(rect2, margin):
                        # Calculate separation
                        sep = rect1.separation_vector(rect2)
                        
                        if sep[0] != 0 or sep[1] != 0:
                            # Move both rooms apart
                            room1.x += int(sep[0] * 0.5) + (1 if sep[0] > 0 else -1 if sep[0] < 0 else 0)
                            room1.y += int(sep[1] * 0.5) + (1 if sep[1] > 0 else -1 if sep[1] < 0 else 0)
                            room2.x -= int(sep[0] * 0.5) + (1 if sep[0] > 0 else -1 if sep[0] < 0 else 0)
                            room2.y -= int(sep[1] * 0.5) + (1 if sep[1] > 0 else -1 if sep[1] < 0 else 0)
                            moved = True
            
            if not moved:
                break
        
        # Compact towards center based on density
        if self.params.density > 0.5:
            self._compact_rooms(rooms)
        
        return rooms
    
    def _build_occupancy_grid(self, dungeon: Dungeon) -> None:
        """Build occupancy grid from placed rooms."""
        for room in dungeon.rooms.values():
            if room.shape == RoomShape.CIRCLE:
                radius = room.width // 2
                self.occupancy.mark_room(
                    room.id, room.x, room.y, 
                    room.width, room.height,
                    margin=1, is_circle=True, radius=radius
                )
            else:
                self.occupancy.mark_room(
                    room.id, room.x, room.y,
                    room.width, room.height,
                    margin=1
                )
    
    def _compact_rooms(self, rooms: List[Room]) -> None:
        """Move rooms towards center while maintaining separation."""
        if not rooms:
            return
            
        # Find centroid
        cx = sum(r.x + r.width / 2 for r in rooms) / len(rooms)
        cy = sum(r.y + r.height / 2 for r in rooms) / len(rooms)
        
        # Sort by distance from center (move outer rooms first)
        rooms_by_dist = sorted(rooms, 
            key=lambda r: ((r.x + r.width/2 - cx)**2 + (r.y + r.height/2 - cy)**2),
            reverse=True)
        
        for room in rooms_by_dist:
            # Try to move towards center
            rcx = room.x + room.width / 2
            rcy = room.y + room.height / 2
            
            dx = 1 if rcx > cx else -1 if rcx < cx else 0
            dy = 1 if rcy > cy else -1 if rcy < cy else 0
            
            # Check if move would cause collision
            test_rect = Rect(room.x + dx, room.y + dy, room.width, room.height)
            can_move = True
            
            for other in rooms:
                if other.id == room.id:
                    continue
                other_rect = Rect(other.x, other.y, other.width, other.height)
                if test_rect.overlaps(other_rect, margin=2):
                    can_move = False
                    break
            
            if can_move:
                room.x += dx
                room.y += dy
    
    def _apply_symmetry(self, rooms: List[Room]) -> List[Room]:
        """Apply symmetry transformations and optional breaking."""
        if self.params.symmetry == SymmetryType.NONE:
            return rooms
        
        result = list(rooms)
        
        # Find bounds for mirroring
        if not rooms:
            return result
            
        max_x = max(r.x + r.width for r in rooms)
        min_x = min(r.x for r in rooms)
        axis_x = (max_x + min_x) / 2
        
        max_y = max(r.y + r.height for r in rooms)
        min_y = min(r.y for r in rooms)
        axis_y = (max_y + min_y) / 2
        
        # Initialize mirror pairs tracking
        if not hasattr(self, '_mirror_pairs'):
            self._mirror_pairs = {}
        self._mirror_axis_x = axis_x  # Store for passage mirroring
        
        if self.params.symmetry == SymmetryType.BILATERAL:
            # Mirror across vertical axis
            for room in rooms:
                # Skip some rooms for symmetry breaking
                if self.rng.random() < self.params.symmetry_break:
                    continue
                    
                mirror_x = int(2 * axis_x - room.x - room.width)
                mirrored = Room(
                    x=mirror_x, y=room.y,
                    width=room.width, height=room.height,
                    shape=room.shape, z=room.z
                )
                result.append(mirrored)
                # Track the mirror relationship (both directions)
                self._mirror_pairs[room.id] = mirrored.id
                self._mirror_pairs[mirrored.id] = room.id
        
        elif self.params.symmetry == SymmetryType.RADIAL_2:
            # 180° rotation
            for room in rooms:
                if self.rng.random() < self.params.symmetry_break:
                    continue
                    
                rot_x = int(2 * axis_x - room.x - room.width)
                rot_y = int(2 * axis_y - room.y - room.height)
                rotated = Room(
                    x=rot_x, y=rot_y,
                    width=room.width, height=room.height,
                    shape=room.shape, z=room.z
                )
                result.append(rotated)
        
        elif self.params.symmetry == SymmetryType.RADIAL_4:
            # 90° rotations (4-fold)
            for room in rooms:
                for angle in [1, 2, 3]:  # 90, 180, 270 degrees
                    if self.rng.random() < self.params.symmetry_break:
                        continue
                    
                    # Rotate around center
                    rcx = room.x + room.width / 2 - axis_x
                    rcy = room.y + room.height / 2 - axis_y
                    
                    if angle == 1:  # 90°
                        new_cx, new_cy = -rcy, rcx
                        new_w, new_h = room.height, room.width
                    elif angle == 2:  # 180°
                        new_cx, new_cy = -rcx, -rcy
                        new_w, new_h = room.width, room.height
                    else:  # 270°
                        new_cx, new_cy = rcy, -rcx
                        new_w, new_h = room.height, room.width
                    
                    rotated = Room(
                        x=int(new_cx + axis_x - new_w / 2),
                        y=int(new_cy + axis_y - new_h / 2),
                        width=new_w, height=new_h,
                        shape=room.shape, z=room.z
                    )
                    result.append(rotated)
        
        return result
    
    def _connect_rooms(self, dungeon: Dungeon) -> List[Passage]:
        """Connect rooms - uses spine-based for symmetric, MST for asymmetric."""
        rooms = list(dungeon.rooms.values())
        if len(rooms) < 2:
            return []
        
        if self.params.symmetry in (SymmetryType.BILATERAL, SymmetryType.RADIAL_2, SymmetryType.RADIAL_4):
            return self._connect_rooms_spine(dungeon, rooms)
        else:
            return self._connect_rooms_mst(dungeon, rooms)
    
    def _connect_rooms_spine(self, dungeon: Dungeon, rooms: List[Room]) -> List[Passage]:
        """
        Connect rooms using spine-based logic for symmetric layouts.
        Phase 1: Connect spine rooms vertically (center exits)
        Phase 2: Connect branches to spine, mirroring passages
        Phase 3: Symmetry breaking with opportunistic random connections
        """
        passages = []
        connected_rooms = set()
        
        # Get mirror pairs if available
        mirror_pairs = getattr(self, '_mirror_pairs', {})
        
        # Identify spine rooms (near x=0) vs branch rooms
        spine_rooms = [r for r in rooms if abs(r.center[0]) < 5]
        branch_rooms = [r for r in rooms if abs(r.center[0]) >= 5]
        
        # Sort spine by Y
        spine_rooms = sorted(spine_rooms, key=lambda r: r.center[1])
        
        # PHASE 1: Connect spine rooms vertically
        for i in range(len(spine_rooms) - 1):
            room1 = spine_rooms[i]
            room2 = spine_rooms[i + 1]
            
            passage = self._create_spine_passage(room1, room2, dungeon)
            if passage:
                if self._add_validated_passage(dungeon, passage, passages, connected_rooms):
                    pass  # Successfully added
        
        # PHASE 2: Connect branches to spine (with mirroring)
        left_branches = sorted([r for r in branch_rooms if r.center[0] < 0], 
                               key=lambda r: r.center[1])
        
        for left_room in left_branches:
            # Find nearest spine room
            if not spine_rooms:
                continue
                
            nearest_spine = min(spine_rooms,
                key=lambda r: abs(r.center[1] - left_room.center[1]))
            
            # Create passage from spine to left branch
            passage = self._create_spine_passage(nearest_spine, left_room, dungeon)
            if passage:
                self._add_validated_passage(dungeon, passage, passages, connected_rooms)
                
                # Mirror the passage to right side if mirror pair exists
                if left_room.id in mirror_pairs:
                    right_room_id = mirror_pairs[left_room.id]
                    right_room = dungeon.rooms.get(right_room_id)
                    
                    if right_room and right_room.id not in connected_rooms:
                        # Create truly mirrored passage by mirroring waypoints
                        axis_x = getattr(self, '_mirror_axis_x', 0)
                        mirrored_waypoints = self._mirror_waypoints(passage.waypoints, axis_x)
                        
                        if mirrored_waypoints and self.occupancy.is_valid_waypoints(mirrored_waypoints):
                            mirrored_passage = Passage(
                                start_room=nearest_spine.id,
                                end_room=right_room.id,
                                waypoints=mirrored_waypoints,
                                width=passage.width,
                                style=passage.style
                            )
                            # Validate and add mirrored passage
                            if self._add_validated_passage(dungeon, mirrored_passage, passages, connected_rooms):
                                pass  # Successfully added
        
        # Connect any remaining right-side rooms
        right_branches = [r for r in branch_rooms if r.center[0] > 0 and r.id not in connected_rooms]
        for right_room in right_branches:
            if not spine_rooms:
                continue
            nearest_spine = min(spine_rooms,
                key=lambda r: abs(r.center[1] - right_room.center[1]))
            
            passage = self._create_spine_passage(nearest_spine, right_room, dungeon)
            if passage:
                self._add_validated_passage(dungeon, passage, passages, connected_rooms)
        
        # Connect isolated rooms
        isolated = [r for r in rooms if r.id not in connected_rooms]
        for room in isolated:
            connected_list = [r for r in rooms if r.id in connected_rooms]
            if not connected_list:
                connected_list = rooms
            
            # Sort by distance and try each until one works (that we're not already connected to)
            candidates = sorted(connected_list, 
                key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1]))
            
            for candidate in candidates[:5]:
                if self._are_rooms_connected(room.id, candidate.id):
                    continue  # Already connected, try another
                    
                passage = self._create_spine_passage(room, candidate, dungeon)
                if passage:
                    if self._add_validated_passage(dungeon, passage, passages, connected_rooms):
                        break
        
        # PHASE 3: Symmetry breaking - opportunistic random connections
        if self.params.symmetry_break > 0:
            for room in rooms:
                if self.rng.random() > self.params.symmetry_break:
                    continue
                
                others = sorted(
                    [r for r in rooms if r.id != room.id],
                    key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1])
                )[:5]
                
                for other in others:
                    # Don't create duplicate connections
                    if not self._can_add_connection(room.id, other.id):
                        continue
                        
                    passage = self._create_passage(room, other, dungeon, allow_partial=True)
                    if passage:
                        if self._add_validated_passage(dungeon, passage, passages):
                            break
        
        return passages
    
    def _create_spine_passage(self, room1: Room, room2: Room, dungeon: Dungeon) -> Optional[Passage]:
        """
        Create a spine passage - prefers center exits and straight connections.
        Falls back to regular passage if spine connection fails.
        """
        # Determine direction based on relative positions
        dx = room2.center[0] - room1.center[0]
        dy = room2.center[1] - room1.center[1]
        
        # Try straight connection first (always best for spine)
        straight_result = self._try_straight_connection(room1, room2)
        if straight_result:
            # Validate no diagonals
            if not self.occupancy.is_valid_waypoints(straight_result):
                print(f"WARNING: Diagonal in spine straight: {straight_result}")
            else:
                return Passage(
                    start_room=room1.id,
                    end_room=room2.id,
                    waypoints=straight_result,
                    width=self.params.passage_width,
                    style=PassageStyle.STRAIGHT
                )
        
        # Determine spine direction - prefer center exits
        if abs(dy) > abs(dx):
            # Vertical spine (north-south)
            if dy > 0:
                dir1, dir2 = 'south', 'north'
            else:
                dir1, dir2 = 'north', 'south'
        else:
            # Horizontal spine (east-west)  
            if dx > 0:
                dir1, dir2 = 'east', 'west'
            else:
                dir1, dir2 = 'west', 'east'
        
        # Try with center exit (offset 0) first
        full_waypoints, _ = self._try_passage_route(room1, room2, dir1, dir2, 0, 0, 0)
        if full_waypoints:
            # Validate no diagonals
            if not self.occupancy.is_valid_waypoints(full_waypoints):
                print(f"WARNING: Diagonal in spine route: {full_waypoints}")
            else:
                style = PassageStyle.STRAIGHT if len(full_waypoints) == 2 else PassageStyle.L_BEND
                return Passage(
                    start_room=room1.id,
                    end_room=room2.id,
                    waypoints=full_waypoints,
                    width=self.params.passage_width,
                    style=style
                )
        
        # Fall back to regular passage creation
        return self._create_passage(room1, room2, dungeon, allow_partial=True)
    
    def _connect_rooms_mst(self, dungeon: Dungeon, rooms: List[Room]) -> List[Passage]:
        """Connect rooms using Delaunay triangulation and MST (asymmetric layouts)."""
        # Get room centers as points
        points = [Point(r.center[0], r.center[1]) for r in rooms]
        
        # Build Delaunay triangulation
        all_edges = delaunay_triangulation(points)
        
        # Get MST for guaranteed connectivity
        mst_edges = minimum_spanning_tree(points, all_edges)
        
        # Add extra edges based on loop_factor (Jaquaying)
        extra_edges = [e for e in all_edges if e not in mst_edges]
        self.rng.shuffle(extra_edges)
        
        num_extra = int(len(extra_edges) * self.params.loop_factor)
        final_edges = mst_edges + extra_edges[:num_extra]
        
        # Track connected rooms
        connected_rooms = set()
        passages = []
        
        # Create passages for each edge
        for edge in final_edges:
            room1 = rooms[edge[0]]
            room2 = rooms[edge[1]]
            passage = self._create_passage(room1, room2, dungeon)
            if passage:
                self._add_validated_passage(dungeon, passage, passages, connected_rooms)
        
        # Try to connect isolated rooms - first pass: room-to-room only
        isolated = [r for r in rooms if r.id not in connected_rooms]
        for room in isolated:
            others = sorted(
                [r for r in rooms if r.id != room.id],
                key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1])
            )
            for other in others[:10]:
                # Skip if already connected
                if self._are_rooms_connected(room.id, other.id):
                    continue
                    
                passage = self._create_passage(room, other, dungeon, allow_partial=True)
                if passage:
                    if self._add_validated_passage(dungeon, passage, passages, connected_rooms):
                        break
        
        # Second pass: allow partial passages (room-to-passage T-junctions)
        still_isolated = [r for r in rooms if r.id not in connected_rooms]
        for room in still_isolated:
            others = sorted(
                [r for r in rooms if r.id != room.id],
                key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1])
            )
            for other in others[:10]:
                # Skip if already connected
                if self._are_rooms_connected(room.id, other.id):
                    continue
                    
                passage = self._create_passage(room, other, dungeon, allow_partial=True)
                if passage:
                    if self._add_validated_passage(dungeon, passage, passages, connected_rooms):
                        break
        
        return passages
    
    def _connect_orphan_rooms(self, dungeon: Dungeon) -> None:
        """
        Find rooms with no passages and connect them to nearest connected room.
        This ensures all rooms are reachable.
        """
        if len(dungeon.rooms) < 2:
            return
        
        # Multiple passes to handle clusters of orphans
        max_passes = 5
        for pass_num in range(max_passes):
            # Find rooms with connections
            connected_room_ids = set()
            for passage in dungeon.passages.values():
                connected_room_ids.add(passage.start_room)
                connected_room_ids.add(passage.end_room)
            
            # Find orphan rooms
            orphan_rooms = [
                room for room in dungeon.rooms.values() 
                if room.id not in connected_room_ids
            ]
            
            if not orphan_rooms:
                return  # All rooms connected!
            
            # Get list of connected rooms to connect to
            connected_rooms = [
                room for room in dungeon.rooms.values()
                if room.id in connected_room_ids
            ]
            
            # If no rooms are connected yet, pick the first two rooms and connect them
            if not connected_rooms and len(orphan_rooms) >= 2:
                room1 = orphan_rooms[0]
                room2 = orphan_rooms[1]
                passage = self._create_passage(room1, room2, dungeon, allow_partial=True)
                if passage:
                    if self._add_validated_passage(dungeon, passage):
                        connected_room_ids.add(room1.id)
                        connected_room_ids.add(room2.id)
                continue  # Recalculate orphans
            
            made_connection = False
            
            # Try to connect each orphan to nearest connected room
            for orphan in orphan_rooms:
                if not connected_rooms:
                    break
                
                # Sort ALL rooms (connected and orphan) by distance
                all_targets = sorted(
                    [r for r in dungeon.rooms.values() if r.id != orphan.id],
                    key=lambda r: abs(r.center_grid[0] - orphan.center_grid[0]) + 
                                  abs(r.center_grid[1] - orphan.center_grid[1])
                )
                
                # Prioritize connected rooms, but also include nearby orphans
                targets = []
                for t in all_targets[:10]:
                    if t.id in connected_room_ids:
                        targets.insert(0, t)  # Connected rooms first
                    else:
                        targets.append(t)  # Orphans at end
                
                # Try to connect
                for target in targets[:8]:
                    passage = self._create_passage(orphan, target, dungeon, allow_partial=True)
                    if passage:
                        if self._add_validated_passage(dungeon, passage):
                            made_connection = True
                            break
                
                if made_connection:
                    break  # Recalculate in next pass
            
            # If no connections made with strict mode, try partial/longer passages
            if not made_connection:
                for orphan in orphan_rooms:
                    all_targets = sorted(
                        [r for r in dungeon.rooms.values() if r.id != orphan.id],
                        key=lambda r: abs(r.center_grid[0] - orphan.center_grid[0]) + 
                                      abs(r.center_grid[1] - orphan.center_grid[1])
                    )
                    
                    for target in all_targets[:8]:
                        passage = self._create_passage(orphan, target, dungeon, allow_partial=True)
                        if passage:
                            if self._add_validated_passage(dungeon, passage):
                                made_connection = True
                                break
                    
                    if made_connection:
                        break
            
            if not made_connection:
                break  # No progress possible
        
        # Final cleanup: Ensure dungeon is fully connected (single graph component)
        self._ensure_connected(dungeon)
    
    def _cleanup_orphan_passages(self, dungeon: Dungeon) -> None:
        """Remove passages that reference non-existent rooms."""
        orphan_passages = [
            pid for pid, p in dungeon.passages.items()
            if p.start_room not in dungeon.rooms or p.end_room not in dungeon.rooms
        ]
        for pid in orphan_passages:
            del dungeon.passages[pid]
    
    def _find_components(self, dungeon: Dungeon) -> List[set]:
        """Find connected components in the dungeon graph.
        
        Handles both direct room-to-room passages AND T-junctions where
        a passage joins an existing passage (indirectly connecting rooms).
        """
        # First clean up any orphan passages
        self._cleanup_orphan_passages(dungeon)
        
        adjacency = {room_id: set() for room_id in dungeon.rooms}
        
        # Build a map of which passages connect which rooms
        # Direct connections: start_room <-> end_room
        for passage in dungeon.passages.values():
            if passage.start_room in adjacency and passage.end_room in adjacency:
                adjacency[passage.start_room].add(passage.end_room)
                adjacency[passage.end_room].add(passage.start_room)
        
        # Handle T-junctions: if a passage ends at "passage", check if its
        # endpoint physically overlaps with another passage's cells
        passage_cells = {}  # Map of (x,y) -> set of room_ids the passage connects
        for passage in dungeon.passages.values():
            if passage.start_room not in dungeon.rooms:
                continue
            cells = self.occupancy.get_passage_cells(passage.waypoints, passage.width)
            rooms_connected = {passage.start_room}
            if passage.end_room in dungeon.rooms:
                rooms_connected.add(passage.end_room)
            for cell in cells:
                if cell not in passage_cells:
                    passage_cells[cell] = set()
                passage_cells[cell].update(rooms_connected)
        
        # Now find T-junction connections: if two passages share a cell,
        # their connected rooms are indirectly connected
        for cell, rooms in passage_cells.items():
            if len(rooms) > 1:
                rooms_list = list(rooms)
                for i, room1 in enumerate(rooms_list):
                    for room2 in rooms_list[i+1:]:
                        if room1 in adjacency and room2 in adjacency:
                            adjacency[room1].add(room2)
                            adjacency[room2].add(room1)
        
        visited = set()
        components = []
        
        for start_room in dungeon.rooms:
            if start_room in visited:
                continue
            
            component = set()
            queue = [start_room]
            while queue:
                room_id = queue.pop(0)
                if room_id in visited:
                    continue
                visited.add(room_id)
                component.add(room_id)
                for neighbor in adjacency.get(room_id, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            components.append(component)
        
        return components
    
    def _ensure_connected(self, dungeon: Dungeon) -> None:
        """Ensure all rooms are connected. Try to bridge components, then remove unreachable."""
        max_attempts = 10
        
        for attempt in range(max_attempts):
            components = self._find_components(dungeon)
            
            if len(components) <= 1:
                return  # All connected!
            
            # Sort by size (largest first)
            components.sort(key=len, reverse=True)
            main_component = components[0]
            
            # Try to connect smaller components to main
            connected_any = False
            
            for small_component in components[1:]:
                # Find closest room pair between components
                best_pair = None
                best_dist = float('inf')
                
                for main_room_id in main_component:
                    main_room = dungeon.rooms[main_room_id]
                    for small_room_id in small_component:
                        small_room = dungeon.rooms[small_room_id]
                        dist = (abs(main_room.center_grid[0] - small_room.center_grid[0]) + 
                               abs(main_room.center_grid[1] - small_room.center_grid[1]))
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (main_room, small_room)
                
                if best_pair:
                    # Check if already connected
                    if self._are_rooms_connected(best_pair[0].id, best_pair[1].id):
                        # Already connected but in different components? Graph is wrong
                        main_component.update(small_component)
                        connected_any = True
                        break
                    
                    # Try to create passage
                    passage = self._create_passage(best_pair[0], best_pair[1], dungeon, allow_partial=True)
                    if passage:
                        if self._add_validated_passage(dungeon, passage):
                            main_component.update(small_component)
                            connected_any = True
                        break  # Recalculate components
            
            if not connected_any:
                break  # No progress, stop trying
        
        # Final check - remove any remaining disconnected components
        components = self._find_components(dungeon)
        if len(components) > 1:
            largest = max(components, key=len)
            rooms_to_remove = set()
            passages_to_remove = set()
            
            for component in components:
                if component != largest:
                    rooms_to_remove.update(component)
            
            for passage_id, passage in list(dungeon.passages.items()):
                if passage.start_room in rooms_to_remove or passage.end_room in rooms_to_remove:
                    passages_to_remove.add(passage_id)
            
            for room_id in rooms_to_remove:
                del dungeon.rooms[room_id]
            for passage_id in passages_to_remove:
                del dungeon.passages[passage_id]
        
        # Final cleanup - remove any orphan passages that slipped through
        self._cleanup_orphan_passages(dungeon)
    
    def _add_extra_connections(self, dungeon: Dungeon) -> List[Passage]:
        """
        Second pass: Add extra connections after initial layout is complete.
        This implements Jaquaying - creating loops, shortcuts, and alternate paths.
        """
        extra_passages = []
        rooms = list(dungeon.rooms.values())
        
        if len(rooms) < 2:
            return extra_passages
        
        # PASS 1: Extra room-to-room connections
        # Look for nearby rooms that aren't directly connected
        if self.params.extra_room_connections > 0:
            for room in rooms:
                # Find nearby rooms that we're not connected to
                nearby = sorted(
                    [r for r in rooms if r.id != room.id],
                    key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1])
                )[:8]  # Check 8 nearest
                
                for other in nearby:
                    # Check if we can add connection (not already connected)
                    if not self._can_add_connection(room.id, other.id):
                        continue
                    
                    # Random chance to try connection
                    if self.rng.random() > self.params.extra_room_connections:
                        continue
                    
                    # Try to create passage
                    passage = self._create_passage(room, other, dungeon, allow_partial=True)
                    if passage:
                        self._add_validated_passage(dungeon, passage, extra_passages)
        
        # PASS 2: T-junction connections to existing passages
        # Look for rooms near passages that could form T-junctions
        if self.params.extra_passage_junctions > 0:
            for room in rooms:
                # Count how many connections this room has
                room_connection_count = sum(
                    1 for pair in self._connected_pairs 
                    if room.id in pair
                )
                if room_connection_count >= 3:  # Already well-connected
                    continue
                
                # Random chance
                if self.rng.random() > self.params.extra_passage_junctions:
                    continue
                
                # Find nearest room to try passage toward (may hit existing passage)
                nearby = sorted(
                    [r for r in rooms if r.id != room.id],
                    key=lambda r: abs(r.center[0] - room.center[0]) + abs(r.center[1] - room.center[1])
                )[:5]
                
                for other in nearby:
                    # Check if we can add connection
                    if not self._can_add_connection(room.id, other.id):
                        continue
                    
                    # Try partial passage (will hit existing passage for T-junction)
                    passage = self._create_passage(room, other, dungeon, allow_partial=True)
                    if passage and passage.end_room == "passage":
                        if self._add_validated_passage(dungeon, passage, extra_passages):
                            break  # One T-junction per room
        
        return extra_passages
    
    def _mirror_waypoints(self, waypoints: List[Tuple[int, int]], axis_x: float) -> List[Tuple[int, int]]:
        """
        Mirror waypoints across a vertical axis at x = axis_x.
        Each point (x, y) becomes (2*axis_x - x, y).
        """
        if not waypoints:
            return []
        
        mirrored = []
        for x, y in waypoints:
            mirror_x = int(2 * axis_x - x)
            mirrored.append((mirror_x, y))
        
        return mirrored
    
    def _is_valid_passage(self, waypoints: List[Tuple[int, int]], width: int = 1) -> bool:
        """
        Test if waypoints would create a valid passage.
        Does NOT create or mark anything - just validates.
        
        Checks:
        - Waypoints exist and have at least 2 points
        - All segments are axis-aligned (no diagonals)
        - Path doesn't go through blocked cells, rooms, doors, stairs, etc.
        """
        if not waypoints or len(waypoints) < 2:
            return False
        
        # Check axis alignment
        if not self.occupancy.is_valid_waypoints(waypoints):
            return False
        
        # Get all cells the passage would occupy
        cells = self.occupancy.get_passage_cells(waypoints, width)
        
        # Validate against blocked cells, doors, etc.
        cell_string = self.occupancy.get_cell_string(cells)
        return self.occupancy.is_valid_passage_string(cell_string)
    
    def _mark_passage_and_exits(self, passage: Passage) -> bool:
        """
        Validate and mark a passage in the occupancy grid.
        
        Returns False and does NOT mark if validation fails.
        This ensures no invalid passages can be drawn to the occupancy buffer.
        """
        # Validate BEFORE marking
        if not self._is_valid_passage(passage.waypoints, passage.width):
            return False
        
        cells = self.occupancy.get_passage_cells(passage.waypoints, passage.width)
        self.occupancy.mark_passage(passage.start_room + "-" + passage.end_room, cells)
        
        # Mark exit points (first and last waypoints)
        if passage.waypoints:
            p1 = passage.waypoints[0]
            self.occupancy.mark_exit(p1[0], p1[1])
            if len(passage.waypoints) > 1:
                p2 = passage.waypoints[-1]
                self.occupancy.mark_exit(p2[0], p2[1])
        
        # Track connection with its length
        self._track_connection(passage)
        return True
    
    def _add_validated_passage(self, dungeon: Dungeon, passage: Passage, 
                                passages_list: List[Passage] = None,
                                connected_rooms: Set[str] = None) -> bool:
        """
        Validate, add to dungeon, and mark a passage - all in one step.
        
        Only adds the passage if validation passes. This ensures no invalid
        passages end up in the dungeon.
        
        Returns True if passage was added, False if validation failed.
        """
        # Validate FIRST - before adding to dungeon
        if not self._is_valid_passage(passage.waypoints, passage.width):
            return False
        
        # Now safe to add and mark
        if passages_list is not None:
            passages_list.append(passage)
        dungeon.add_passage(passage)
        
        # Mark in occupancy (we already validated, so this should succeed)
        cells = self.occupancy.get_passage_cells(passage.waypoints, passage.width)
        self.occupancy.mark_passage(passage.start_room + "-" + passage.end_room, cells)
        
        # Mark exit points
        if passage.waypoints:
            p1 = passage.waypoints[0]
            self.occupancy.mark_exit(p1[0], p1[1])
            if len(passage.waypoints) > 1:
                p2 = passage.waypoints[-1]
                self.occupancy.mark_exit(p2[0], p2[1])
        
        # Track connection
        self._track_connection(passage)
        
        # Update connected rooms if provided
        if connected_rooms is not None:
            if passage.start_room:
                connected_rooms.add(passage.start_room)
            if passage.end_room:
                connected_rooms.add(passage.end_room)
        
        return True
    
    def _get_passage_length(self, passage: Passage) -> int:
        """Calculate the total length of a passage in grid cells."""
        if not passage.waypoints or len(passage.waypoints) < 2:
            return 0
        
        total = 0
        for i in range(len(passage.waypoints) - 1):
            p1 = passage.waypoints[i]
            p2 = passage.waypoints[i + 1]
            # Manhattan distance (passages are axis-aligned)
            total += abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
        return total
    
    def _track_connection(self, passage: Passage) -> None:
        """Track a connection between two rooms with its passage length."""
        pair = tuple(sorted([passage.start_room, passage.end_room]))
        length = self._get_passage_length(passage)
        
        # Only track if this is the first connection or if it's shorter
        if pair not in self._connected_pairs or length < self._connected_pairs[pair]:
            self._connected_pairs[pair] = length
    
    def _are_rooms_connected(self, room1_id: str, room2_id: str) -> bool:
        """Check if two rooms are already connected."""
        pair = tuple(sorted([room1_id, room2_id]))
        return pair in self._connected_pairs
    
    def _can_add_connection(self, room1_id: str, room2_id: str) -> bool:
        """
        Check if we can add a connection between two rooms.
        Returns False if:
        - They're already connected
        - They have an existing connection > MAX_CONNECTION_LENGTH_FOR_EXTRA grids
        """
        pair = tuple(sorted([room1_id, room2_id]))
        if pair not in self._connected_pairs:
            return True  # Not connected yet, can connect
        
        # Already connected - don't allow duplicate
        return False
    
    def _align_adjacent_exits(self, room1: Room, room2: Room, dir1: str, dir2: str
                              ) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """
        For adjacent rooms, find aligned exit points that allow a direct 2-cell connection.
        Returns (p1, p2) if alignment found, (None, None) otherwise.
        """
        # Get the ranges where exits can be placed (non-corner positions)
        def get_exit_range(room: Room, direction: str) -> Tuple[int, int, int]:
            """Returns (min_pos, max_pos, fixed_coord) for exit positions."""
            if direction in ('north', 'south'):
                # Exits vary along x
                if room.width <= 2:
                    min_pos = room.x
                    max_pos = room.x + room.width - 1
                else:
                    min_pos = room.x + 1
                    max_pos = room.x + room.width - 2
                fixed = room.y - 1 if direction == 'north' else room.y + room.height
                return (min_pos, max_pos, fixed)
            else:
                # Exits vary along y
                if room.height <= 2:
                    min_pos = room.y
                    max_pos = room.y + room.height - 1
                else:
                    min_pos = room.y + 1
                    max_pos = room.y + room.height - 2
                fixed = room.x - 1 if direction == 'west' else room.x + room.width
                return (min_pos, max_pos, fixed)
        
        r1_min, r1_max, r1_fixed = get_exit_range(room1, dir1)
        r2_min, r2_max, r2_fixed = get_exit_range(room2, dir2)
        
        # Check if the fixed coordinates allow a 2-cell connection
        if dir1 in ('east', 'west') and dir2 in ('east', 'west'):
            # Horizontal connection - check if fixed x coords are adjacent
            if abs(r1_fixed - r2_fixed) != 1:
                return (None, None)
            # Find overlapping y range
            overlap_min = max(r1_min, r2_min)
            overlap_max = min(r1_max, r2_max)
            if overlap_min > overlap_max:
                return (None, None)
            # Use middle of overlap
            shared_y = (overlap_min + overlap_max) // 2
            return ((r1_fixed, shared_y), (r2_fixed, shared_y))
        
        elif dir1 in ('north', 'south') and dir2 in ('north', 'south'):
            # Vertical connection - check if fixed y coords are adjacent
            if abs(r1_fixed - r2_fixed) != 1:
                return (None, None)
            # Find overlapping x range
            overlap_min = max(r1_min, r2_min)
            overlap_max = min(r1_max, r2_max)
            if overlap_min > overlap_max:
                return (None, None)
            # Use middle of overlap
            shared_x = (overlap_min + overlap_max) // 2
            return ((shared_x, r1_fixed), (shared_x, r2_fixed))
        
        return (None, None)
    
    def _try_passage_route(self, room1: Room, room2: Room, dir1: str, dir2: str, 
                            turn_offset: int = 0, exit_offset1: int = 0, 
                            exit_offset2: int = 0) -> Tuple[Optional[List[Tuple[int, int]]], Optional[List[Tuple[int, int]]]]:
        """
        Try to create a passage route with given directions, turn offset, and exit offsets.
        Returns (full_waypoints, partial_waypoints):
        - full_waypoints: complete room-to-room path if valid, None otherwise
        - partial_waypoints: room-to-passage path if we hit an existing passage, None otherwise
        """
        MIN_STRAIGHT = 2
        
        p1 = room1.get_edge_point(dir1, exit_offset1)
        p2 = room2.get_edge_point(dir2, exit_offset2)
        
        # Check if exit points are valid (not adjacent to existing exits)
        if not self.occupancy.is_valid_exit(p1[0], p1[1]):
            return (None, None)
        if not self.occupancy.is_valid_exit(p2[0], p2[1]):
            return (None, None)
        
        # For adjacent rooms (potential 2-cell connection), align exit points
        dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
        if dist <= 2:
            # Try to align exits for direct connection
            p1, p2 = self._align_adjacent_exits(room1, room2, dir1, dir2)
            if p1 is None:
                return (None, None)
            # Re-check validity for aligned exits
            if not self.occupancy.is_valid_exit(p1[0], p1[1]):
                return (None, None)
            if not self.occupancy.is_valid_exit(p2[0], p2[1]):
                return (None, None)
        
        waypoints = [p1]
        
        # Check if aligned (straight passage)
        if p1[0] == p2[0] or p1[1] == p2[1]:
            waypoints.append(p2)
        else:
            # L-bend needed
            if dir1 in ('east', 'west'):
                # Horizontal exit from room1
                if dir1 == 'east':
                    mid_x = max(p1[0] + MIN_STRAIGHT, (p1[0] + p2[0]) // 2 + turn_offset)
                else:
                    mid_x = min(p1[0] - MIN_STRAIGHT, (p1[0] + p2[0]) // 2 + turn_offset)
                
                wp1 = (mid_x, p1[1])
                wp2 = (mid_x, p2[1])
                waypoints.append(wp1)
                if wp1[1] != wp2[1]:
                    waypoints.append(wp2)
            else:
                # Vertical exit from room1
                if dir1 == 'south':
                    mid_y = max(p1[1] + MIN_STRAIGHT, (p1[1] + p2[1]) // 2 + turn_offset)
                else:
                    mid_y = min(p1[1] - MIN_STRAIGHT, (p1[1] + p2[1]) // 2 + turn_offset)
                
                wp1 = (p1[0], mid_y)
                wp2 = (p2[0], mid_y)
                waypoints.append(wp1)
                if wp1[0] != wp2[0]:
                    waypoints.append(wp2)
            
            waypoints.append(p2)
        
        # Validate waypoints are axis-aligned (no diagonals)
        if not self.occupancy.is_valid_waypoints(waypoints):
            return (None, None)
        
        # Get cells and validate
        cells = self.occupancy.get_passage_cells(waypoints, self.params.passage_width)
        cell_string = self.occupancy.get_cell_string(cells)
        
        if self.occupancy.is_valid_passage_string(cell_string):
            return (waypoints, None)
        
        # Check if we can create a partial passage (room to existing passage)
        # Find where we first hit a passage (P) and truncate there
        partial_waypoints = self._find_partial_to_passage(p1, waypoints, cells, cell_string)
        
        return (None, partial_waypoints)
    
    def _find_partial_to_passage(self, start: Tuple[int, int], waypoints: List[Tuple[int, int]], 
                                  cells: List[Tuple[int, int]], cell_string: str) -> Optional[List[Tuple[int, int]]]:
        """
        Find a valid partial passage that ends at an existing passage (T-junction).
        Returns truncated waypoints if valid, None otherwise.
        """
        # Find first P in cell string (after initial R)
        first_p = -1
        for i, c in enumerate(cell_string):
            if c == 'P' and i > 0:  # Skip if P is at start
                first_p = i
                break
        
        if first_p < 2:  # Need at least R-E before hitting P, or R-P for adjacent
            return None
        
        # Don't create very long T-junctions (max 10 cells)
        if first_p > 10:
            return None
        
        # Get the cell where we hit the passage
        hit_cell = cells[first_p]
        
        # Truncate cells to just before the P
        truncated_cells = cells[:first_p]
        truncated_string = cell_string[:first_p]
        
        # Add the P cell as endpoint (the T-junction)
        truncated_cells.append(hit_cell)
        truncated_string += 'P'
        
        # Validate: should be R...EP (reserved, empties, then one passage)
        # We allow ending on P (the junction point)
        if 'O' in truncated_string[:-1]:  # No rooms except maybe at connection
            return None
        if 'PP' in truncated_string[:-1]:  # No double passage before the junction
            return None
        if 'RR' in truncated_string and len(truncated_string) > 2:  # No RR except for 2-cell
            return None
        
        # Build waypoints to the hit cell
        # Find waypoints that lead to the hit_cell following the original path
        partial = [start]
        
        # Walk through original waypoints and find where hit_cell would be
        for i in range(len(waypoints) - 1):
            wp_start = waypoints[i]
            wp_end = waypoints[i + 1]
            
            # Check if hit_cell is on this segment
            if wp_start[0] == wp_end[0]:  # Vertical segment
                if hit_cell[0] == wp_start[0]:
                    min_y = min(wp_start[1], wp_end[1])
                    max_y = max(wp_start[1], wp_end[1])
                    if min_y <= hit_cell[1] <= max_y:
                        # Hit cell is on this segment
                        if wp_start != start:
                            partial.append(wp_start)
                        partial.append(hit_cell)
                        return partial
            else:  # Horizontal segment
                if hit_cell[1] == wp_start[1]:
                    min_x = min(wp_start[0], wp_end[0])
                    max_x = max(wp_start[0], wp_end[0])
                    if min_x <= hit_cell[0] <= max_x:
                        # Hit cell is on this segment
                        if wp_start != start:
                            partial.append(wp_start)
                        partial.append(hit_cell)
                        return partial
            
            # Not on this segment, add waypoint if it's after start
            if wp_start != start:
                partial.append(wp_start)
        
        # Fallback - shouldn't reach here if hit_cell is actually on the path
        return None
    
    # Tunable: How much to penalize longer passages (0 = no preference, higher = prefer shorter)
    PASSAGE_LENGTH_WEIGHT = 1.0
    # Tunable: Max candidates to collect before selecting best (limits search time)
    MAX_PASSAGE_CANDIDATES = 20
    
    def _passage_length(self, waypoints: List[Tuple[int, int]]) -> int:
        """Calculate total length of a passage from its waypoints."""
        total = 0
        for i in range(len(waypoints) - 1):
            p1, p2 = waypoints[i], waypoints[i + 1]
            total += abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
        return total
    
    def _create_passage(self, room1: Room, room2: Room, dungeon: Dungeon, 
                        allow_partial: bool = True) -> Optional[Passage]:
        """
        Create a passage between two rooms. Tries multiple routes and selects
        the shortest valid one (soft preference for shorter passages).
        Priority: 1) Straight connections, 2) Shortest L-bend, 3) Partial to passage (T-junction)
        """
        # Don't create self-loop passages
        if room1.id == room2.id:
            return None
        
        # Don't create duplicate passages
        if self._are_rooms_connected(room1.id, room2.id):
            return None
        
        c1 = room1.center
        c2 = room2.center
        dx = c2[0] - c1[0]
        dy = c2[1] - c1[1]
        
        # PHASE 1: Try straight connections first (most preferred - always shortest)
        straight_result = self._try_straight_connection(room1, room2)
        if straight_result:
            # Validate no diagonals
            if not self.occupancy.is_valid_waypoints(straight_result):
                print(f"WARNING: Diagonal in create_passage straight: {straight_result}")
            else:
                return Passage(
                    start_room=room1.id,
                    end_room=room2.id,
                    waypoints=straight_result,
                    width=self.params.passage_width,
                    style=PassageStyle.STRAIGHT
                )
        
        # PHASE 2: Collect L-bend candidates and select shortest
        candidates = []  # [(length, waypoints), ...]
        best_partial = None
        best_partial_length = float('inf')
        
        dir_options = []
        if abs(dx) > abs(dy):
            if dx > 0:
                dir_options.append(('east', 'west'))
                dir_options.append(('south', 'north') if dy > 0 else ('north', 'south'))
            else:
                dir_options.append(('west', 'east'))
                dir_options.append(('south', 'north') if dy > 0 else ('north', 'south'))
        else:
            if dy > 0:
                dir_options.append(('south', 'north'))
                dir_options.append(('east', 'west') if dx > 0 else ('west', 'east'))
            else:
                dir_options.append(('north', 'south'))
                dir_options.append(('east', 'west') if dx > 0 else ('west', 'east'))
        
        all_dirs = [('north', 'south'), ('south', 'north'), ('east', 'west'), ('west', 'east')]
        for d in all_dirs:
            if d not in dir_options:
                dir_options.append(d)
        
        turn_offsets = [0, -2, 2, -4, 4, -6, 6, -10, 10]
        exit_offsets = [0, -1, 1, -2, 2, -3, 3]
        
        for dir1, dir2 in dir_options:
            for turn_off in turn_offsets:
                for exit_off in exit_offsets:
                    full_waypoints, partial_waypoints = self._try_passage_route(
                        room1, room2, dir1, dir2, turn_off, exit_off, exit_off
                    )
                    if full_waypoints:
                        length = self._passage_length(full_waypoints)
                        candidates.append((length, full_waypoints))
                        # Early exit if we have enough short candidates
                        if len(candidates) >= self.MAX_PASSAGE_CANDIDATES:
                            break
                    if partial_waypoints:
                        length = self._passage_length(partial_waypoints)
                        if length < best_partial_length:
                            best_partial = partial_waypoints
                            best_partial_length = length
                if len(candidates) >= self.MAX_PASSAGE_CANDIDATES:
                    break
            if len(candidates) >= self.MAX_PASSAGE_CANDIDATES:
                break
        
        # Select shortest candidate (filter out any with diagonals)
        valid_candidates = [(l, w) for (l, w) in candidates if self.occupancy.is_valid_waypoints(w)]
        if valid_candidates:
            valid_candidates.sort(key=lambda x: x[0] * self.PASSAGE_LENGTH_WEIGHT)
            best_waypoints = valid_candidates[0][1]
            style = PassageStyle.STRAIGHT if len(best_waypoints) == 2 else PassageStyle.L_BEND
            return Passage(
                start_room=room1.id,
                end_room=room2.id,
                waypoints=best_waypoints,
                width=self.params.passage_width,
                style=style
            )
        
        # PHASE 3: Partial passage to existing passage (T-junction)
        # Limit T-junction length to avoid weird long U-shaped passages
        MAX_T_JUNCTION_LENGTH = 8
        if allow_partial and best_partial:
            t_length = self._passage_length(best_partial)
            if t_length > MAX_T_JUNCTION_LENGTH:
                return None  # T-junction too long
            # Validate no diagonals
            if not self.occupancy.is_valid_waypoints(best_partial):
                print(f"WARNING: Diagonal in partial passage: {best_partial}")
            else:
                style = PassageStyle.STRAIGHT if len(best_partial) == 2 else PassageStyle.L_BEND
                return Passage(
                    start_room=room1.id,
                    end_room="passage",
                    waypoints=best_partial,
                    width=self.params.passage_width,
                    style=style
                )
        
        return None
    
    def _try_straight_connection(self, room1: Room, room2: Room) -> Optional[List[Tuple[int, int]]]:
        """
        Try to find a straight (2-point) connection between rooms.
        For each valid exit from room1, check if room2 has an aligned valid exit.
        """
        # Check horizontal alignment (east-west connection)
        if room1.x + room1.width <= room2.x or room2.x + room2.width <= room1.x:
            # Rooms don't overlap vertically in x, check for horizontal passage
            if room1.x < room2.x:
                dir1, dir2 = 'east', 'west'
            else:
                dir1, dir2 = 'west', 'east'
            
            result = self._find_aligned_exits(room1, room2, dir1, dir2)
            if result:
                return result
        
        # Check vertical alignment (north-south connection)
        if room1.y + room1.height <= room2.y or room2.y + room2.height <= room1.y:
            if room1.y < room2.y:
                dir1, dir2 = 'south', 'north'
            else:
                dir1, dir2 = 'north', 'south'
            
            result = self._find_aligned_exits(room1, room2, dir1, dir2)
            if result:
                return result
        
        return None
    
    def _find_aligned_exits(self, room1: Room, room2: Room, dir1: str, dir2: str
                           ) -> Optional[List[Tuple[int, int]]]:
        """
        Find aligned exit positions for a straight passage.
        Returns [p1, p2] if valid straight connection found, None otherwise.
        """
        # Use Room's generic methods for consistent handling of all room types
        pos1_list = room1.get_valid_exit_positions(dir1)
        pos2_list = room2.get_valid_exit_positions(dir2)
        fixed1 = room1.get_edge_coord(dir1)
        fixed2 = room2.get_edge_coord(dir2)
        
        # Find overlapping positions (aligned exits)
        overlap = set(pos1_list) & set(pos2_list)
        if not overlap:
            return None
        
        # Try each aligned position, preferring center
        cx1, cy1 = room1.center_grid
        center1 = cx1 if dir1 in ('north', 'south') else cy1
        sorted_overlap = sorted(overlap, key=lambda p: abs(p - center1))
        
        for pos in sorted_overlap:
            if dir1 in ('north', 'south'):
                p1 = (pos, fixed1)
                p2 = (pos, fixed2)
            else:
                p1 = (fixed1, pos)
                p2 = (fixed2, pos)
            
            # Verify points are aligned (same x or same y)
            if p1[0] != p2[0] and p1[1] != p2[1]:
                continue  # Skip misaligned points
            
            # Validate this straight passage
            cells = self.occupancy.get_passage_cells([p1, p2], self.params.passage_width)
            cell_string = self.occupancy.get_cell_string(cells)
            
            if self.occupancy.is_valid_passage_string(cell_string):
                return [p1, p2]
        
        return None
    
    def _try_branch_from_existing_passage(self, room1: Room, room2: Room, 
                                           dungeon: Dungeon) -> Optional[Passage]:
        """
        Try to connect room1 to room2 by branching off an existing passage from room1.
        
        Instead of creating A→(crosses existing A-B)→C, we create:
        - Keep the existing A-B passage
        - Create a T-junction from a point on A-B to C
        
        This avoids redundant crossing passages from the same room.
        """
        # Find existing passages that start or end at room1
        room1_passages = [
            p for p in dungeon.passages.values() 
            if p.start_room == room1.id or p.end_room == room1.id
        ]
        
        if not room1_passages:
            # print(f"DEBUG: No existing passages from {room1.id}")
            return None
        
        c2 = room2.center
        best_branch = None
        best_length = float('inf')
        
        for existing_passage in room1_passages:
            # Get all cells along this passage
            passage_cells = self.occupancy.get_passage_cells(
                existing_passage.waypoints, existing_passage.width
            )
            
            if len(passage_cells) < 3:
                continue  # Too short to branch from
            
            # Find the best branch point - a cell that's aligned with room2
            # We want to branch perpendicular to reach room2
            for branch_cell in passage_cells[1:-1]:  # Skip first/last (exits)
                bx, by = branch_cell
                
                # Determine if we can branch to room2 from here
                # Try each direction perpendicular to the existing passage
                for branch_dir in ['north', 'south', 'east', 'west']:
                    # Try to create a passage from branch_cell to room2
                    branch_waypoints = self._try_branch_to_room(
                        branch_cell, branch_dir, room2
                    )
                    
                    if branch_waypoints:
                        length = self._passage_length(branch_waypoints)
                        if length < best_length:
                            best_length = length
                            best_branch = branch_waypoints
        
        if best_branch:
            # Create a passage from branch point to room2
            # Mark it as starting from "passage" to indicate T-junction
            style = PassageStyle.STRAIGHT if len(best_branch) == 2 else PassageStyle.L_BEND
            return Passage(
                start_room=room1.id,  # Track original room for connectivity
                end_room=room2.id,
                waypoints=best_branch,
                width=self.params.passage_width,
                style=style
            )
        
        return None
    
    def _try_branch_to_room(self, branch_point: Tuple[int, int], branch_dir: str,
                            target_room: Room) -> Optional[List[Tuple[int, int]]]:
        """
        Try to create a passage from a branch point on an existing passage to a target room.
        Returns waypoints if valid, None otherwise.
        """
        bx, by = branch_point
        
        # Determine target direction based on room position
        tx, ty = target_room.center_grid
        
        # Check if this branch direction makes sense
        if branch_dir == 'north' and ty >= by:
            return None  # Target is south, can't branch north
        if branch_dir == 'south' and ty <= by:
            return None
        if branch_dir == 'east' and tx <= bx:
            return None
        if branch_dir == 'west' and tx >= bx:
            return None
        
        # Get valid exit positions on the target room facing the branch point
        opposite_dir = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
        target_dir = opposite_dir[branch_dir]
        
        target_exits = target_room.get_valid_exit_positions(target_dir)
        target_fixed = target_room.get_edge_coord(target_dir)
        
        if not target_exits:
            return None
        
        # Find best exit position (prefer aligned with branch point)
        if branch_dir in ('north', 'south'):
            # Branch is vertical, find exit with matching x
            best_exit_pos = min(target_exits, key=lambda p: abs(p - bx))
            target_point = (best_exit_pos, target_fixed)
        else:
            # Branch is horizontal, find exit with matching y
            best_exit_pos = min(target_exits, key=lambda p: abs(p - by))
            target_point = (target_fixed, best_exit_pos)
        
        # Check if we can reach this exit
        if not self.occupancy.is_valid_exit(target_point[0], target_point[1]):
            return None
        
        # Build waypoints
        # Start from branch_point, go to target_point (may need L-bend)
        if branch_point[0] == target_point[0] or branch_point[1] == target_point[1]:
            # Straight connection
            waypoints = [branch_point, target_point]
        else:
            # Need L-bend
            if branch_dir in ('north', 'south'):
                # Vertical first, then horizontal
                mid_point = (branch_point[0], target_point[1])
            else:
                # Horizontal first, then vertical
                mid_point = (target_point[0], branch_point[1])
            waypoints = [branch_point, mid_point, target_point]
        
        # Validate waypoints
        if not self.occupancy.is_valid_waypoints(waypoints):
            return None
        
        # Validate passage cells
        cells = self.occupancy.get_passage_cells(waypoints, self.params.passage_width)
        cell_string = self.occupancy.get_cell_string(cells)
        
        # For branch passages, starting on 'P' is expected (we're branching from existing passage)
        # So we need a modified validation
        if len(cell_string) > 0 and cell_string[0] == 'P':
            # Remove leading P for validation (we know we're starting from a passage)
            rest_string = cell_string[1:]
            # The rest should be valid: no O, no PP, no RR (except short passages)
            if 'O' in rest_string:
                return None
            if 'PP' in rest_string:
                return None
            if 'RR' in rest_string and len(rest_string) > 2:
                return None
        else:
            # Not starting on a passage cell - unexpected
            return None
        
        return waypoints
    
    def _prune_redundant_crossings(self, dungeon: Dungeon) -> None:
        """
        Detect passage crossings and prune redundant passages.
        
        When two passages from the same room share a crossing point, keep the one
        with the shortest run to its first crossing point.
        """
        passages = list(dungeon.passages.values())
        if len(passages) < 2:
            return
        
        # Step 1: Build passage cell sets and find crossings
        passage_cells = {}  # passage_id -> set of cells
        for passage in passages:
            cells = self.occupancy.get_passage_cells(passage.waypoints, passage.width)
            passage_cells[passage.id] = set(cells)
        
        # Step 2: Find all crossing points between passages
        crossings = {}  # (passage_id1, passage_id2) -> set of crossing cells
        crossing_points = {}  # cell -> list of passage_ids that cross here
        
        passage_ids = list(passage_cells.keys())
        for i, pid1 in enumerate(passage_ids):
            for pid2 in passage_ids[i+1:]:
                shared = passage_cells[pid1] & passage_cells[pid2]
                if shared:
                    pair = tuple(sorted([pid1, pid2]))
                    crossings[pair] = shared
                    for cell in shared:
                        if cell not in crossing_points:
                            crossing_points[cell] = []
                        if pid1 not in crossing_points[cell]:
                            crossing_points[cell].append(pid1)
                        if pid2 not in crossing_points[cell]:
                            crossing_points[cell].append(pid2)
        
        if not crossing_points:
            return  # No crossings to prune
        
        # Step 3: For each room, find passages that share a crossing point
        # and prune redundant ones
        passages_to_remove = set()
        
        # Group passages by their start room
        room_passages = {}  # room_id -> list of passage objects
        for passage in passages:
            if passage.start_room not in room_passages:
                room_passages[passage.start_room] = []
            room_passages[passage.start_room].append(passage)
        
        for room_id, room_psg_list in room_passages.items():
            if len(room_psg_list) < 2:
                continue
            
            # Find passages from this room that share any crossing point
            for crossing_cell, crossing_passage_ids in crossing_points.items():
                # Get passages from this room that go through this crossing
                room_crossing_passages = [
                    p for p in room_psg_list 
                    if p.id in crossing_passage_ids and p.id not in passages_to_remove
                ]
                
                if len(room_crossing_passages) < 2:
                    continue
                
                # Calculate distance to first crossing for each passage
                passage_distances = []
                for passage in room_crossing_passages:
                    dist = self._distance_to_first_crossing(passage, crossing_points)
                    passage_distances.append((dist, passage))
                
                # Sort by distance, keep shortest, mark others for removal
                passage_distances.sort(key=lambda x: x[0])
                for dist, passage in passage_distances[1:]:  # Skip first (shortest)
                    passages_to_remove.add(passage.id)
        
        # Step 4: Remove redundant passages
        for pid in passages_to_remove:
            if pid in dungeon.passages:
                del dungeon.passages[pid]
    
    def _distance_to_first_crossing(self, passage: Passage, 
                                     crossing_points: dict) -> int:
        """
        Calculate the distance along a passage to its first crossing point.
        Returns the number of cells from start to first crossing.
        """
        cells = self.occupancy.get_passage_cells(passage.waypoints, passage.width)
        
        # Walk along waypoints and count cells until we hit a crossing
        total_dist = 0
        for i in range(len(passage.waypoints) - 1):
            p1 = passage.waypoints[i]
            p2 = passage.waypoints[i + 1]
            
            # Calculate cells along this segment
            if p1[0] == p2[0]:  # Vertical
                y_start, y_end = min(p1[1], p2[1]), max(p1[1], p2[1])
                for y in range(y_start, y_end + 1):
                    cell = (p1[0], y)
                    if cell in crossing_points:
                        return total_dist
                    total_dist += 1
            else:  # Horizontal
                x_start, x_end = min(p1[0], p2[0]), max(p1[0], p2[0])
                for x in range(x_start, x_end + 1):
                    cell = (x, p1[1])
                    if cell in crossing_points:
                        return total_dist
                    total_dist += 1
        
        return total_dist  # No crossing found, return total length
    
    # Door generation constants
    DOOR_CHANCE = 0.6          # Chance a room entrance gets a door
    OPEN_DOOR_CHANCE = 0.3     # Chance a door is open vs closed
    
    def _generate_doors(self, dungeon: Dungeon) -> None:
        """
        Generate doors at room entrances/exits.
        
        Doors are placed where passages connect to rooms. Not every entrance
        gets a door - some can be open archways.
        """
        if not dungeon.passages:
            return
        
        # Track which entrance points already have doors
        entrance_points = set()
        
        for passage in dungeon.passages.values():
            # Skip T-junctions (passages to existing passages)
            if passage.end_room == "passage":
                continue
            
            waypoints = passage.waypoints
            if len(waypoints) < 2:
                continue
            
            # Get rooms at each end
            start_room = dungeon.rooms.get(passage.start_room)
            end_room = dungeon.rooms.get(passage.end_room)
            
            # Process start room entrance
            if start_room and len(waypoints) >= 1:
                entry_point = waypoints[0]
                door = self._maybe_create_door(
                    entry_point, start_room, passage, entrance_points, is_start=True
                )
                if door:
                    dungeon.add_door(door)
                    entrance_points.add((entry_point[0], entry_point[1]))
            
            # Process end room entrance
            if end_room and len(waypoints) >= 1:
                entry_point = waypoints[-1]
                door = self._maybe_create_door(
                    entry_point, end_room, passage, entrance_points, is_start=False
                )
                if door:
                    dungeon.add_door(door)
                    entrance_points.add((entry_point[0], entry_point[1]))
    
    def _maybe_create_door(self, entry_point: Tuple[int, int], room: Room, 
                           passage: Passage, existing_entrances: set,
                           is_start: bool) -> Optional[Door]:
        """
        Maybe create a door at an entry point. Returns Door or None.
        """
        # Don't place multiple doors at the same entrance
        if (entry_point[0], entry_point[1]) in existing_entrances:
            return None
        
        # Don't place door adjacent to another door (prevents 2-cell passage issues)
        if self.occupancy.has_adjacent_door(entry_point[0], entry_point[1]):
            return None
        
        # Random chance to have a door
        if self.rng.random() > self.DOOR_CHANCE:
            return None
        
        # Determine door direction based on position relative to room
        direction = self._get_door_direction(entry_point, room)
        
        # Determine door type (open or closed)
        if self.rng.random() < self.OPEN_DOOR_CHANCE:
            door_type = DoorType.OPEN
        else:
            door_type = DoorType.CLOSED
        
        # Mark this cell with DOOR modifier in the grid
        self.occupancy.set_modifier(entry_point[0], entry_point[1], PassageModifier.DOOR)
        
        return Door(
            x=entry_point[0],
            y=entry_point[1],
            direction=direction,
            door_type=door_type,
            room_id=room.id,
            passage_id=passage.id
        )
    
    def _get_door_direction(self, entry_point: Tuple[int, int], room: Room) -> str:
        """Determine which direction a door should face based on entry point and room."""
        rx, ry = room.center_grid
        ex, ey = entry_point
        
        # Door faces outward from room
        dx = ex - rx
        dy = ey - ry
        
        if abs(dx) > abs(dy):
            return 'east' if dx > 0 else 'west'
        else:
            return 'south' if dy > 0 else 'north'
    
    # Stair generation constants
    STAIR_CHANCE = 0.15        # Chance a passage gets stairs
    STAIR_UP_CHANCE = 0.5      # Chance stairs go up vs down
    
    def _generate_stairs(self, dungeon: Dungeon) -> None:
        """
        Generate stairs in passages.
        
        Stairs are placed in the middle of passages, indicating level changes.
        """
        if not dungeon.passages:
            return
        
        for passage in dungeon.passages.values():
            # Skip T-junctions
            if passage.end_room == "passage":
                continue
            
            waypoints = passage.waypoints
            if len(waypoints) < 2:
                continue
            
            # Calculate passage length
            passage_length = 0
            for i in range(len(waypoints) - 1):
                w1, w2 = waypoints[i], waypoints[i + 1]
                passage_length += abs(w2[0] - w1[0]) + abs(w2[1] - w1[1])
            
            # Only place stairs in longer passages (at least 4 cells)
            if passage_length < 4:
                continue
            
            # Random chance to have stairs
            if self.rng.random() > self.STAIR_CHANCE:
                continue
            
            # Find a cell in the middle of the passage
            stair_pos = self._find_passage_midpoint(waypoints)
            if not stair_pos:
                continue
            
            # Determine stair direction (up or down)
            if self.rng.random() < self.STAIR_UP_CHANCE:
                stair_dir = StairDirection.UP
            else:
                stair_dir = StairDirection.DOWN
            
            # Determine orientation based on passage direction at that point
            orientation = self._get_stair_orientation(waypoints, stair_pos)
            
            stair = Stair(
                x=stair_pos[0],
                y=stair_pos[1],
                direction=orientation,
                stair_dir=stair_dir,
                passage_id=passage.id
            )
            dungeon.add_stair(stair)
    
    def _find_passage_midpoint(self, waypoints: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Find a cell near the middle of a passage."""
        # Get all cells in the passage
        cells = []
        for i in range(len(waypoints) - 1):
            w1, w2 = waypoints[i], waypoints[i + 1]
            if w1[0] == w2[0]:  # Vertical segment
                min_y, max_y = min(w1[1], w2[1]), max(w1[1], w2[1])
                for y in range(min_y, max_y + 1):
                    cells.append((w1[0], y))
            else:  # Horizontal segment
                min_x, max_x = min(w1[0], w2[0]), max(w1[0], w2[0])
                for x in range(min_x, max_x + 1):
                    cells.append((x, w1[1]))
        
        if not cells:
            return None
        
        # Return cell near middle (avoid first/last 2 cells near rooms)
        if len(cells) <= 4:
            return None
        
        mid_idx = len(cells) // 2
        return cells[mid_idx]
    
    def _get_stair_orientation(self, waypoints: List[Tuple[int, int]], 
                                pos: Tuple[int, int]) -> str:
        """Determine stair orientation based on passage direction at position."""
        # Find which segment the position is on
        for i in range(len(waypoints) - 1):
            w1, w2 = waypoints[i], waypoints[i + 1]
            
            if w1[0] == w2[0]:  # Vertical segment
                if w1[0] == pos[0]:
                    min_y, max_y = min(w1[1], w2[1]), max(w1[1], w2[1])
                    if min_y <= pos[1] <= max_y:
                        return 'south' if w2[1] > w1[1] else 'north'
            else:  # Horizontal segment
                if w1[1] == pos[1]:
                    min_x, max_x = min(w1[0], w2[0]), max(w1[0], w2[0])
                    if min_x <= pos[0] <= max_x:
                        return 'east' if w2[0] > w1[0] else 'west'
        
        return 'south'  # Default
    
    def _generate_exits(self, dungeon: Dungeon) -> None:
        """
        Generate dungeon entrances and exits.
        
        For spine-based layouts: entrance is created from first spine room (spine_start_room).
        For other layouts: entrance is at an edge/dead-end room.
        After placing entrance, numbers all rooms by distance from entrance.
        
        Entrances are at the END of a passage leading into the dungeon.
        """
        if not dungeon.rooms:
            return
        
        entrance_room = None
        entrance_passage = None
        entrance_pos = None
        entrance_dir = 'north'
        
        # For spine layouts, use the first spine room
        is_spine = getattr(dungeon, 'is_spine_layout', False)
        if is_spine and dungeon.spine_start_room:
            entrance_room = dungeon.rooms.get(dungeon.spine_start_room)
            if entrance_room:
                # Create entrance from this room going north (opposite of spine direction)
                entrance_passage, entrance_pos, entrance_dir = self._create_entrance_passage(
                    entrance_room, dungeon, preferred_dir='north'
                )
        
        # If spine entrance failed or not a spine layout, find an edge room
        if not entrance_passage:
            entrance_room, entrance_passage, entrance_pos, entrance_dir = self._find_edge_room_entrance(dungeon)
        
        if entrance_room and entrance_passage and entrance_pos:
            # Add the entrance passage to dungeon (with validation)
            if not self._add_validated_passage(dungeon, entrance_passage):
                # Entrance passage validation failed - skip entrance
                return
            
            # Create the main entrance at the end of the passage
            main_exit = Exit(
                x=entrance_pos[0],
                y=entrance_pos[1],
                direction=entrance_dir,
                exit_type=ExitType.ENTRANCE,
                room_id=entrance_room.id,
                is_main=True
            )
            dungeon.add_exit(main_exit)
        
        # Number rooms by distance from entrance (or first room if no entrance)
        if entrance_room:
            self._number_rooms_from_entrance(dungeon, entrance_room)
        elif dungeon.rooms:
            # Fallback: number from first room
            first_room = list(dungeon.rooms.values())[0]
            self._number_rooms_from_entrance(dungeon, first_room)
    
    def _find_edge_room_entrance(self, dungeon: Dungeon) -> Tuple[Optional[Room], Optional[Passage], Optional[Tuple[int, int]], str]:
        """
        Find a room at the edge of the map that faces empty space.
        Returns (room, passage, entrance_pos, direction) or (None, None, None, '').
        """
        from .occupancy import CellType
        
        bounds = dungeon.bounds
        rooms = list(dungeon.rooms.values())
        
        # Score rooms by how close they are to the map edge
        def edge_score(room: Room) -> float:
            cx, cy = room.center_grid
            # Distance to nearest edge
            dist_to_left = cx - bounds[0]
            dist_to_right = bounds[2] - cx
            dist_to_top = cy - bounds[1]
            dist_to_bottom = bounds[3] - cy
            return -min(dist_to_left, dist_to_right, dist_to_top, dist_to_bottom)
        
        # Sort rooms by edge score (closest to edge first)
        sorted_rooms = sorted(rooms, key=edge_score, reverse=True)
        
        # Try each room until we find one with a clear entrance path
        for room in sorted_rooms:
            entrance_passage, entrance_pos, entrance_dir = self._create_entrance_passage(room, dungeon)
            if entrance_passage and entrance_pos:
                return (room, entrance_passage, entrance_pos, entrance_dir)
        
        # Last resort: force entrance on the room closest to edge
        if sorted_rooms:
            room = sorted_rooms[0]
            entrance_passage, entrance_pos, entrance_dir = self._force_entrance_passage(room, dungeon)
            return (room, entrance_passage, entrance_pos, entrance_dir)
        
        return (None, None, None, '')
    
    def _force_entrance_passage(self, room: Room, dungeon: Dungeon) -> Tuple[Optional[Passage], Optional[Tuple[int, int]], str]:
        """
        Force an entrance passage from a room, even if it overlaps existing elements.
        Used as last resort to ensure every dungeon has an entrance.
        """
        bounds = dungeon.bounds
        cx, cy = room.center_grid
        
        # Choose direction towards nearest edge
        dist_to_edges = {
            'west': cx - bounds[0],
            'east': bounds[2] - cx,
            'north': cy - bounds[1],
            'south': bounds[3] - cy
        }
        
        # Sort by distance to edge (closest first)
        sorted_dirs = sorted(dist_to_edges.keys(), key=lambda d: dist_to_edges[d])
        
        dir_vectors = {
            'north': (0, -1),
            'south': (0, 1),
            'east': (1, 0),
            'west': (-1, 0)
        }
        
        for direction in sorted_dirs:
            room_exit = room.get_edge_point(direction, 0)
            dx, dy = dir_vectors[direction]
            
            # Create a 3-cell entrance passage
            passage_length = 3
            entrance_x = room_exit[0] + dx * passage_length
            entrance_y = room_exit[1] + dy * passage_length
            
            waypoints = [(entrance_x, entrance_y), (room_exit[0], room_exit[1])]
            
            entrance_passage = Passage(
                start_room="",
                end_room=room.id,
                waypoints=waypoints
            )
            
            return (entrance_passage, (entrance_x, entrance_y), direction)
        
        return (None, None, '')
    
    def _create_entrance_passage(self, room: Room, dungeon: Dungeon, preferred_dir: str = 'north') -> Tuple[Optional[Passage], Optional[Tuple[int, int]], str]:
        """
        Create an entrance passage leading into the dungeon.
        
        For spine-based layouts, the entrance is opposite the spine growth direction.
        Returns (passage, entrance_position, direction) or (None, None, '') if failed.
        
        The entrance passage must not overlap any reserved or occupied grid cells.
        """
        from .occupancy import CellType
        
        # Get the edge point where passage connects to room
        room_exit = room.get_edge_point(preferred_dir, 0)
        
        # Check if this exit is already used
        used_exits = set()
        for passage in dungeon.passages.values():
            if passage.waypoints:
                used_exits.add(passage.waypoints[0])
                used_exits.add(passage.waypoints[-1])
        
        # Try different directions, starting with preferred
        all_dirs = ['north', 'west', 'east', 'south']
        directions = [preferred_dir] + [d for d in all_dirs if d != preferred_dir]
        
        # Direction vectors (pointing outward from room)
        dir_vectors = {
            'north': (0, -1),
            'south': (0, 1),
            'east': (1, 0),
            'west': (-1, 0)
        }
        
        # Try to find a clear path for the entrance
        for try_dir in directions:
            room_exit = room.get_edge_point(try_dir, 0)
            if room_exit in used_exits:
                continue
            
            dx, dy = dir_vectors[try_dir]
            
            # Try different passage lengths (2-5 cells), shorter first
            for passage_length in range(2, 6):
                # Check if all cells along the passage are not occupied by rooms/passages
                # RESERVED cells are OK - they're just buffer zones
                all_clear = True
                
                # Start one cell outside the room
                start_x = room_exit[0] + dx
                start_y = room_exit[1] + dy
                
                for i in range(passage_length):
                    check_x = start_x + dx * i
                    check_y = start_y + dy * i
                    
                    cell_info = self.occupancy.get(check_x, check_y)
                    # Only block on actual occupied cells (ROOM, PASSAGE, DOOR)
                    # RESERVED and EMPTY are fine
                    if cell_info.cell_type in (CellType.ROOM, CellType.PASSAGE, CellType.DOOR):
                        all_clear = False
                        break
                
                if all_clear:
                    # Found a valid entrance direction and length
                    entrance_dir = try_dir
                    
                    # Entrance point is at the far end of the passage
                    entrance_x = start_x + dx * (passage_length - 1)
                    entrance_y = start_y + dy * (passage_length - 1)
                    
                    # Create waypoints - passage goes from entrance all the way to room exit
                    waypoints = [(entrance_x, entrance_y), (room_exit[0], room_exit[1])]
                    
                    # Create the passage
                    entrance_passage = Passage(
                        start_room="",  # No start room - it's the entrance
                        end_room=room.id,
                        waypoints=waypoints
                    )
                    
                    return (entrance_passage, (entrance_x, entrance_y), entrance_dir)
        
        # No valid entrance path found for this room
        return (None, None, '')
    
    def _number_rooms_from_entrance(self, dungeon: Dungeon, entrance_room: Room) -> None:
        """
        Number all rooms sequentially via BFS from entrance room.
        Each room gets a unique number. Entrance room is #1.
        Rooms closer to entrance get lower numbers.
        """
        # Build adjacency graph
        adjacency = {room_id: set() for room_id in dungeon.rooms}
        for passage in dungeon.passages.values():
            if passage.start_room in adjacency and passage.end_room in adjacency:
                adjacency[passage.start_room].add(passage.end_room)
                adjacency[passage.end_room].add(passage.start_room)
        
        # BFS from entrance - assign sequential unique numbers
        visited = set()
        queue = [entrance_room.id]
        room_number = 1
        
        while queue:
            room_id = queue.pop(0)
            if room_id in visited:
                continue
            visited.add(room_id)
            
            if room_id in dungeon.rooms:
                dungeon.rooms[room_id].number = room_number
                room_number += 1
            
            # Add neighbors in sorted order for deterministic numbering
            neighbors = sorted(adjacency.get(room_id, []))
            for neighbor_id in neighbors:
                if neighbor_id not in visited and neighbor_id not in queue:
                    queue.append(neighbor_id)
        
        # Any unvisited rooms get high numbers (shouldn't happen if connected)
        for room in dungeon.rooms.values():
            if room.number == 0:
                room.number = room_number
                room_number += 1
    
    def _apply_archetype(self, dungeon: Dungeon) -> None:
        """Apply archetype-specific modifications."""
        if not dungeon.rooms:
            return
            
        rooms = list(dungeon.rooms.values())
        
        # Tag rooms based on graph position
        # Find room with most connections (potential hub)
        rooms_by_connections = sorted(rooms, key=lambda r: len(r.connections), reverse=True)
        
        if rooms_by_connections:
            # Tag hub room
            rooms_by_connections[0].tags.append('hub')
            
            # Find dead-ends (1 connection)
            for room in rooms:
                if len(room.connections) == 1:
                    room.tags.append('dead_end')
        
        # Archetype-specific tagging
        if self.params.archetype == DungeonArchetype.LAIR:
            # Largest room is the lair
            largest = max(rooms, key=lambda r: r.width * r.height)
            largest.tags.append('lair')
            largest.tags.append('boss')
        
        elif self.params.archetype == DungeonArchetype.TEMPLE:
            # Central room is sanctum
            bounds = dungeon.bounds
            cx = (bounds[0] + bounds[2]) / 2
            cy = (bounds[1] + bounds[3]) / 2
            
            closest = min(rooms, key=lambda r: 
                (r.center[0] - cx)**2 + (r.center[1] - cy)**2)
            closest.tags.append('sanctum')
    
    def _number_rooms(self, dungeon: Dungeon) -> None:
        """Number rooms using branch-cluster algorithm starting from entrance."""
        if not dungeon.rooms:
            return
        
        # Use the numbering algorithm
        numbers = number_dungeon(dungeon)
        
        # Apply numbers to rooms
        for room_id, num in numbers.items():
            if room_id in dungeon.rooms:
                dungeon.rooms[room_id].number = num
    
    def _generate_water(self, dungeon: Dungeon) -> None:
        """Generate water features using noise-based marching squares."""
        try:
            from .water import WaterGenerator
        except ImportError:
            # opensimplex not installed
            return
        
        # Generate water seed
        water_seed = self.rng.randint(0, 2**31)
        dungeon.water_seed = water_seed
        
        # Create water generator
        water_gen = WaterGenerator(water_seed)
        
        # Get dungeon bounds with some padding
        bounds = dungeon.bounds
        
        # Create floor mask using occupancy grid
        def floor_mask(x: float, y: float) -> bool:
            """Return True if position is valid floor (room or passage)."""
            ix, iy = int(x), int(y)
            cell = self.occupancy.get(ix, iy)
            return cell.cell_type in (CellType.ROOM, CellType.PASSAGE)
        
        # Generate water regions
        water_regions = water_gen.generate_water_regions(
            bounds=bounds,
            threshold=self.params.water_threshold,
            resolution=0.25,  # 4 samples per grid cell
            floor_mask=floor_mask,
            min_area=2.0  # Filter tiny pools
        )
        
        # Convert to model WaterRegion and add to dungeon
        for region in water_regions:
            model_region = WaterRegion(
                boundary=region.boundary,
                bounds=region.bounds
            )
            dungeon.water_regions.append(model_region)

