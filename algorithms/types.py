"""Type definitions for the crosshatch pattern generator."""

from typing import Tuple, Union
from algorithms.shapes import Rectangle, Circle, ShapeGroup

# Type aliases
Point = Tuple[float, float]
Line = Tuple[Point, Point]
Shape = Union[Rectangle, Circle, ShapeGroup]
