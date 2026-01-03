from enum import Enum, auto
import random
from dungeongen.map.room import Room
from dungeongen.map._props.column import Column, ColumnType
from dungeongen.map._props.prop import Prop
from dungeongen.graphics.shapes import Rectangle, Circle
from typing import List
from dungeongen.constants import CELL_SIZE
import math

class ColumnArrangement(Enum):
    """Available patterns for arranging columns in rooms."""
    GRID = auto()      # Columns arranged in a grid pattern
    RECTANGLE = auto() # Columns arranged around rectangle perimeter
    HORIZONTAL_ROWS = auto() # Columns arranged in horizontal rows
    VERTICAL_ROWS = auto()   # Columns arranged in vertical rows
    CIRCLE = auto()    # Columns arranged in a circle

def arrange_columns(room: Room,
                    arrangement: ColumnArrangement,
                    column_type: ColumnType = ColumnType.ROUND,
                    margin: float = 0) -> List['Prop']:
    """Create columns in this room according to the specified arrangement pattern.
    
    Args:
        arrangement: Pattern to arrange columns in
        column_type: Shape of the column (round or square) default: ColumnType.ROUND
        margin: Optional margin in grid units from room edges (default: 0)
        
    Returns:
        List of created column props
        
    Raises:
        ValueError: If arrangement is invalid for this room type
    """
    positions = []  # List of (x,y) map coordinates
    angles = []     # Optional list of angles for columns
    
    # For circular rooms, only allow CIRCLE arrangement
    if isinstance(room._shape, Circle):
        if arrangement != ColumnArrangement.CIRCLE:
            raise ValueError("Only CIRCLE arrangement supported for circular rooms")
            
        circle = room._shape  # type: Circle
        # Place columns away from wall based on margin
        radius = circle.radius - ((margin + 1) * CELL_SIZE)
        center = circle.bounds.center
        
        # Use 8 columns for now
        num_columns = 8
        for i in range(num_columns):
            angle = (i * 2 * math.pi / num_columns)
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            positions.append((x, y))
            angles.append(angle)
            
    # For rectangular rooms
    elif isinstance(room._shape, Rectangle):
        rect = room._shape  # type: Rectangle
        
        # Get room dimensions in grid units
        grid_width = int(rect.width / CELL_SIZE)
        grid_height = int(rect.height / CELL_SIZE)
        
        # Calculate valid column placement rectangle
        left = 1 + margin
        right = grid_width - (1 + margin)
        top = 1 + margin
        bottom = grid_height - (1 + margin)
        
        # Calculate all positions in grid coordinates first
        grid_positions = []  # List of (x,y) grid coordinates
        
        if arrangement == ColumnArrangement.GRID:
            # Place columns in a grid pattern with 2-unit spacing
            for x in range(int(left), int(right) + 1):
                for y in range(int(top), int(bottom) + 1):
                    grid_positions.append((x, y))
                        
        elif arrangement == ColumnArrangement.RECTANGLE:
            # Place columns around perimeter
            # Top and bottom rows
            for x in range(int(left), int(right) + 1):
                grid_positions.append((x, int(top)))  # Top row
                grid_positions.append((x, int(bottom)))  # Bottom row
            
            # Left and right columns (excluding corners)
            for y in range(int(top) + 1, int(bottom)):
                grid_positions.append((int(left), y))  # Left column
                grid_positions.append((int(right), y))  # Right column
                        
        elif arrangement == ColumnArrangement.HORIZONTAL_ROWS:
            if bottom - top < 2:  # Not enough vertical space for two rows
                return []
            # Place columns in two horizontal rows
            for x in range(int(left), int(right) + 1):
                grid_positions.append((x, int(top)))      # Top row
                grid_positions.append((x, int(bottom)))   # Bottom row
                
        else:  # VERTICAL_ROWS
            if right - left < 2:  # Not enough horizontal space for two columns
                return []
            # Place columns in two vertical rows
            for y in range(int(top), int(bottom) + 1):
                grid_positions.append((int(left), y))     # Left column
                grid_positions.append((int(right), y))    # Right column

        # Convert grid positions to map space
        for grid_x, grid_y in grid_positions:
            map_x = rect.left + (grid_x * CELL_SIZE)
            map_y = rect.top + (grid_y * CELL_SIZE)
            positions.append((map_x, map_y))
    
    else:
        raise ValueError(f"Unsupported room shape for column arrangement: {type(room._shape)}")
        
    # Create and add columns
    columns = []
    for i, pos in enumerate(positions):
        angle = angles[i] if angles else 0
        column = (Column.create_square(pos[0], pos[1], angle + math.pi/2) 
                    if column_type == ColumnType.SQUARE 
                    else Column.create_round(pos[0], pos[1]))
        room.add_prop(column)
        columns.append(column)
        
    return columns