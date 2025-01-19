"""Enums for room arrangement strategies."""
from enum import Enum, auto
from typing import Tuple

class RoomDirection(Enum):
    """Direction to generate rooms."""
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
        
    def get_forward(self) -> Tuple[int, int]:
        """Get the (dx, dy) grid offset for this direction."""
        if self == RoomDirection.NORTH:
            return (0, -1)
        elif self == RoomDirection.SOUTH:
            return (0, 1)
        elif self == RoomDirection.EAST:
            return (1, 0)
        else:  # WEST
            return (-1, 0)
        
    def get_left(self) -> Tuple[int, int]:
        """Gets the (dx, dy) grid offset for the left direction."""
        if self == RoomDirection.NORTH:
            return (-1, 0)
        elif self == RoomDirection.SOUTH:
            return (1, 0)
        elif self == RoomDirection.EAST:
            return (0, -1)
        else:
            return (0, 1)  

    def get_opposite(self) -> 'RoomDirection':
        """Get the opposite direction."""
        if self == RoomDirection.NORTH:
            return RoomDirection.SOUTH
        elif self == RoomDirection.SOUTH:
            return RoomDirection.NORTH
        elif self == RoomDirection.EAST:
            return RoomDirection.WEST
        else:
            return RoomDirection.EAST
            
    def is_perpendicular(self, other: 'RoomDirection') -> bool:
        """Check if this direction is perpendicular to another direction."""
        return ((self in (RoomDirection.NORTH, RoomDirection.SOUTH) and 
                other in (RoomDirection.EAST, RoomDirection.WEST)) or
               (self in (RoomDirection.EAST, RoomDirection.WEST) and 
                other in (RoomDirection.NORTH, RoomDirection.SOUTH)))
                
    def is_parallel(self, other: 'RoomDirection') -> bool:
        """Check if this direction is parallel to another direction."""
        return self in (RoomDirection.NORTH, RoomDirection.SOUTH) == \
               other in (RoomDirection.NORTH, RoomDirection.SOUTH)
               
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
