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

def map_to_grid(x: float, y: float) -> Point:
    """Convert drawing (pixel) coordinates to grid coordinates.
    
    Args:
        x: Map x-coordinate
        y: Map y-coordinate
        
    Returns:
        Tuple of (grid_x, grid_y) coordinates
    """
    return (math.floor(x / CELL_SIZE), math.floor(y / CELL_SIZE))

def grid_points_to_grid_rect(start_x: float, start_y: float, end_x: float, end_y: float) -> tuple[float, float, float, float]:
    """Convert two grid points into a proper grid-aligned rectangle.
    
    The x,y coordinates are the minimum values of the start/end points.
    The width/height are calculated as (max - min + 1) to include both end points.
    
    Args:
        start_x: Starting X coordinate in grid units
        start_y: Starting Y coordinate in grid units
        end_x: Ending X coordinate in grid units
        end_y: Ending Y coordinate in grid units
        
    Returns:
        Tuple of (rect_x, rect_y, rect_width, rect_height) in grid units
    """
    # Get min x,y for position
    x = min(start_x, end_x)
    y = min(start_y, end_y)
    
    # Calculate width/height as max - min + 1
    width = abs(max(start_x, end_x) - x) + 1
    height = abs(max(start_y, end_y) - y) + 1
    
    return (x, y, width, height)

def grid_rect_points(rect_x: float, rect_y: float, rect_width: float, rect_height: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Convert a grid rectangle into its corner points.
    
    Args:
        rect_x: Rectangle X coordinate in grid units
        rect_y: Rectangle Y coordinate in grid units
        rect_width: Rectangle width in grid units
        rect_height: Rectangle height in grid units
        
    Returns:
        Tuple of ((x1,y1), (x2,y2)) representing top-left and bottom-right points
    """
    return ((rect_x, rect_y), (rect_x + rect_width - 1, rect_y + rect_height - 1))

def map_rect_points(rect_x: float, rect_y: float, rect_width: float, rect_height: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Convert a map rectangle into its corner points.
    
    Args:
        rect_x: Rectangle X coordinate in map units
        rect_y: Rectangle Y coordinate in map units
        rect_width: Rectangle width in map units
        rect_height: Rectangle height in map units
        
    Returns:
        Tuple of ((x1,y1), (x2,y2)) representing top-left and bottom-right points
    """
    return ((rect_x, rect_y), (rect_x + rect_width, rect_y + rect_height))

