"""Enumerations used throughout the map package."""

from enum import Enum, auto

class GridStyle(Enum):
    """Available grid drawing styles."""
    NONE = auto()  # No grid
    DOTS = auto()  # Draw grid as dots at intersections

class Layers(Enum):
    """Drawing layers for map elements."""
    SHADOW = auto()  # Shadow layer drawn first
    PROPS = auto()   # Base layer for props and general elements
    DOORS = auto()   # Door layer that draws over room outlines
