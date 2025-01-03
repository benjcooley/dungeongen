"""Rotation enum for props."""

import math
from enum import Enum

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
