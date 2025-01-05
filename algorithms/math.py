"""Vector math utilities."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple

@dataclass
class Point:
    """A 2D point/vector with basic vector operations."""
    x: float
    y: float
    
    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)
        
    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)
        
    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)
        
    def __truediv__(self, scalar: float) -> Point:
        return Point(self.x / scalar, self.y / scalar)
        
    def __neg__(self) -> Point:
        """Return negated vector (-x, -y)."""
        return Point(-self.x, -self.y)
        
    def dot(self, other: Point) -> float:
        """Compute dot product with another vector."""
        return self.x * other.x + self.y * other.y
        
    def length(self) -> float:
        """Get vector length."""
        return math.sqrt(self.x * self.x + self.y * self.y)
        
    def normalized(self) -> Point:
        """Get normalized vector (length 1)."""
        length = self.length()
        if length == 0:
            return Point(0, 0)
        return self / length
        
    def rotated(self, angle: float) -> Point:
        """Return vector rotated by angle (in radians)."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Point(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )
        
    def perpendicular(self) -> Point:
        """Get perpendicular vector (rotated 90 degrees counterclockwise)."""
        return Point(-self.y, self.x)
        
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (x,y) tuple."""
        return (self.x, self.y)
