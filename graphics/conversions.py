"""Utility functions for converting between grid and drawing coordinates."""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from options import Options

def grid_to_drawing(x: float, y: float, options: 'Options') -> Tuple[float, float]:
    """Convert grid coordinates to drawing (pixel) coordinates.
    
    Args:
        x: Grid x-coordinate
        y: Grid y-coordinate
        options: Options containing cell_size
        
    Returns:
        Tuple of (drawing_x, drawing_y) coordinates
    """
    return (x * options.cell_size, y * options.cell_size)

def drawing_to_grid(x: float, y: float, options: 'Options') -> Tuple[float, float]:
    """Convert drawing (pixel) coordinates to grid coordinates.
    
    Args:
        x: Drawing x-coordinate
        y: Drawing y-coordinate
        options: Options containing cell_size
        
    Returns:
        Tuple of (grid_x, grid_y) coordinates
    """
    return (x / options.cell_size, y / options.cell_size)

def grid_to_drawing_size(width: float, height: float, options: 'Options') -> Tuple[float, float]:
    """Convert grid dimensions to drawing (pixel) dimensions.
    
    Args:
        width: Grid width
        height: Grid height
        options: Options containing cell_size
        
    Returns:
        Tuple of (drawing_width, drawing_height) dimensions
    """
    return (width * options.cell_size, height * options.cell_size)

def drawing_to_grid_size(width: float, height: float, options: 'Options') -> Tuple[float, float]:
    """Convert drawing (pixel) dimensions to grid dimensions.
    
    Args:
        width: Drawing width
        height: Drawing height
        options: Options containing cell_size
        
    Returns:
        Tuple of (grid_width, grid_height) dimensions
    """
    return (width / options.cell_size, height / options.cell_size)
