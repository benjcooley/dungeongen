"""Rotation enum for props."""

import math
from enum import Enum
from typing import Union

class Rotation(Enum):
    """Rotation angles for props in 90-degree increments."""
    ROT_0 = 0
    ROT_90 = 90
    ROT_180 = 180
    ROT_270 = 270
    
    @property
    def radians(self) -> float:
        """Get the rotation angle in radians."""
        return math.radians(self.value)
        
    @classmethod
    def from_radians(cls, radians: float) -> 'Rotation':
        """Convert radians to nearest rotation angle.
        
        Args:
            radians: Angle in radians
            
        Returns:
            Nearest Rotation enum value
        """
        # Convert to degrees and normalize to 0-359
        degrees = int(math.degrees(radians)) % 360
        
        # Map to nearest enum value
        if degrees <= 45 or degrees > 315:
            return cls.ROT_0
        elif degrees <= 135:
            return cls.ROT_90  
        elif degrees <= 225:
            return cls.ROT_180
        else:  # degrees <= 315
            return cls.ROT_270
        
    @classmethod
    def from_radians_snapped(cls, radians: float) -> 'Rotation':
        """Convert radians to nearest 90-degree rotation.
        
        Args:
            radians: Angle in radians
            
        Returns:
            Nearest 90-degree Rotation enum value
        """
        # Convert to degrees and normalize to 0-360
        degrees = math.degrees(radians) % 360
        
        # Find nearest 90-degree increment
        nearest = round(degrees / 90) * 90
        
        # Map to enum values
        if nearest == 0 or nearest == 360:
            return cls.ROT_0
        elif nearest == 90:
            return cls.ROT_90
        elif nearest == 180:
            return cls.ROT_180
        else:  # 270
            return cls.ROT_270
