"""Column arrangement options for room layouts."""

from enum import Enum, auto

class RowOrientation(Enum):
    """Orientation for row-based column arrangements."""
    HORIZONTAL = auto()
    VERTICAL = auto()

class ColumnArrangement(Enum):
    """Available arrangements for columns in a room."""
    ROWS = auto()      # Columns arranged in parallel rows
    CIRCLE = auto()    # Columns arranged in a circle
