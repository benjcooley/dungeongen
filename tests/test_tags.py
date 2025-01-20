"""Test tags for grouping test cases."""

from enum import Enum, auto

class TestTags(Enum):
    """Tags for grouping test cases."""
    ALL = auto()
    BASIC = auto()
    CORNERS = auto()
    INTERSECTIONS = auto()
    DEAD_ENDS = auto()
    PARALLEL = auto()
    INVALID = auto()
