"""Vector math utilities."""

from __future__ import annotations
import math
from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from graphics.aliases import Point

class Matrix2D:
    """A 2D transformation matrix using row-major order.
    
    The matrix is stored as:
    | a  b  tx |
    | c  d  ty |
    | 0  0  1  |
    
    Where:
    - a, b, c, d define rotation/scale/shear
    - tx, ty define translation
    """
    
    def __init__(self, a: float = 1, b: float = 0, c: float = 0, 
                 d: float = 1, tx: float = 0, ty: float = 0) -> None:
        self.a = a   # Scale X
        self.b = b   # Shear Y
        self.c = c   # Shear X
        self.d = d   # Scale Y
        self.tx = tx # Translate X
        self.ty = ty # Translate Y
    
    @classmethod
    def identity(cls) -> 'Matrix2D':
        """Create an identity matrix."""
        return cls()
    
    @classmethod
    def translation(cls, dx: float, dy: float) -> 'Matrix2D':
        """Create a translation matrix."""
        return cls(tx=dx, ty=dy)
    
    @classmethod
    def rotation(cls, angle: float) -> 'Matrix2D':
        """Create a rotation matrix for angle in radians."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return cls(cos_a, -sin_a, sin_a, cos_a)
    
    @classmethod
    def scale(cls, sx: float, sy: float | None = None) -> 'Matrix2D':
        """Create a scaling matrix."""
        if sy is None:
            sy = sx
        return cls(sx, 0, 0, sy)
    
    def __mul__(self, other: 'Matrix2D') -> 'Matrix2D':
        """Multiply two matrices (this * other)."""
        return Matrix2D(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            tx=self.a * other.tx + self.b * other.ty + self.tx,
            ty=self.c * other.tx + self.d * other.ty + self.ty
        )
    
    def transform_point(self, point: 'Point2D') -> 'Point2D':
        """Transform a point using this matrix."""
        return Point2D(
            self.a * point.x + self.b * point.y + self.tx,
            self.c * point.x + self.d * point.y + self.ty
        )
    
    def transform_points(self, points: List['Point2D']) -> List['Point2D']:
        """Transform multiple points using this matrix."""
        return [self.transform_point(p) for p in points]
    
    def determinant(self) -> float:
        """Calculate the determinant of this matrix."""
        return self.a * self.d - self.b * self.c
    
    def inverted(self) -> 'Matrix2D':
        """Return the inverse of this matrix."""
        det = self.determinant()
        if abs(det) < 1e-6:
            raise ValueError("Matrix is not invertible")
        
        inv_det = 1.0 / det
        return Matrix2D(
            a=self.d * inv_det,
            b=-self.b * inv_det,
            c=-self.c * inv_det,
            d=self.a * inv_det,
            tx=-(self.d * self.tx - self.b * self.ty) * inv_det,
            ty=-(self.a * self.ty - self.c * self.tx) * inv_det
        )

class Point2D:
    """A 2D point/vector with basic vector operations."""
    
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        """Initialize a Point2 with optional coordinates.
        
        Args:
            x: X coordinate (default: 0.0)
            y: Y coordinate (default: 0.0)
        """
        self.x = x
        self.y = y
    
    @classmethod
    def from_point(cls, point: 'Point') -> 'Point2D':
        """Create a Point2D from a Point tuple."""
        return cls(point[0], point[1])
    
    def __add__(self, other: Point) -> 'Point2D':
        return Point2D(self.x + other.x, self.y + other.y)
        
    def __sub__(self, other: Point) -> 'Point2D':
        return Point2D(self.x - other.x, self.y - other.y)
        
    def __mul__(self, scalar: float) -> 'Point2D':
        return Point2D(self.x * scalar, self.y * scalar)
        
    def __truediv__(self, scalar: float) -> 'Point2D':
        return Point2D(self.x / scalar, self.y / scalar)
        
    def __neg__(self) -> 'Point2D':
        """Return negated vector (-x, -y)."""
        return Point2D(-self.x, -self.y)
        
    def dot(self, other: Point) -> float:
        """Compute dot product with another vector."""
        return self.x * other.x + self.y * other.y
        
    def length(self) -> float:
        """Get vector length."""
        return math.sqrt(self.x * self.x + self.y * self.y)
        
    def normalized(self) -> 'Point2D':
        """Get normalized vector (length 1)."""
        length = self.length()
        if length == 0:
            return Point2D(0, 0)
        return self / length
        
    def rotated(self, angle: float) -> 'Point2D':
        """Return vector rotated by angle (in radians)."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Point2D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )
        
    def perpendicular(self) -> 'Point2D':
        """Get perpendicular vector (rotated 90 degrees counterclockwise)."""
        return Point2D(-self.y, self.x)
        
    def to_point(self) -> Tuple[float, float]:
        """Convert to Point tuple."""
        return (self.x, self.y)
