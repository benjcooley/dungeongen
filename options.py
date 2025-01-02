"""Configuration options for the crosshatch pattern generator."""

import math

# Drawing constants
WIDTH: int = 400
HEIGHT: int = 400
STROKE_WIDTH: float = 1.2

# Pattern constants
NUM_STROKES: int = 3
SPACING: float = 10
RANDOM_ANGLE_VARIATION: float = math.radians(10)

# Derived constants
POISSON_RADIUS: float = SPACING * (NUM_STROKES - 1)
NEIGHBOR_RADIUS: float = POISSON_RADIUS * 1.5
STROKE_LENGTH: float = POISSON_RADIUS * 2
MIN_STROKE_LENGTH: float = STROKE_LENGTH * 0.35
RANDOM_LENGTH_VARIATION: float = 0.1
