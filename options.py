"""Configuration options for the crosshatch pattern generator."""

import math
from dataclasses import dataclass

@dataclass
class Options:
    """Configuration options for the crosshatch pattern generator."""
    
    # Canvas dimensions
    canvas_width: int = 400
    canvas_height: int = 400
    
    # Crosshatch stroke appearance
    crosshatch_stroke_width: float = 1.2
    
    # Crosshatch pattern configuration
    crosshatch_strokes_per_cluster: int = 3
    crosshatch_stroke_spacing: float = 10
    crosshatch_angle_variation: float = math.radians(10)
    
    @property
    def poisson_radius(self) -> float:
        """Radius for Poisson disk sampling of crosshatch clusters."""
        return self.crosshatch_stroke_spacing * (self.crosshatch_strokes_per_cluster - 1)
    
    @property
    def cluster_neighbor_radius(self) -> float:
        """Radius for detecting neighboring crosshatch clusters."""
        return self.poisson_radius * 1.5
    
    @property
    def crosshatch_stroke_length(self) -> float:
        """Base length of crosshatch strokes."""
        return self.poisson_radius * 2
    
    @property
    def min_crosshatch_stroke_length(self) -> float:
        """Minimum allowed length for crosshatch strokes."""
        return self.crosshatch_stroke_length * 0.35
    
    @property
    def crosshatch_length_variation(self) -> float:
        """Maximum random variation in crosshatch stroke length."""
        return 0.1
