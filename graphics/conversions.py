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

def map_rect_to_grid_points(rect_x: float, rect_y: float, rect_width: float, rect_height: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Convert a map rectangle into grid space corner points.
    
    Args:
        rect_x: Rectangle X coordinate in map units
        rect_y: Rectangle Y coordinate in map units
        rect_width: Rectangle width in map units
        rect_height: Rectangle height in map units
        
    Returns:
        Tuple of ((grid_x1,grid_y1), (grid_x2,grid_y2)) representing corners in grid space
    """
    p1 = grid_from_map(rect_x, rect_y)
    p2 = grid_from_map(rect_x + rect_width, rect_y + rect_height)
    return (p1, p2)

def grid_points_to_map_rect(grid_x1: float, grid_y1: float, grid_x2: float, grid_y2: float) -> tuple[float, float, float, float]:
    """Convert two grid points into a map space rectangle.
    
    Args:
        grid_x1: First X coordinate in grid units
        grid_y1: First Y coordinate in grid units
        grid_x2: Second X coordinate in grid units
        grid_y2: Second Y coordinate in grid units
        
    Returns:
        Tuple of (rect_x, rect_y, rect_width, rect_height) in map units
    """
    p1 = map_from_grid(grid_x1, grid_y1)
    p2 = map_from_grid(grid_x2, grid_y2)
    return (p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])

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

