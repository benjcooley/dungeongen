"""Enums for room arrangement strategies."""
from enum import Enum, auto

class RoomDirection(Enum):
    """Direction to generate rooms."""
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

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
