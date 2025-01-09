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

def grid_points_to_grid_rect(start_x: float, start_y: float, end_x: float, end_y: float) -> tuple[float, float, float, float]:
    """Convert two grid points into a proper grid-aligned rectangle.
    
    Takes into account the "off by one" rule when converting grid points to rectangles.
    The end coordinates are adjusted to account for grid cell intervals.
    
    Args:
        start_x: Starting X coordinate in grid units
        start_y: Starting Y coordinate in grid units
        end_x: Ending X coordinate in grid units
        end_y: Ending Y coordinate in grid units
        
    Returns:
        Tuple of (rect_x, rect_y, rect_width, rect_height) in grid units
    """
    # Determine if horizontal or vertical based on which coordinates match
    if start_y == end_y:  # Horizontal
        x = min(start_x, end_x)
        width = abs(end_x - start_x) + 1  # Add 1 to include end cell
        height = 1
        return (x, start_y, width, height)
    elif start_x == end_x:  # Vertical  
        y = min(start_y, end_y)
        width = 1
        height = abs(end_y - start_y) + 1  # Add 1 to include end cell
        return (start_x, y, width, height)
    else:
        raise ValueError(f"Points ({start_x}, {start_y}) and ({end_x}, {end_y}) must form a horizontal or vertical line")

