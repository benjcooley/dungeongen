"""Utility functions for converting between grid and drawing coordinates."""

from typing import Tuple, TYPE_CHECKING

from altair import Point
from constants import CELL_SIZE
import math

if TYPE_CHECKING:
    from options import Options

def map_from_grid(grid_x: float, grid_y: float) -> Point:
    """Convert grid coordinates to map (pixel) coordinates.
    
    Args:
        grid_x: Grid x-coordinate
        grid_y: Grid y-coordinate
        
    Returns:
        Tuple of (map_x, map_y) coordinates
    """
    return (grid_x * CELL_SIZE, grid_y * CELL_SIZE)

def grid_from_map(map_x: float, map_y: float) -> Point:
    """Convert map (pixel) coordinates to grid coordinates.
    
    Args:
        map_x: Map x-coordinate
        map_y: Map y-coordinate
        
    Returns:
        Tuple of (grid_x, grid_y) coordinates
    """
    return (math.floor(map_x / CELL_SIZE), math.floor(map_y / CELL_SIZE))

def map_size_from_grid(grid_width: float, grid_height: float) -> tuple[float, float]:
    """Convert grid dimensions to map dimensions.
    
    Args:
        grid_width: Width in grid units
        grid_height: Height in grid units
        
    Returns:
        Tuple of (map_width, map_height)
    """
    return (grid_width * CELL_SIZE, grid_height * CELL_SIZE)

def grid_size_from_map(map_width: float, map_height: float) -> tuple[float, float]:
    """Convert map dimensions to grid dimensions.
    
    Note: This adds 1 to include the ending grid cell, since map coordinates
    represent the full extent of the shape.
    
    Args:
        map_width: Width in map units
        map_height: Height in map units
        
    Returns:
        Tuple of (grid_width, grid_height) 
    """
    return (math.ceil(map_width / CELL_SIZE), math.ceil(map_height / CELL_SIZE))

def grid_rect_from_points(start_x: float, start_y: float, end_x: float, end_y: float) -> tuple[float, float, float, float]:
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

