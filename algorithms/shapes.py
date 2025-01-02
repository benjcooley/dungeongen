"""Shape definitions for the crosshatch pattern generator."""

import math
from algorithms.types import Point

class Rectangle:
    def __init__(self, x: float, y: float, width: float, height: float, inflate: float = 0) -> None:
        self.x = x  # Original x
        self.y = y  # Original y
        self.width = width  # Original width
        self.height = height  # Original height
        self._inflate = inflate
        self._inflated_x = x - inflate
        self._inflated_y = y - inflate
        self._inflated_width = width + 2 * inflate
        self._inflated_height = height + 2 * inflate

    def contains(self, px: float, py: float) -> bool:
        dx = max(0, abs(px - (self._inflated_x + self._inflated_width / 2)) - self._inflated_width / 2)
        dy = max(0, abs(py - (self._inflated_y + self._inflated_height / 2)) - self._inflated_height / 2)
        return math.sqrt(dx ** 2 + dy ** 2) <= self._inflate

class Circle:
    def __init__(self, cx: float, cy: float, radius: float, inflate: float = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.radius = radius  # Original radius
        self._inflated_radius = radius + inflate

    def contains(self, px: float, py: float) -> bool:
        return math.sqrt((px - self.cx)**2 + (py - self.cy)**2) <= self._inflated_radius
