"""Rotation class for props that supports both cardinal directions and arbitrary angles."""

import math
from enum import Enum
from typing import Union, Optional

class Rotation:
    """Rotation angles for props supporting both cardinal directions and arbitrary angles.
    
    The class provides both enum-like cardinal direction constants (ROT_0, ROT_90, etc.)
    and support for arbitrary rotation angles.
    
    Examples:
        # Using cardinal directions
        rot = Rotation.ROT_0
        rot = Rotation.ROT_90
        
        # Using arbitrary angles
        rot = Rotation(45)  # 45 degrees
        rot = Rotation.from_radians(math.pi/4)  # 45 degrees
    """
    
    # Cardinal direction constants (set after class def)
    ROT_0: 'Rotation' = None  # type: ignore
    ROT_90: 'Rotation' = None  # type: ignore
    ROT_180: 'Rotation' = None  # type: ignore
    ROT_270: 'Rotation' = None  # type: ignore
    
    def __init__(self, degrees: float) -> None:
        """Initialize with angle in degrees.
        
        Args:
            degrees: Rotation angle in degrees
        """
        self._degrees = degrees % 360
        
    @property
    def degrees(self) -> float:
        """Get the rotation angle in degrees."""
        return self._degrees
        
    @degrees.setter
    def degrees(self, value: float) -> None:
        """Set the rotation angle in degrees."""
        self._degrees = value % 360
        
    @property
    def radians(self) -> float:
        """Get the rotation angle in radians."""
        return math.radians(self._degrees)
        
    @radians.setter 
    def radians(self, value: float) -> None:
        """Set the rotation angle in radians."""
        self._degrees = math.degrees(value) % 360
        
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rotation):
            return NotImplemented
        return abs((self._degrees - other._degrees) % 360) < 0.001
        
    def __str__(self) -> str:
        return f"Rotation({self._degrees}°)"
        
    def __repr__(self) -> str:
        return self.__str__()
        
    @classmethod
    def from_radians(cls, radians: float) -> 'Rotation':
        """Create rotation from angle in radians.
        
        Args:
            radians: Angle in radians
            
        Returns:
            New Rotation instance
        """
        return cls(math.degrees(radians))
        
        
    @classmethod
    def from_degrees(cls, degrees: float) -> 'Rotation':
        """Create rotation from angle in degrees.
        
        Args:
            degrees: Angle in degrees
            
        Returns:
            New Rotation instance
        """
        return cls(degrees)
        
    @classmethod
    def from_radians_snapped(cls, radians: float) -> 'Rotation':
        """Convert radians to nearest 90-degree rotation.
        
        Args:
            radians: Angle in radians
            
        Returns:
            Nearest cardinal Rotation (ROT_0, ROT_90, etc.)
        """
        # Convert to degrees and normalize to 0-360
        degrees = math.degrees(radians) % 360
        
        # Find nearest 90-degree increment
        nearest = round(degrees / 90) * 90
        
        # Map to cardinal rotations
        if nearest == 0 or nearest == 360:
            return cls.ROT_0
        elif nearest == 90:
            return cls.ROT_90
        elif nearest == 180:
            return cls.ROT_180
        else:  # 270
            return cls.ROT_270
            
    @classmethod
    def random_cardinal_rotation(cls) -> 'Rotation':
        """Get a random cardinal rotation (0, 90, 180, or 270 degrees).
        
        Returns:
            Random cardinal Rotation (ROT_0, ROT_90, ROT_180, or ROT_270)
        """
        import random
        return random.choice([cls.ROT_0, cls.ROT_90, cls.ROT_180, cls.ROT_270])

# Initialize cardinal direction constants
Rotation.ROT_0 = Rotation(0)
Rotation.ROT_90 = Rotation(90) 
Rotation.ROT_180 = Rotation(180)
Rotation.ROT_270 = Rotation(270)
