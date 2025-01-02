"""Shape definitions for the crosshatch pattern generator."""

import math
from algorithms.types import Point

class Rectangle:
    def __init__(self, x, y, width, height, inflate=0):
        self.x = x - inflate
        self.y = y - inflate
        self.width = width + 2 * inflate
        self.height = height + 2 * inflate
        self.inflate = inflate

    def contains(self, px, py):
        dx = max(0, abs(px - (self.x + self.width / 2)) - self.width / 2)
        dy = max(0, abs(py - (self.y + self.height / 2)) - self.height / 2)
        return math.sqrt(dx ** 2 + dy ** 2) <= self.inflate

class Circle:
    def __init__(self, cx, cy, radius, inflate = 0):
        self.cx = cx
        self.cy = cy
        self.radius = radius + inflate

    def contains(self, px, py):
        return math.sqrt((px - self.cx)**2 + (py - self.cy)**2) <= self.radius
