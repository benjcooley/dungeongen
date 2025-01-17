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
