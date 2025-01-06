"""Prop type definitions."""

from enum import StrEnum, auto

class PropType(StrEnum):
    """Available prop types that can be added to map elements."""
    
    # Rock types
    SMALL_ROCK = auto()
    MEDIUM_ROCK = auto()
    LARGE_ROCK = auto()
    
    # Furniture
    ALTAR = auto()
    COFFIN = auto()
    
    @classmethod
    def rock_types(cls) -> list['PropType']:
        """Get all rock prop types."""
        return [cls.SMALL_ROCK, cls.MEDIUM_ROCK, cls.LARGE_ROCK]
