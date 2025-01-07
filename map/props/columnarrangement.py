"""Enums for column arrangement patterns."""

from enum import Enum, auto

class ColumnArrangement(Enum):
    """Available patterns for arranging columns in rooms."""
    GRID = auto()      # Columns arranged in a grid pattern
    RECTANGLE = auto() # Columns arranged around rectangle perimeter
    ROWS = auto()      # Columns arranged in parallel rows
    CIRCLE = auto()    # Columns arranged in a circle

class RowOrientation(Enum):
    """Orientation for row-based column arrangements."""
    HORIZONTAL = auto()
    VERTICAL = auto()
