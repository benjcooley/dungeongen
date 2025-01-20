"""Enumerations used throughout the map package."""

from enum import Enum, auto
from typing import Tuple
import random
from typing import Optional

class GridStyle(Enum):
    """Available grid drawing styles."""
    NONE = auto()  # No grid
    DOTS = auto()  # Draw grid as dots at intersections

class Layers(Enum):
    """Drawing layers for map elements."""
    SHADOW = auto()    # Shadow layer drawn first
    PROPS = auto()     # Base layer for props and general elements
    OVERLAY = auto()   # Overlay layer that draws over room outlines (doors, etc)

class RockType(Enum):
    """Types of rocks that can be added to map elements."""
    SMALL = auto()   # Small rocks
    MEDIUM = auto()  # Medium rocks
    ANY = auto()     # Random selection between types
    
    @classmethod
    def random_type(cls) -> 'RockType':
        """Return a random rock type (excluding ANY).
        
        SMALL rocks are twice as likely to be chosen as MEDIUM rocks.
        """
        return random.choice([cls.SMALL, cls.SMALL, cls.MEDIUM])

class Direction(Enum):
    """Cardinal directions for room connections."""
    NORTH = auto()
    SOUTH = auto() 
    EAST = auto()
    WEST = auto()
    
    def get_offset(self) -> Tuple[int, int]:
        """Get the (dx, dy) grid offset for this direction."""
        if self == Direction.NORTH:
            return (0, -1)
        elif self == Direction.SOUTH:
            return (0, 1)
        elif self == Direction.EAST:
            return (1, 0)
        else:  # WEST
            return (-1, 0)

# Pre-computed direction offsets
_DIRECTION_OFFSETS = [
    (0, -1),   # NORTH
    (1, -1),   # NORTHEAST
    (1, 0),    # EAST
    (1, 1),    # SOUTHEAST
    (0, 1),    # SOUTH
    (-1, 1),   # SOUTHWEST
    (-1, 0),   # WEST
    (-1, -1)   # NORTHWEST
]

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

    @classmethod
    def get_offset(cls, direction_value: int) -> Tuple[int, int]:
        """Get the offset tuple for a direction value."""
        return _DIRECTION_OFFSETS[direction_value % 8]

    def get_forward(self) -> Tuple[int, int]:
        """Get the (dx, dy) grid offset for the forward direction."""
        return _DIRECTION_OFFSETS[self.value]
        
    def get_left(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the left direction."""
        return _DIRECTION_OFFSETS[(self.value + 6) % 8]
    
    def get_right(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the right direction."""
        return _DIRECTION_OFFSETS[(self.value + 2) % 8]

    def get_back(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the back direction."""
        return _DIRECTION_OFFSETS[(self.value + 4) % 8]

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
    def from_delta(dx: int, dy: int) -> 'RoomDirection':
        """Convert a delta to a cardinal direction."""
        if dx > 0:
            return RoomDirection.EAST
        elif dx < 0:
            return RoomDirection.WEST
        elif dy > 0:
            return RoomDirection.SOUTH
        else:
            return RoomDirection.NORTH
            
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
