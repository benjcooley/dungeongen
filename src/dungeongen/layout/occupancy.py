"""Occupancy grid for collision detection and pathfinding."""
from typing import Dict, Set, Tuple, List, Optional
from enum import IntEnum
from dataclasses import dataclass


class CellType(IntEnum):
    """What occupies a grid cell. Values 0-15 (4 bits)."""
    EMPTY = 0
    ROOM = 1
    PASSAGE = 2
    WALL = 3        # Room perimeter
    DOOR = 4        # Connection point
    RESERVED = 5    # Reserved for future use (margin around rooms)
    BLOCKED = 6     # Blocked cells (room corners, beside round room exits)


class CellModifier(IntEnum):
    """Special modifiers for cells. Values 0-15 (4 bits)."""
    NONE = 0        # No modifier
    DOOR = 1        # Has a door
    JUNCTION = 2    # T-junction or crossing
    STAIRS = 3      # Has stairs
    EXIT = 4        # Dungeon entrance/exit


# Bit packing: lower 4 bits = CellType, upper 4 bits = CellModifier
# Cell value = (modifier << 4) | cell_type
def pack_cell(cell_type: CellType, modifier: CellModifier = CellModifier.NONE) -> int:
    """Pack cell type and modifier into a single byte."""
    return (modifier << 4) | cell_type


def unpack_cell_type(value: int) -> CellType:
    """Extract cell type from packed value."""
    return CellType(value & 0x0F)


def unpack_modifier(value: int) -> CellModifier:
    """Extract modifier from packed value."""
    return CellModifier((value >> 4) & 0x0F)


# Legacy compatibility - CellInfo still available for element_id tracking
@dataclass
class CellInfo:
    """Information about what occupies a cell (legacy interface)."""
    cell_type: CellType
    element_id: Optional[str] = None  # ID of room or passage
    modifier: CellModifier = CellModifier.NONE  # Special passage modifier
    
    @property
    def packed(self) -> int:
        """Get packed representation."""
        return pack_cell(self.cell_type, self.modifier)


# Backwards compatibility alias
PassageModifier = CellModifier


class _CellsProxy:
    """Proxy for backwards compatibility with code that accesses grid.cells dict."""
    
    def __init__(self, grid: 'OccupancyGrid'):
        self._grid = grid
    
    def __contains__(self, key: Tuple[int, int]) -> bool:
        return key in self._grid._cells
    
    def __getitem__(self, key: Tuple[int, int]) -> CellInfo:
        return self._grid.get(key[0], key[1])
    
    def __setitem__(self, key: Tuple[int, int], value: CellInfo) -> None:
        self._grid.set_cell(key[0], key[1], value.cell_type, value.modifier, value.element_id)
    
    def get(self, key: Tuple[int, int], default=None):
        if key in self._grid._cells:
            return self._grid.get(key[0], key[1])
        return default
    
    def clear(self) -> None:
        self._grid._cells.clear()
        self._grid._element_ids.clear()
    

class OccupancyGrid:
    """
    Grid tracking what occupies each cell.
    Used for collision detection and pathfinding during generation.
    
    Uses packed integers for efficient storage:
    - Lower 4 bits: CellType (0-15)
    - Upper 4 bits: CellModifier (0-15)
    """
    
    def __init__(self):
        # Packed cell values: (x, y) -> packed byte (type + modifier)
        self._cells: Dict[Tuple[int, int], int] = {}
        # Element ID tracking (separate for memory efficiency - only where needed)
        self._element_ids: Dict[Tuple[int, int], str] = {}
        # Group tracking
        self.room_cells: Dict[str, Set[Tuple[int, int]]] = {}  # room_id -> cells
        self.passage_cells: Dict[str, Set[Tuple[int, int]]] = {}  # passage_id -> cells
        self.exit_points: Set[Tuple[int, int]] = set()  # All exit/door cells
        
    def clear(self) -> None:
        """Clear the grid."""
        self._cells.clear()
        self._element_ids.clear()
        self.room_cells.clear()
        self.passage_cells.clear()
        self.exit_points.clear()
    
    def get(self, x: int, y: int) -> CellInfo:
        """Get cell info at position (legacy interface)."""
        pos = (x, y)
        if pos not in self._cells:
            return CellInfo(CellType.EMPTY)
        packed = self._cells[pos]
        return CellInfo(
            cell_type=unpack_cell_type(packed),
            element_id=self._element_ids.get(pos),
            modifier=unpack_modifier(packed)
        )
    
    def get_type(self, x: int, y: int) -> CellType:
        """Get cell type efficiently."""
        pos = (x, y)
        if pos not in self._cells:
            return CellType.EMPTY
        return unpack_cell_type(self._cells[pos])
    
    def get_modifier(self, x: int, y: int) -> CellModifier:
        """Get cell modifier efficiently."""
        pos = (x, y)
        if pos not in self._cells:
            return CellModifier.NONE
        return unpack_modifier(self._cells[pos])
    
    def set_cell(self, x: int, y: int, cell_type: CellType, 
                 modifier: CellModifier = CellModifier.NONE,
                 element_id: Optional[str] = None) -> None:
        """Set cell with type, modifier, and optional element ID."""
        pos = (x, y)
        self._cells[pos] = pack_cell(cell_type, modifier)
        if element_id:
            self._element_ids[pos] = element_id
        elif pos in self._element_ids:
            del self._element_ids[pos]
    
    def set_modifier(self, x: int, y: int, modifier: CellModifier) -> None:
        """Set modifier on existing cell, preserving type."""
        pos = (x, y)
        if pos in self._cells:
            cell_type = unpack_cell_type(self._cells[pos])
            self._cells[pos] = pack_cell(cell_type, modifier)
    
    def is_empty(self, x: int, y: int) -> bool:
        """Check if cell is empty."""
        return (x, y) not in self._cells or unpack_cell_type(self._cells[(x, y)]) == CellType.EMPTY
    
    def get_cell(self, x: int, y: int) -> str:
        """Get cell type as string: 'EMPTY', 'ROOM', 'PASSAGE', 'RESERVED', 'DOOR'."""
        return self.get_type(x, y).name
    
    # Legacy property for backwards compatibility
    @property
    def cells(self) -> Dict[Tuple[int, int], CellInfo]:
        """Legacy cells dict (creates CellInfo objects on access)."""
        return _CellsProxy(self)
    
    def is_passable(self, x: int, y: int) -> bool:
        """Check if cell can be traversed by a passage.
        
        Passages cannot pass through:
        - ROOM cells
        - BLOCKED cells (corners, exit adjacents)
        - DOOR cells (existing door locations)
        - Passages with DOOR or STAIRS modifiers (checked elsewhere)
        """
        cell_type = self.get_type(x, y)
        return cell_type in (CellType.EMPTY, CellType.PASSAGE)
    
    def is_blocked(self, x: int, y: int) -> bool:
        """Check if cell is blocked (corners, exit adjacents)."""
        return self.get_type(x, y) == CellType.BLOCKED
    
    def is_blocking(self, x: int, y: int) -> bool:
        """Check if cell is blocking (passage, room, or blocked cell)."""
        return self.get_type(x, y) in (CellType.PASSAGE, CellType.ROOM, CellType.BLOCKED)
    
    def mark_blocked(self, x: int, y: int, element_id: Optional[str] = None) -> None:
        """Mark a cell as blocked (only if currently empty or reserved)."""
        pos = (x, y)
        current_type = self.get_type(x, y)
        # Only block empty or reserved cells - don't overwrite rooms, passages, doors
        if current_type in (CellType.EMPTY, CellType.RESERVED):
            self.set_cell(x, y, CellType.BLOCKED, element_id=element_id)
    
    def mark_round_room_exit_blocked(self, room_id: str, exit_x: int, exit_y: int, 
                                      direction: str) -> None:
        """
        Mark the two cells beside a round room exit as BLOCKED.
        
        For a round room exit, the cells perpendicular to the exit direction
        should be blocked to prevent passages from entering at bad angles.
        
        Args:
            room_id: ID of the room
            exit_x, exit_y: Position of the exit cell
            direction: Exit direction ('N', 'S', 'E', 'W')
        """
        # Perpendicular offsets based on exit direction
        if direction in ('N', 'S'):
            # Exit goes north/south, block cells to east and west
            self.mark_blocked(exit_x - 1, exit_y, element_id=room_id)
            self.mark_blocked(exit_x + 1, exit_y, element_id=room_id)
        else:  # 'E' or 'W'
            # Exit goes east/west, block cells to north and south
            self.mark_blocked(exit_x, exit_y - 1, element_id=room_id)
            self.mark_blocked(exit_x, exit_y + 1, element_id=room_id)
    
    def is_valid_exit(self, x: int, y: int) -> bool:
        """
        Check if this is a valid exit point.
        Exit points cannot be:
        - At an existing exit point
        - At a cell already occupied (passage, room, or blocked)
        - Adjacent to existing exits
        """
        # Check if this cell is already an exit point
        if (x, y) in self.exit_points:
            return False
        
        # Check if this cell is already occupied by something blocking
        if self.is_blocking(x, y):
            return False
        
        # Check all 8 neighbors (including diagonals)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                neighbor = (x + dx, y + dy)
                if neighbor in self.exit_points:
                    return False
        return True
    
    def mark_exit(self, x: int, y: int) -> None:
        """Mark a cell as an exit point."""
        self.exit_points.add((x, y))
    
    def has_adjacent_door(self, x: int, y: int) -> bool:
        """Check if any adjacent cell (4-directional) has a door modifier."""
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            if self.get_modifier(x + dx, y + dy) == CellModifier.DOOR:
                return True
        return False
    
    def can_place_room(self, x: int, y: int, width: int, height: int, margin: int = 1) -> bool:
        """Check if a room can be placed at position (with margin)."""
        for dx in range(-margin, width + margin):
            for dy in range(-margin, height + margin):
                if not self.is_empty(x + dx, y + dy):
                    return False
        return True
    
    def get_cell_string(self, cells: List[Tuple[int, int]]) -> str:
        """
        Get a string representing the cell types along a path.
        E=Empty, R=Reserved, P=Passage, O=Room, B=Blocked
        D=Door cell or passage with Door modifier, S=Passage with Stairs modifier
        """
        result = []
        for cell in cells:
            cell_type = self.get_type(cell[0], cell[1])
            modifier = self.get_modifier(cell[0], cell[1])
            
            if cell_type == CellType.EMPTY:
                result.append('E')
            elif cell_type == CellType.RESERVED:
                result.append('R')
            elif cell_type == CellType.PASSAGE:
                # Check modifiers on passage cells
                if modifier == CellModifier.DOOR:
                    result.append('D')  # Passage with door - blocking
                elif modifier == CellModifier.STAIRS:
                    result.append('S')  # Passage with stairs - blocking
                else:
                    result.append('P')  # Regular passage
            elif cell_type == CellType.ROOM:
                result.append('O')
            elif cell_type == CellType.BLOCKED:
                result.append('B')
            elif cell_type == CellType.DOOR:
                result.append('D')  # Door cell - blocking
            elif cell_type == CellType.WALL:
                result.append('B')  # Wall cell - blocking (treat same as blocked)
            else:
                result.append('B')  # Unknown - treat as blocked
        return ''.join(result)
    
    def is_valid_passage_string(self, cell_string: str) -> bool:
        """
        Check if a cell string represents a valid passage BEFORE creation.
        
        Must be called BEFORE marking the passage - once marked, cells become 'P'.
        
        Invalid:
        - 'O' anywhere - room cells
        - 'B' anywhere - blocked cells (corners, exit adjacents)
        - 'D' anywhere - door cells
        - 'S' anywhere - stairs cells  
        - 'PP' - two passage cells in a row (would overlap existing passage)
        - 'RRR' or more - three+ reserved cells in a row (running along room margin)
        
        OK:
        - Single 'P' - crossing one existing passage cell
        - Single 'R' - passing through one reserved cell adjacent to room
        - 'RR' - two reserved cells (valid for 2-cell passage between adjacent rooms)
        - 'E' - empty cells
        """
        # A passage must have at least 1 cell
        if len(cell_string) < 1:
            return False
        
        # Room cells
        if 'O' in cell_string:
            return False
        
        # Blocked cells
        if 'B' in cell_string:
            return False
        
        # Door cells
        if 'D' in cell_string:
            return False
        
        # Stairs cells
        if 'S' in cell_string:
            return False
        
        # Overlapping passages (PP = more than single crossing)
        if 'PP' in cell_string:
            return False
        
        # 'RR' is only valid for very short passages (1-2 cells) between adjacent rooms
        # For longer passages, 'RR' means running parallel to a room wall
        if len(cell_string) > 2 and 'RR' in cell_string:
            return False
        
        return True
    
    
    def can_place_passage(self, cells: List[Tuple[int, int]], exclude_rooms: Set[str] = None) -> bool:
        """
        Check if a passage can occupy the given cells.
        Uses cell string validation for pattern checking.
        """
        cell_string = self.get_cell_string(cells)
        return self.is_valid_passage_string(cell_string)
    
    def mark_room(self, room_id: str, x: int, y: int, width: int, height: int, 
                  margin: int = 1, is_circle: bool = False, radius: int = 0) -> None:
        """
        Mark cells as occupied by a room.
        Room interior is ROOM, surrounding buffer is RESERVED.
        Corners of rectangular rooms are BLOCKED.
        No separate wall cells - walls are implied by room edge.
        """
        cells = set()
        
        if is_circle:
            # Circular room - mark cells whose CENTERS are within the circle
            cx = x + width // 2
            cy = y + height // 2
            
            visual_radius = width / 2.0
            visual_r_sq = visual_radius * visual_radius
            margin_radius = visual_radius + margin
            margin_r_sq = margin_radius * margin_radius
            
            check_range = int(visual_radius) + margin + 1
            for dx in range(-check_range, check_range + 1):
                for dy in range(-check_range, check_range + 1):
                    cell = (cx + dx, cy + dy)
                    dist_sq = dx * dx + dy * dy
                    
                    if dist_sq <= visual_r_sq:
                        self.set_cell(cell[0], cell[1], CellType.ROOM, element_id=room_id)
                        cells.add(cell)
                    elif dist_sq <= margin_r_sq:
                        if cell not in self._cells:
                            self.set_cell(cell[0], cell[1], CellType.RESERVED, element_id=room_id)
            
            # Mark blocked cells beside all 4 potential exit positions for round rooms
            # Exits are at: north (cx, y-1), south (cx, y+height), east (x+width, cy), west (x-1, cy)
            # Block perpendicular cells beside each exit
            
            # North exit at (cx, y-1) - block (cx-1, y-1) and (cx+1, y-1)
            self.mark_blocked(cx - 1, y - 1, element_id=room_id)
            self.mark_blocked(cx + 1, y - 1, element_id=room_id)
            
            # South exit at (cx, y+height) - block (cx-1, y+height) and (cx+1, y+height)
            self.mark_blocked(cx - 1, y + height, element_id=room_id)
            self.mark_blocked(cx + 1, y + height, element_id=room_id)
            
            # East exit at (x+width, cy) - block (x+width, cy-1) and (x+width, cy+1)
            self.mark_blocked(x + width, cy - 1, element_id=room_id)
            self.mark_blocked(x + width, cy + 1, element_id=room_id)
            
            # West exit at (x-1, cy) - block (x-1, cy-1) and (x-1, cy+1)
            self.mark_blocked(x - 1, cy - 1, element_id=room_id)
            self.mark_blocked(x - 1, cy + 1, element_id=room_id)
        else:
            # Rectangular room - mark interior
            for dx in range(width):
                for dy in range(height):
                    cell = (x + dx, y + dy)
                    self.set_cell(cell[0], cell[1], CellType.ROOM, element_id=room_id)
                    cells.add(cell)
            
            # Mark margin buffer (RESERVED), except corners which are BLOCKED
            corners = {
                (x - margin, y - margin),           # Top-left corner
                (x + width + margin - 1, y - margin),    # Top-right corner
                (x - margin, y + height + margin - 1),   # Bottom-left corner
                (x + width + margin - 1, y + height + margin - 1)  # Bottom-right corner
            }
            
            for dx in range(-margin, width + margin):
                for dy in range(-margin, height + margin):
                    cell = (x + dx, y + dy)
                    if cell not in self._cells:
                        if cell in corners:
                            self.set_cell(cell[0], cell[1], CellType.BLOCKED, element_id=room_id)
                        else:
                            self.set_cell(cell[0], cell[1], CellType.RESERVED, element_id=room_id)
        
        self.room_cells[room_id] = cells
    
    def mark_door(self, room_id: str, x: int, y: int, width: int = 1,
                  modifier: CellModifier = CellModifier.NONE) -> None:
        """Mark a door/connection point on a room."""
        for dx in range(width):
            self.set_cell(x + dx, y, CellType.DOOR, modifier=modifier, element_id=room_id)
    
    def mark_passage(self, passage_id: str, cells: List[Tuple[int, int]], margin: int = 1,
                     modifier: CellModifier = CellModifier.NONE) -> None:
        """Mark cells as occupied by a passage, plus reserved halo around it."""
        cell_set = set()
        
        # First mark the passage cells
        for cell in cells:
            cell_type = self.get_type(cell[0], cell[1])
            if cell_type not in (CellType.ROOM, CellType.DOOR):
                self.set_cell(cell[0], cell[1], CellType.PASSAGE, modifier=modifier, element_id=passage_id)
            cell_set.add(cell)
        
        # Then mark reserved halo around passage
        for cell in cells:
            for dx in range(-margin, margin + 1):
                for dy in range(-margin, margin + 1):
                    if dx == 0 and dy == 0:
                        continue
                    neighbor = (cell[0] + dx, cell[1] + dy)
                    if neighbor not in self._cells:
                        self.set_cell(neighbor[0], neighbor[1], CellType.RESERVED)
        
        self.passage_cells[passage_id] = cell_set
    
    def get_passage_cells(self, waypoints: List[Tuple[int, int]], width: int) -> List[Tuple[int, int]]:
        """Get all cells that a passage would occupy given its waypoints and width."""
        cells = []
        # For width W, we want exactly W cells centered on the line
        # Offset range: for width=1 -> [0], width=2 -> [0,1], width=3 -> [-1,0,1]
        start_offset = -(width - 1) // 2
        end_offset = width // 2
        
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i + 1]
            
            if p1[0] == p2[0]:  # Vertical segment
                x = int(p1[0])
                y_start, y_end = int(min(p1[1], p2[1])), int(max(p1[1], p2[1]))
                for y in range(y_start, y_end + 1):
                    for dx in range(start_offset, end_offset + 1):
                        cells.append((x + dx, y))
            elif p1[1] == p2[1]:  # Horizontal segment
                y = int(p1[1])
                x_start, x_end = int(min(p1[0], p2[0])), int(max(p1[0], p2[0]))
                for x in range(x_start, x_end + 1):
                    for dy in range(start_offset, end_offset + 1):
                        cells.append((x, y + dy))
            else:
                # DIAGONAL SEGMENT - this should never happen!
                # Log a warning and skip this segment
                print(f"WARNING: Diagonal passage segment detected: {p1} -> {p2}")
                # Don't add any cells for invalid diagonal
        
        return cells
    
    @staticmethod
    def is_valid_waypoints(waypoints: List[Tuple[int, int]]) -> bool:
        """Check that all waypoint segments are axis-aligned (no diagonals)."""
        if len(waypoints) < 2:
            return False
        for i in range(len(waypoints) - 1):
            p1 = waypoints[i]
            p2 = waypoints[i + 1]
            # Must be same x OR same y, not both different
            if p1[0] != p2[0] and p1[1] != p2[1]:
                return False
        return True
    
    def find_path(self, start: Tuple[int, int], end: Tuple[int, int], 
                  allowed_rooms: Set[str] = None, max_iterations: int = 1000) -> Optional[List[Tuple[int, int]]]:
        """
        Find a path from start to end using A* that avoids obstacles.
        Returns list of waypoints (turns), not every cell.
        
        Rules enforced:
        1. No ROOM cells (except start/end in allowed_rooms)
        2. No PP pattern (two passage cells in a row)
        3. No RR pattern (two reserved cells in a row)
        """
        import heapq
        
        allowed_rooms = allowed_rooms or set()
        
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        def get_cell_category(x, y):
            """Get simplified cell category for pattern checking."""
            cell_type = self.get_type(x, y)
            modifier = self.get_modifier(x, y)
            
            if cell_type == CellType.ROOM:
                element_id = self._element_ids.get((x, y))
                return 'O' if element_id not in allowed_rooms else 'A'
            elif cell_type == CellType.BLOCKED:
                return 'B'  # Blocked cells (corners, exit adjacents)
            elif cell_type == CellType.DOOR:
                return 'D'  # Door cells on room boundaries - blocking
            elif cell_type == CellType.PASSAGE:
                # Check for blocking modifiers on passages
                if modifier == CellModifier.DOOR:
                    return 'D'  # Passage with door - blocking
                elif modifier == CellModifier.STAIRS:
                    return 'S'  # Passage with stairs - blocking
                return 'P'
            elif cell_type == CellType.RESERVED:
                return 'R'
            else:  # EMPTY
                return 'E'
        
        def can_move_to(x, y, prev_category):
            """Check if we can move to (x,y) given the previous cell's category."""
            category = get_cell_category(x, y)
            
            # Rule 1: No room cells (except allowed)
            if category == 'O':
                return False, None
            
            # Rule 2: No blocked cells (corners, exit adjacents)
            if category == 'B':
                return False, None
            
            # Rule 3: No door cells (passages with doors)
            if category == 'D':
                return False, None
            
            # Rule 4: No stairs cells (passages with stairs)
            if category == 'S':
                return False, None
            
            # Rule 5: No PP pattern
            if category == 'P' and prev_category == 'P':
                return False, None
            
            # Rule 6: No RR pattern
            if category == 'R' and prev_category == 'R':
                return False, None
            
            return True, category
        
        def can_turn_at(x, y):
            """Check if a passage can turn (change direction) at this cell."""
            cell_type = self.get_type(x, y)
            if cell_type == CellType.EMPTY:
                return True
            if cell_type in (CellType.ROOM, CellType.DOOR):
                element_id = self._element_ids.get((x, y))
                return element_id in allowed_rooms
            return False
        
        # A* search with state = (pos, direction, prev_category)
        start_cat = get_cell_category(start[0], start[1])
        # (f, g, pos, direction, prev_category)
        open_set = [(heuristic(start, end), 0, start, None, start_cat)]
        # State includes position AND previous category to handle pattern rules
        came_from = {(start, start_cat): None}
        g_score = {(start, start_cat): 0}
        
        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            _, g, current, prev_dir, prev_cat = heapq.heappop(open_set)
            
            if current == end:
                # Reconstruct path
                path = []
                state = (current, prev_cat)
                while state is not None:
                    path.append(state[0])
                    state = came_from.get(state)
                path.reverse()
                
                # Simplify to waypoints (only keep turns)
                return self._simplify_path(path)
            
            # Try all 4 directions
            for dx, dy, direction in [(0, -1, 'N'), (0, 1, 'S'), (1, 0, 'E'), (-1, 0, 'W')]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Check if we can move there (pattern rules)
                can_move, new_cat = can_move_to(neighbor[0], neighbor[1], prev_cat)
                if not can_move:
                    continue
                
                # Check if this would be a turn
                is_turn = prev_dir and direction != prev_dir
                
                # If turning, the CURRENT cell must allow turns
                if is_turn and not can_turn_at(current[0], current[1]):
                    continue
                
                # Penalize turns and non-empty cells to prefer clean paths
                turn_cost = 0.5 if is_turn else 0
                cell_cost = 0.2 if new_cat in ('R', 'P') else 0
                tentative_g = g + 1 + turn_cost + cell_cost
                
                state = (neighbor, new_cat)
                if state not in g_score or tentative_g < g_score[state]:
                    g_score[state] = tentative_g
                    f = tentative_g + heuristic(neighbor, end)
                    heapq.heappush(open_set, (f, tentative_g, neighbor, direction, new_cat))
                    came_from[state] = (current, prev_cat)
        
        return None  # No path found
    
    def _simplify_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Simplify a cell-by-cell path to waypoints (only keep turns)."""
        if len(path) <= 2:
            return path
        
        waypoints = [path[0]]
        
        for i in range(1, len(path) - 1):
            prev = path[i - 1]
            curr = path[i]
            next_p = path[i + 1]
            
            # Check if direction changed
            dx1 = curr[0] - prev[0]
            dy1 = curr[1] - prev[1]
            dx2 = next_p[0] - curr[0]
            dy2 = next_p[1] - curr[1]
            
            if (dx1, dy1) != (dx2, dy2):
                waypoints.append(curr)
        
        waypoints.append(path[-1])
        return waypoints
    
    def debug_print(self, bounds: Tuple[int, int, int, int], use_color: bool = True) -> str:
        """Print ASCII representation of the grid for debugging.
        
        Passage modifiers shown as colored letters (override base 'P'):
        - D = Door (red)
        - J = Junction (yellow)
        - S = Stairs (cyan)
        - X = Exit (green)
        - P = Regular passage (white)
        """
        lines = []
        
        # Base type characters
        type_chars = {
            CellType.EMPTY: '.',
            CellType.ROOM: '#',
            CellType.PASSAGE: 'P',
            CellType.WALL: '+',
            CellType.DOOR: 'd',  # lowercase for cell type door
            CellType.RESERVED: ' ',
            CellType.BLOCKED: 'B',  # Blocked corners/exit adjacents
        }
        
        # ANSI color codes
        RESET = '\033[0m' if use_color else ''
        RED = '\033[91m' if use_color else ''
        GREEN = '\033[92m' if use_color else ''
        YELLOW = '\033[93m' if use_color else ''
        CYAN = '\033[96m' if use_color else ''
        
        # Modifier characters with colors (override base char for passages)
        modifier_display = {
            CellModifier.DOOR: (f'{RED}D{RESET}', 'D'),
            CellModifier.JUNCTION: (f'{YELLOW}J{RESET}', 'J'),
            CellModifier.STAIRS: (f'{CYAN}S{RESET}', 'S'),
            CellModifier.EXIT: (f'{GREEN}X{RESET}', 'X'),
        }
        
        for y in range(bounds[1], bounds[3] + 1):
            row = ''
            for x in range(bounds[0], bounds[2] + 1):
                cell_type = self.get_type(x, y)
                modifier = self.get_modifier(x, y)
                
                # If passage has a modifier, show the modifier char instead
                if cell_type == CellType.PASSAGE and modifier != CellModifier.NONE:
                    colored, plain = modifier_display.get(modifier, ('P', 'P'))
                    row += colored if use_color else plain
                else:
                    row += type_chars.get(cell_type, '?')
            lines.append(row)
        
        return '\n'.join(lines)

