"""Enumerations used throughout the map package."""

from enum import Enum, auto
import random

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
