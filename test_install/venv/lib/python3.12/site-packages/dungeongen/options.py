"""Configuration options for the crosshatch pattern generator."""

import math
from dataclasses import dataclass, field
from typing import Set
from dungeongen.map.enums import GridStyle

_invalid_options: 'Options'

@dataclass
class Options:
    """Configuration options for the crosshatch pattern generator."""
    
    # Canvas dimensions
    canvas_width: int = 2000
    canvas_height: int = 2000
    
    # Generation tags that influence random distributions
    tags: Set[str] = field(default_factory=set)
    
    # Crosshatch stroke appearance
    crosshatch_stroke_width: float = 1.5
    
    # Crosshatch pattern configuration
    crosshatch_strokes_per_cluster: int = 3
    crosshatch_stroke_spacing: float = 10
    crosshatch_angle_variation: float = math.radians(10)
    
    @property
    def crosshatch_poisson_radius(self) -> float:
        """Radius for Poisson disk sampling of crosshatch clusters."""
        return self.crosshatch_stroke_spacing * (self.crosshatch_strokes_per_cluster - 1)
    
    @property
    def crosshatch_neighbor_radius(self) -> float:
        """Radius for detecting neighboring crosshatch clusters."""
        return self.crosshatch_poisson_radius * 1.5
    
    @property
    def crosshatch_stroke_length(self) -> float:
        """Base length of crosshatch strokes."""
        return self.crosshatch_poisson_radius * 2
    
    @property
    def min_crosshatch_stroke_length(self) -> float:
        """Minimum allowed length for crosshatch strokes."""
        return self.crosshatch_stroke_length * 0.35
    
    @property
    def crosshatch_length_variation(self) -> float:
        """Maximum random variation in crosshatch stroke length."""
        return 0.1
    
    # Rendering options
    crosshatch_border_size: float = 24.0  # Size of crosshatched border around rooms
    crosshatch_background_color: int = 0xFFFFFFFF  # White
    crosshatch_shading_color: int = 0xFFD0D2D5  # Darker gray with subtle blue tint for crosshatch background
    
    # Room rendering options
    room_shadow_color: int = 0xFFD0D0D0  # Lighter gray for room shadows
    room_color: int = 0xFFFFFFFF  # White for room fill
    prop_light_color: int = 0xFFE0E0E0  # Very light gray for props
    prop_fill_color: int = 0xFFFFFFFF  # White for prop fill (same as room_color)
    prop_outline_color: int = 0xFF000000  # Black for prop outline (same as border_color)
    prop_stroke_width: float = 2.0  # Width of prop borders (thinner than door_stroke_width)
    room_shadow_offset_x: float = 6.0   # Shadow x offset in pixels (positive for left)
    room_shadow_offset_y: float = 8.0  # Shadow y offset in pixels (positive for up)
    
    # Grid options
    grid_style: 'GridStyle' = GridStyle.DOTS  # Grid drawing style using dots
    grid_color: int = 0xFF202020  # Very dark gray color for grid
    grid_dot_size: float = 3.0  # Base stroke width for grid dots
    grid_dot_length: float = 1.0  # Base length for grid dots
    grid_dot_variation: float = 0.15  # Random variation in dot length (±15%)
    grid_dots_per_cell: int = 5  # Number of dots to draw per cell
    # Border options
    border_color: int = 0xFF000000  # Black color for region borders
    border_width: float = 6.0  # Width of region borders in pixels
    door_stroke_width: float = 4.0  # Width of door border strokes (2/3 of border_width)
    map_border_cells: float = 4.0  # Number of cells padding around the map

    @staticmethod
    def get_invalid_options() -> 'Options':
        return _invalid_options
    
    @property
    def is_invalid(self) -> bool:
        return self == _invalid_options

_invalid_options = Options()
