"""Validator for dungeon layout rules."""
from typing import List, Tuple, Set, Dict
from dataclasses import dataclass
from .models import Dungeon, Room, Passage, RoomShape


@dataclass
class Violation:
    """A rule violation in the dungeon layout."""
    rule: str           # Which rule was violated
    description: str    # Human-readable description
    location: Tuple[int, int]  # Grid coordinates
    severity: str       # 'error' or 'warning'
    element_ids: List[str]  # IDs of involved rooms/passages


class DungeonValidator:
    """Validates dungeon layouts against design rules."""
    
    def __init__(self, dungeon: Dungeon):
        self.dungeon = dungeon
        self.violations: List[Violation] = []
        self.occupancy: Dict[Tuple[int, int], Set[str]] = {}  # grid cell -> element IDs
        
    def validate(self) -> List[Violation]:
        """Run all validation checks and return violations."""
        self.violations = []
        self._build_occupancy_grid()
        
        self._check_room_overlaps()
        self._check_passage_room_overlaps()
        self._check_passage_overlaps()
        self._check_orthogonal_exits()
        self._check_minimum_turn_spacing()
        self._check_round_room_exits()
        
        return self.violations
    
    def _build_occupancy_grid(self) -> None:
        """Build occupancy grid marking which elements occupy each cell."""
        self.occupancy = {}
        
        # Mark room cells
        for room in self.dungeon.rooms.values():
            cells = self._get_room_cells(room)
            for cell in cells:
                if cell not in self.occupancy:
                    self.occupancy[cell] = set()
                self.occupancy[cell].add(f"room:{room.id}")
        
        # Mark passage cells
        for passage in self.dungeon.passages.values():
            cells = self._get_passage_cells(passage)
            for cell in cells:
                if cell not in self.occupancy:
                    self.occupancy[cell] = set()
                self.occupancy[cell].add(f"passage:{passage.id}")
    
    def _get_room_cells(self, room: Room) -> List[Tuple[int, int]]:
        """Get all grid cells occupied by a room."""
        cells = []
        b = room.bounds
        for x in range(b[0], b[2]):
            for y in range(b[1], b[3]):
                if room.shape == RoomShape.CIRCLE:
                    # Check if cell is within circle
                    cx, cy = room.center
                    r = room.width / 2
                    if (x + 0.5 - cx)**2 + (y + 0.5 - cy)**2 <= r**2:
                        cells.append((x, y))
                else:
                    cells.append((x, y))
        return cells
    
    def _get_passage_cells(self, passage: Passage) -> List[Tuple[int, int]]:
        """Get all grid cells occupied by a passage."""
        cells = []
        width = passage.width
        # For width W, we want exactly W cells centered on the line
        start_offset = -(width - 1) // 2
        end_offset = width // 2
        
        for i in range(len(passage.waypoints) - 1):
            p1 = passage.waypoints[i]
            p2 = passage.waypoints[i + 1]
            
            # Get cells along this segment
            if p1[0] == p2[0]:  # Vertical segment
                x = p1[0]
                y_start, y_end = min(p1[1], p2[1]), max(p1[1], p2[1])
                for y in range(int(y_start), int(y_end) + 1):
                    for dx in range(start_offset, end_offset + 1):
                        cells.append((int(x) + dx, y))
            else:  # Horizontal segment
                y = p1[1]
                x_start, x_end = min(p1[0], p2[0]), max(p1[0], p2[0])
                for x in range(int(x_start), int(x_end) + 1):
                    for dy in range(start_offset, end_offset + 1):
                        cells.append((x, int(y) + dy))
        
        return cells
    
    def _check_room_overlaps(self) -> None:
        """Rule 0: Check for room-room overlaps."""
        rooms = list(self.dungeon.rooms.values())
        for i, room1 in enumerate(rooms):
            for room2 in rooms[i+1:]:
                if room1.collides_with(room2, margin=0):
                    cx = (room1.center[0] + room2.center[0]) / 2
                    cy = (room1.center[1] + room2.center[1]) / 2
                    self.violations.append(Violation(
                        rule="Rule 0: No Overlaps",
                        description=f"Rooms {room1.id[:4]} and {room2.id[:4]} overlap",
                        location=(int(cx), int(cy)),
                        severity="error",
                        element_ids=[room1.id, room2.id]
                    ))
    
    def _check_passage_room_overlaps(self) -> None:
        """Rule 0: Check for passage-room overlaps (except at connection points)."""
        for passage in self.dungeon.passages.values():
            passage_cells = set(self._get_passage_cells(passage))
            
            # Get connected room IDs
            connected = {passage.start_room, passage.end_room}
            
            for room in self.dungeon.rooms.values():
                if room.id in connected:
                    continue  # Skip connected rooms
                    
                room_cells = set(self._get_room_cells(room))
                overlap = passage_cells & room_cells
                
                if overlap:
                    loc = list(overlap)[0]
                    self.violations.append(Violation(
                        rule="Rule 0: No Overlaps",
                        description=f"Passage {passage.id[:4]} overlaps room {room.id[:4]}",
                        location=loc,
                        severity="error",
                        element_ids=[passage.id, room.id]
                    ))
    
    def _check_passage_overlaps(self) -> None:
        """Rule 0: Check for unintentional passage-passage overlaps.
        
        Passages meeting at junctions must have valid clearance:
        - At a T-junction, the 4 corner cells around the junction must be empty/reserved
        - At a crossing, similar clearance rules apply
        """
        passages = list(self.dungeon.passages.values())
        
        # Build set of all passage cells for clearance checking
        all_passage_cells = set()
        for p in passages:
            all_passage_cells.update(self._get_passage_cells(p))
        
        # Build set of all room cells
        all_room_cells = set()
        for room in self.dungeon.rooms.values():
            all_room_cells.update(self._get_room_cells(room))
        
        for i, p1 in enumerate(passages):
            cells1 = set(self._get_passage_cells(p1))
            for p2 in passages[i+1:]:
                cells2 = set(self._get_passage_cells(p2))
                overlap = cells1 & cells2
                
                if overlap:
                    # Check each overlap point for valid junction clearance
                    for cell in overlap:
                        if not self._is_valid_junction(cell, all_passage_cells, all_room_cells):
                            self.violations.append(Violation(
                                rule="Rule 0: Invalid Junction",
                                description=f"Junction at {cell} has insufficient clearance",
                                location=cell,
                                severity="error",
                                element_ids=[p1.id, p2.id]
                            ))
    
    def _is_valid_junction(self, junction: Tuple[int, int], 
                           passage_cells: Set[Tuple[int, int]],
                           room_cells: Set[Tuple[int, int]]) -> bool:
        """Check if a junction point has valid clearance.
        
        A valid junction requires the 4 corner cells to be empty (not occupied
        by passages or rooms, except for reserved/blocked cells).
        """
        x, y = junction
        
        # The 4 corner cells around the junction
        corners = [
            (x - 1, y - 1),  # NW
            (x + 1, y - 1),  # NE
            (x - 1, y + 1),  # SW
            (x + 1, y + 1),  # SE
        ]
        
        for corner in corners:
            # Corner must not be occupied by a passage or room
            if corner in passage_cells or corner in room_cells:
                return False
        
        return True
    
    def _check_orthogonal_exits(self) -> None:
        """Rule 1: Check that passages exit rooms orthogonally."""
        for passage in self.dungeon.passages.values():
            if len(passage.waypoints) < 2:
                continue
            
            # Check exit from start room
            start_room = self.dungeon.rooms.get(passage.start_room)
            if start_room:
                p1, p2 = passage.waypoints[0], passage.waypoints[1]
                if not self._is_orthogonal_exit(start_room, p1, p2):
                    self.violations.append(Violation(
                        rule="Rule 1: Orthogonal Exits",
                        description=f"Passage {passage.id[:4]} exits room {start_room.id[:4]} non-orthogonally",
                        location=p1,
                        severity="error",
                        element_ids=[passage.id, start_room.id]
                    ))
            
            # Check exit to end room
            end_room = self.dungeon.rooms.get(passage.end_room)
            if end_room and len(passage.waypoints) >= 2:
                p1 = passage.waypoints[-2]
                p2 = passage.waypoints[-1]
                if not self._is_orthogonal_exit(end_room, p2, p1):
                    self.violations.append(Violation(
                        rule="Rule 1: Orthogonal Exits",
                        description=f"Passage {passage.id[:4]} enters room {end_room.id[:4]} non-orthogonally",
                        location=p2,
                        severity="error",
                        element_ids=[passage.id, end_room.id]
                    ))
    
    def _is_orthogonal_exit(self, room: Room, exit_point: Tuple[int, int], next_point: Tuple[int, int]) -> bool:
        """Check if passage exits room orthogonally (perpendicular to wall)."""
        dx = next_point[0] - exit_point[0]
        dy = next_point[1] - exit_point[1]
        
        # Must be purely horizontal or purely vertical
        if dx != 0 and dy != 0:
            return False  # Diagonal - not orthogonal
        
        return True
    
    def _check_minimum_turn_spacing(self) -> None:
        """Rule 1/3: Check minimum spacing before turns."""
        MIN_SPACING = 1  # At least 1 grid before first turn
        
        for passage in self.dungeon.passages.values():
            if len(passage.waypoints) < 3:
                continue  # No turns
            
            # Check first segment length (exit from room)
            p1, p2 = passage.waypoints[0], passage.waypoints[1]
            dist = abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])
            
            if dist < MIN_SPACING:
                self.violations.append(Violation(
                    rule="Rule 1: Minimum Turn Spacing",
                    description=f"Passage {passage.id[:4]} turns too soon after exit ({dist} < {MIN_SPACING})",
                    location=p2,
                    severity="warning",
                    element_ids=[passage.id]
                ))
    
    def _check_round_room_exits(self) -> None:
        """Rule 2: Check that round rooms only have cardinal exits.
        
        Note: Passages connect to the RESERVED CELL OUTSIDE the room,
        not to the room edge itself. So we check if the exit is at a
        cardinal direction from the room center.
        """
        for room in self.dungeon.rooms.values():
            if room.shape != RoomShape.CIRCLE:
                continue
            
            cx, cy = room.center_grid  # Use integer grid center
            
            # Valid exit points are ONE CELL OUTSIDE the room at cardinal directions
            # The room's get_edge_point returns: (cx, y-1) for north, etc.
            valid_exits = [
                (cx, room.y - 1),           # North (one cell above room)
                (cx, room.y + room.height), # South (one cell below room)
                (room.x + room.width, cy),  # East (one cell right of room)
                (room.x - 1, cy),           # West (one cell left of room)
            ]
            
            # Check passages connected to this room
            for passage in self.dungeon.passages.values():
                if passage.start_room == room.id:
                    exit_point = passage.waypoints[0]
                    if not self._is_near_valid_exit(exit_point, valid_exits, tolerance=0.5):
                        self.violations.append(Violation(
                            rule="Rule 2: Round Room Exits",
                            description=f"Passage {passage.id[:4]} exits round room {room.id[:4]} at non-cardinal point",
                            location=(int(exit_point[0]), int(exit_point[1])),
                            severity="error",
                            element_ids=[passage.id, room.id]
                        ))
                
                if passage.end_room == room.id:
                    exit_point = passage.waypoints[-1]
                    if not self._is_near_valid_exit(exit_point, valid_exits, tolerance=0.5):
                        self.violations.append(Violation(
                            rule="Rule 2: Round Room Exits",
                            description=f"Passage {passage.id[:4]} enters round room {room.id[:4]} at non-cardinal point",
                            location=(int(exit_point[0]), int(exit_point[1])),
                            severity="error",
                            element_ids=[passage.id, room.id]
                        ))
    
    def _is_near_valid_exit(self, point: Tuple[int, int], valid_exits: List[Tuple[float, float]], tolerance: float = 1.0) -> bool:
        """Check if a point is near one of the valid exit points."""
        for valid in valid_exits:
            dist = ((point[0] - valid[0])**2 + (point[1] - valid[1])**2)**0.5
            if dist <= tolerance:
                return True
        return False
    
    def get_violation_cells(self) -> Set[Tuple[int, int]]:
        """Get all cells where violations occur."""
        cells = set()
        for v in self.violations:
            cells.add(v.location)
        return cells
    
    def summary(self) -> str:
        """Get a summary of violations."""
        if not self.violations:
            return "✓ All rules passed"
        
        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]
        
        lines = [f"Found {len(self.violations)} violations:"]
        lines.append(f"  {len(errors)} errors, {len(warnings)} warnings")
        
        for v in self.violations[:10]:  # Show first 10
            lines.append(f"  [{v.severity}] {v.rule}: {v.description}")
        
        if len(self.violations) > 10:
            lines.append(f"  ... and {len(self.violations) - 10} more")
        
        return "\n".join(lines)

