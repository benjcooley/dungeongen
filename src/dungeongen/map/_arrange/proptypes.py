"""Prop type definitions."""

from enum import StrEnum, auto
from typing import TYPE_CHECKING, Type

from dungeongen.graphics.rotation import Rotation

if TYPE_CHECKING:
    from dungeongen.map._props.prop import Prop # type: ignore
    from dungeongen.map._props.rock import Rock # type: ignore

class PropType(StrEnum):
    """Available prop types that can be added to map elements."""
    
    # Rock types
    SMALL_ROCK = auto()
    MEDIUM_ROCK = auto()
    LARGE_ROCK = auto()
    
    # Furniture
    ALTAR = auto()
    COFFIN = auto()
    ROUND_COLUMN = auto()
    SQUARE_COLUMN = auto() 
    DIAS = auto()
    
    @classmethod
    def rock_types(cls) -> list['PropType']:
        """Get all rock prop types."""
        return [cls.SMALL_ROCK, cls.MEDIUM_ROCK, cls.LARGE_ROCK]
        
    def create_prop(self, rotation: Rotation = Rotation.ROT_0) -> 'Prop':
        """Create a new prop instance of this type.
        
        Args:
            rotation: Optional rotation for the prop
            
        Returns:
            New prop instance
            
        Raises:
            ValueError: If prop type is not supported
        """
        if self == PropType.SMALL_ROCK:
            return Rock.create_small()
        elif self == PropType.MEDIUM_ROCK:
            return Rock.create_medium()
        elif self == PropType.LARGE_ROCK:
            return Rock.create_large()
        else:
            raise ValueError(f"Unsupported prop type: {self}")
