"""Enumerations used throughout the map package."""

from enum import Enum, auto

class GridStyle(Enum):
    """Available grid drawing styles."""
    NONE = auto()  # No grid
    DOTS = auto()  # Draw grid as dots at intersections
