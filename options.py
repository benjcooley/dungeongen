"""Configuration options for the crosshatch pattern generator."""

import math
from dataclasses import dataclass
from map.grid import GridStyle

@dataclass
class Options:
    """Configuration options for the crosshatch pattern generator."""
    
    # Map grid configuration
    cell_size: float = 64.0  # Size of one grid square in pixels
    
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
    crosshatch_inflation: float = 16.0  # How much to inflate shapes for crosshatching
    crosshatch_background_color: int = 0xFFFFFFFF  # White
    crosshatch_shading_color: int = 0xFFDDDDDD  # Light gray for crosshatch background
    
    # Room rendering options
    room_shadow_color: int = 0xFFD8D8D8  # Very light gray for room shadows
    room_color: int = 0xFFFFFFFF  # White for room fill
    room_shadow_offset_x: float = -8.0  # Shadow x offset in pixels (negative for right)
    room_shadow_offset_y: float = -8.0  # Shadow y offset in pixels (negative for down)
    
    # Grid options
    grid_style: 'GridStyle' = None  # Grid drawing style (None for no grid)
    grid_color: int = 0xFF808080  # Gray color for grid
    grid_dot_size: float = 1.6  # Size of grid dots (1/20th of cell_size)
    grid_dots_per_cell: int = 5  # Number of dots to draw per cell
    
    # Border options
    border_color: int = 0xFF000000  # Black color for region borders
    border_width: float = 4.0  # Width of region borders in pixels
    map_border_cells: float = 4.0  # Number of cells padding around the map
