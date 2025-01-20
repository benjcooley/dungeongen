"""Enums for room arrangement strategies."""
from enum import Enum, auto
from typing import Tuple, Optional

class RoomDirection(Enum):
    """Direction in map space.
    
    Has both a cardinal direction and a numeric facing value (0-7)
    that aligns with ProbeDirection values for consistent orientation handling.
    """
    NORTH = 0
    NORTHEAST = 1
    EAST = 2
    SOUTHEAST = 3
    SOUTH = 4
    SOUTHWEST = 5
    WEST = 6
    NORTHWEST = 7
        
    # Pre-computed direction offsets
    OFFSETS = [
        (0, -1),   # NORTH
        (1, -1),   # NORTHEAST
        (1, 0),    # EAST
        (1, 1),    # SOUTHEAST
        (0, 1),    # SOUTH
        (-1, 1),   # SOUTHWEST
        (-1, 0),   # WEST
        (-1, -1)   # NORTHWEST
    ]

    def get_forward(self) -> Tuple[int, int]:
        """Get the (dx, dy) grid offset for the forward direction."""
        return self.OFFSETS[self.value]
        
    def get_left(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the left direction."""
        return self.OFFSETS((self.value + 6) % 8)
    
    def get_right(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the right direction."""
        return self.OFFSETS((self.value + 2) % 8)

    def get_back(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the back direction."""
        return self.OFFSETS((self.value +4) % 8)

    def get_opposite(self) -> 'RoomDirection':
        """Get the opposite direction."""
        return RoomDirection((self.value + 4) % 8)
    
    @property
    def is_cardinal(self) -> bool:
        """True if direction is NORTH, SOUTH, EAST, WEST."""
        return self.value % 2 == 0
            
    def is_perpendicular(self, other: 'RoomDirection') -> bool:
        """Check if this direction is perpendicular to another direction."""
        return self.value % 4 != other.value % 4
                
    def is_parallel(self, other: 'RoomDirection') -> bool:
        """Check if this direction is parallel to another direction."""
        return self.value % 4 == other.value % 4
               
    @staticmethod
    def from_points(p1: tuple[int, int], p2: tuple[int, int]) -> Optional['RoomDirection']:
        """Get the direction from p1 to p2 assuming they form a straight line.
        
        Args:
            p1: Starting point (x,y)
            p2: Ending point (x,y)
            
        Returns:
            Direction from p1 to p2, or None if points are same or not in straight line
        """
        x1, y1 = p1
        x2, y2 = p2
        
        if x1 == x2 and y1 == y2:
            return None
            
        if x1 == x2:  # Vertical line
            return RoomDirection.SOUTH if y2 > y1 else RoomDirection.NORTH
        elif y1 == y2:  # Horizontal line
            return RoomDirection.EAST if x2 > x1 else RoomDirection.WEST
        else:
            return None  # Not a straight line
            
    def is_valid_direction_for(self, p1: tuple[int, int], p2: tuple[int, int]) -> bool:
        """Check if this direction is valid for moving from p1 to p2.
        
        Args:
            p1: Starting point (x,y)
            p2: Ending point (x,y)
            
        Returns:
            True if this direction would move from p1 towards p2
        """
        x1, y1 = p1
        x2, y2 = p2
        
        # Points are same - no valid direction
        if x1 == x2 and y1 == y2:
            return False
            
        # Check if direction matches delta
        if self == RoomDirection.EAST and x2 > x1:
            return True
        if self == RoomDirection.WEST and x2 < x1:
            return True
        if self == RoomDirection.SOUTH and y2 > y1:
            return True
        if self == RoomDirection.NORTH and y2 < y1:
            return True
            
        return False

class GrowDirection(Enum):
    """Controls which room to grow from when arranging."""
    FORWARD = auto()   # Only grow from last room
    BACKWARD = auto()  # Only grow from first room
    BOTH = auto()      # Grow from either first or last room

class ArrangeRoomStyle(Enum):
    """Room arrangement strategies."""
    SYMMETRIC = auto()  # Arrange rooms symmetrically where possible
    LINEAR = auto()     # Arrange rooms in a roughly linear path
    SPIRAL = auto()     # Arrange rooms in a spiral pattern from center

class GenerateDirection(Enum):
    """Direction to generate new rooms from."""
    BOTH = auto()      # Generate from either first or last room
    FORWARD = auto()   # Generate only from first room
    BACKWARD = auto()  # Generate only from last room
