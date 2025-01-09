"""Utility functions for converting between grid and drawing coordinates."""

from typing import Tuple, TYPE_CHECKING

from altair import Point
from constants import CELL_SIZE
import math

if TYPE_CHECKING:
    from options import Options

def grid_to_map(x: float, y: float) -> Point:
    """Convert grid coordinates to drawing (pixel) coordinates.
    
    Args:
        x: Grid x-coordinate
        y: Grid y-coordinate
        options: Options containing cell_size
        
    Returns:
        Tuple of (map_x, map_y) coordinates
    """
    return (x * CELL_SIZE, y * CELL_SIZE)

def map_to_grid(x: float, y: float, options: 'Options') -> Point:
    """Convert drawing (pixel) coordinates to grid coordinates.
    
    Args:
        x: Map x-coordinate
        y: Map y-coordinate
        options: Options containing cell_size
        
    Returns:
        Tuple of (grid_x, grid_y) coordinates
    """
    return (math.floor(x / CELL_SIZE), math.floor(y / CELL_SIZE))

