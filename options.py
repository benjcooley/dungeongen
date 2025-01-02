"""Configuration options for the crosshatch pattern generator."""

import math
from dataclasses import dataclass

@dataclass
class Options:
    """Configuration options for the crosshatch pattern generator."""
    
    # Drawing options
    width: int = 400
    height: int = 400
    stroke_width: float = 1.2

    # Pattern options
    num_strokes: int = 3
    spacing: float = 10
    random_angle_variation: float = math.radians(10)
    
    @property
    def poisson_radius(self) -> float:
        """Radius for Poisson disk sampling."""
        return self.spacing * (self.num_strokes - 1)
    
    @property
    def neighbor_radius(self) -> float:
        """Radius for neighbor detection."""
        return self.poisson_radius * 1.5
    
    @property
    def stroke_length(self) -> float:
        """Base length of strokes."""
        return self.poisson_radius * 2
    
    @property
    def min_stroke_length(self) -> float:
        """Minimum allowed stroke length."""
        return self.stroke_length * 0.35
    
    @property
    def random_length_variation(self) -> float:
        """Maximum random variation in stroke length."""
        return 0.1
