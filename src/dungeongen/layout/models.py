"""Core data models for dungeon layout."""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional
import uuid


class RoomShape(Enum):
    RECT = auto()
    SQUARE = auto()
    CIRCLE = auto()
    OCTAGON = auto()
    # Meta-room types (junctions treated as rooms)
    T_JUNCTION = auto()      # 3-way intersection
    CROSS = auto()           # 4-way intersection
    L_CORNER = auto()        # 2-way corner (elbow)


class PassageStyle(Enum):
    STRAIGHT = auto()   # Direct connection, same axis
    L_BEND = auto()     # Single 90° turn
    S_CURVE = auto()    # Snake - multiple turns
    Z_BEND = auto()     # Two 90° turns, diagonal progression
    CROSSING = auto()   # Intersection with another passage
    SECRET = auto()     # Hidden passage (dashed, marked with S)


class DoorType(Enum):
    OPEN = auto()       # Open doorway/archway
    CLOSED = auto()     # Standard closed door
    LOCKED = auto()     # Locked door
    SECRET = auto()     # Hidden door


class StairDirection(Enum):
    UP = auto()         # Stairs going up
    DOWN = auto()       # Stairs going down


class ExitType(Enum):
    ENTRANCE = auto()   # Main dungeon entrance
    EXIT = auto()       # Secondary exit
    STAIRS_UP = auto()  # Stairs leading out (up to surface)
    STAIRS_DOWN = auto()  # Stairs leading deeper


@dataclass
class Exit:
    """An entrance/exit point of the dungeon."""
    x: int              # Grid position (outside the room)
    y: int
    direction: str      # 'north', 'south', 'east', 'west' - direction facing out
    exit_type: ExitType = ExitType.ENTRANCE
    room_id: str = ""   # Room this exit connects to
    is_main: bool = False  # Is this the main entrance?
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Stair:
    """Stairs in a passage indicating level change."""
    x: int              # Grid position
    y: int
    direction: str      # 'north', 'south', 'east', 'west' - orientation
    stair_dir: StairDirection = StairDirection.DOWN  # Up or down
    passage_id: str = ""  # Passage this stair is in
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Door:
    """A door at a room entrance/exit."""
    x: int              # Grid position
    y: int
    direction: str      # 'north', 'south', 'east', 'west' - which way it faces
    door_type: DoorType = DoorType.CLOSED
    room_id: str = ""   # Room this door belongs to
    passage_id: str = ""  # Passage this door connects to
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Room:
    """
    A room in the dungeon.
    
    COORDINATE SYSTEM: (x, y) is ALWAYS the top-left corner of the bounding box,
    for ALL room shapes including circles. This ensures consistency.
    
    - For rectangles: (x, y) is top-left, width/height is size
    - For circles: (x, y) is top-left of bounding box, width=height=diameter
    """
    x: int  # Grid position - ALWAYS top-left corner of bounding box
    y: int
    width: int  # In grid units (diameter for circles)
    height: int
    shape: RoomShape = RoomShape.RECT
    z: int = 0  # Level (0 = ground floor)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tags: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    number: int = 0  # Room number (distance from entrance, 1 = entrance room)
    
    @property
    def center_grid(self) -> Tuple[int, int]:
        """
        Get the center cell of the room in INTEGER grid coordinates.
        For odd-sized rooms, this is the exact center cell.
        For even-sized rooms, this is floor of center.
        """
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def center_world(self) -> Tuple[float, float]:
        """
        Get the center point in WORLD/FLOAT coordinates.
        This is the actual geometric center, which falls at the center of a tile,
        NOT at a tile corner. Use this for rendering and distance calculations.
        """
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Alias for center_world for backward compatibility."""
        return self.center_world
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get bounding box (x1, y1, x2, y2) where x2/y2 are exclusive."""
        # Now consistent for all room types since x,y is always top-left
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def get_valid_exit_positions(self, direction: str) -> List[int]:
        """
        Get list of valid (non-corner) exit positions along the edge in given direction.
        Returns positions along the variable axis (x for north/south, y for east/west).
        
        For circles: only center position is valid.
        For rectangles: all non-corner positions are valid.
        """
        if self.shape == RoomShape.CIRCLE:
            # Circles only exit at center
            cx, cy = self.center_grid
            if direction in ('north', 'south'):
                return [cx]
            else:
                return [cy]
        else:
            # Rectangles: all non-corner positions
            if direction in ('north', 'south'):
                if self.width <= 2:
                    return list(range(self.x, self.x + self.width))
                return list(range(self.x + 1, self.x + self.width - 1))
            else:
                if self.height <= 2:
                    return list(range(self.y, self.y + self.height))
                return list(range(self.y + 1, self.y + self.height - 1))
    
    def get_edge_coord(self, direction: str) -> int:
        """
        Get the coordinate of the reserved cell just outside the room edge.
        Returns the fixed axis coordinate (y for north/south, x for east/west).
        
        This is the "exit row/column" - one cell outside the room boundary.
        """
        if direction == 'north':
            return self.y - 1
        elif direction == 'south':
            return self.y + self.height
        elif direction == 'east':
            return self.x + self.width
        else:  # west
            return self.x - 1
    
    def collides_with(self, other: 'Room', margin: int = 1) -> bool:
        """Check if this room collides with another room."""
        b1 = self.bounds
        b2 = other.bounds
        return not (
            b1[2] + margin <= b2[0] or
            b2[2] + margin <= b1[0] or
            b1[3] + margin <= b2[1] or
            b2[3] + margin <= b1[1]
        )
    
    def get_edge_point(self, direction: str, offset: int = 0) -> Tuple[int, int]:
        """
        Get the TILE coordinate for passage attachment (in tile/grid space).
        Returns the reserved tile just OUTSIDE the room (one tile past the edge).
        
        offset: shift from center (0=center, positive=towards max, negative=towards min)
        For circular rooms, only cardinal center points are valid (offset ignored).
        """
        cx, cy = self.center_grid  # Integer grid center
        
        if self.shape == RoomShape.CIRCLE:
            # Circular rooms: exits only at cardinal center points
            # Now x,y is top-left of bounding box, so center is at (x + width//2, y + height//2)
            # Exit is one cell outside the bounding box at the center position
            if direction == 'north':
                return (cx, self.y - 1)
            elif direction == 'south':
                return (cx, self.y + self.height)
            elif direction == 'east':
                return (self.x + self.width, cy)
            elif direction == 'west':
                return (self.x - 1, cy)
            return (cx, cy)
        else:
            # Rectangular rooms: exits can be at any non-corner position
            # Apply offset from center, clamped to avoid corners
            if direction in ('north', 'south'):
                # Horizontal edge - vary x position
                # Valid range: x+1 to x+width-2 (avoid corners), or any if width <= 2
                if self.width <= 2:
                    exit_x = cx  # No corners to avoid on 2-wide
                else:
                    min_x = self.x + 1  # Avoid left corner
                    max_x = self.x + self.width - 2  # Avoid right corner
                    exit_x = max(min_x, min(max_x, cx + offset))
                
                if direction == 'north':
                    return (exit_x, self.y - 1)
                else:
                    return (exit_x, self.y + self.height)
            else:
                # Vertical edge - vary y position
                # Valid range: y+1 to y+height-2 (avoid corners), or any if height <= 2
                if self.height <= 2:
                    exit_y = cy  # No corners to avoid on 2-tall
                else:
                    min_y = self.y + 1  # Avoid top corner
                    max_y = self.y + self.height - 2  # Avoid bottom corner
                    exit_y = max(min_y, min(max_y, cy + offset))
                
                if direction == 'east':
                    return (self.x + self.width, exit_y)
                else:
                    return (self.x - 1, exit_y)
            return (cx, cy)
    
    @property
    def connection_points(self) -> List[str]:
        """Get available connection directions for this room shape."""
        if self.shape == RoomShape.T_JUNCTION:
            # T has 3 connections - which 3 depends on orientation
            # Default: north, east, west (T pointing down)
            return ['north', 'east', 'west']
        elif self.shape == RoomShape.CROSS:
            return ['north', 'south', 'east', 'west']
        elif self.shape == RoomShape.L_CORNER:
            # L has 2 connections - default: south, east
            return ['south', 'east']
        else:
            # Regular rooms can connect on any side
            return ['north', 'south', 'east', 'west']
    
    @property
    def is_junction(self) -> bool:
        """Check if this room is a junction meta-room."""
        return self.shape in (RoomShape.T_JUNCTION, RoomShape.CROSS, RoomShape.L_CORNER)


@dataclass
class Passage:
    """A passage connecting two rooms."""
    start_room: str  # Room ID
    end_room: str  # Room ID
    waypoints: List[Tuple[int, int]]  # Path points including start and end
    width: int = 1  # Grid units (1 = standard D&D corridor)
    style: PassageStyle = PassageStyle.L_BEND
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    @property
    def segments(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get line segments of the passage."""
        segs = []
        for i in range(len(self.waypoints) - 1):
            segs.append((self.waypoints[i], self.waypoints[i + 1]))
        return segs


@dataclass
class WaterRegion:
    """A water pool with smooth organic boundary."""
    boundary: List[Tuple[float, float]]  # Smoothed polygon points (grid coords)
    bounds: Tuple[float, float, float, float] = (0, 0, 0, 0)  # min_x, min_y, max_x, max_y


@dataclass
class Dungeon:
    """Complete dungeon layout."""
    rooms: Dict[str, Room] = field(default_factory=dict)
    passages: Dict[str, Passage] = field(default_factory=dict)
    doors: Dict[str, Door] = field(default_factory=dict)
    stairs: Dict[str, Stair] = field(default_factory=dict)
    exits: Dict[str, Exit] = field(default_factory=dict)
    water_regions: List['WaterRegion'] = field(default_factory=list)
    seed: int = 0
    water_seed: int = 0
    levels: int = 1
    spine_start_room: Optional[str] = None  # First room of spine (for entrance)
    mirror_pairs: Dict[str, str] = field(default_factory=dict)  # room_id -> mirrored_room_id
    spine_direction: str = 'south'  # Direction spine grows: 'north', 'south', 'east', 'west'
    props_seed: int = 0  # Seed for prop decoration (for symmetry)
    
    def add_room(self, room: Room) -> None:
        """Add a room to the dungeon."""
        self.rooms[room.id] = room
    
    def add_door(self, door: Door) -> None:
        """Add a door to the dungeon."""
        self.doors[door.id] = door
    
    def add_stair(self, stair: Stair) -> None:
        """Add a stair to the dungeon."""
        self.stairs[stair.id] = stair
    
    def add_exit(self, exit: Exit) -> None:
        """Add an exit to the dungeon."""
        self.exits[exit.id] = exit
    
    def add_passage(self, passage: Passage) -> bool:
        """Add a passage to the dungeon. Returns False if duplicate or self-loop."""
        # Don't allow self-loop passages
        if passage.start_room == passage.end_room:
            return False
        
        # Check for duplicate passage between same rooms
        pair = tuple(sorted([passage.start_room, passage.end_room]))
        for existing in self.passages.values():
            existing_pair = tuple(sorted([existing.start_room, existing.end_room]))
            if pair == existing_pair:
                return False  # Duplicate - skip
        
        self.passages[passage.id] = passage
        # Update room connections
        if passage.start_room in self.rooms:
            self.rooms[passage.start_room].connections.append(passage.end_room)
        if passage.end_room in self.rooms:
            self.rooms[passage.end_room].connections.append(passage.start_room)
        return True
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get the bounding box of the entire dungeon."""
        if not self.rooms:
            return (0, 0, 10, 10)
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for room in self.rooms.values():
            b = room.bounds
            min_x = min(min_x, b[0])
            min_y = min(min_y, b[1])
            max_x = max(max_x, b[2])
            max_y = max(max_y, b[3])
        
        # Also consider passage waypoints
        for passage in self.passages.values():
            for wx, wy in passage.waypoints:
                min_x = min(min_x, wx)
                min_y = min(min_y, wy)
                max_x = max(max_x, wx)
                max_y = max(max_y, wy)
        
        return (int(min_x), int(min_y), int(max_x), int(max_y))
    
    def room_at(self, x: int, y: int, z: int = 0) -> Optional[Room]:
        """Find room at given coordinates."""
        for room in self.rooms.values():
            if room.z != z:
                continue
            b = room.bounds
            if b[0] <= x < b[2] and b[1] <= y < b[3]:
                return room
        return None

