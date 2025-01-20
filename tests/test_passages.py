"""Test cases for passage generation and validation."""

from enum import Enum, auto
from typing import Tuple
from map.room import Room
from map.passage import Passage
from map._arrange.arrange_enums import RoomDirection
from tests.test_runner import get_runner

class TestTags(Enum):
    """Tags for grouping test cases."""
    ALL = auto()
    BASIC = auto()
    CORNERS = auto()
    INTERSECTIONS = auto()
    DEAD_ENDS = auto()
    PARALLEL = auto()
    INVALID = auto()

def tag_test(*tags: TestTags):
    """Decorator to tag test methods with test categories."""
    def decorator(func):
        setattr(func, 'tags', set(tags))
        return func
    return decorator

class TestPassages:
    """Test cases for passage generation and validation."""
    
    def __init__(self):
        self.runner = get_runner()

    @tag_test(TestTags.BASIC)
    def test_simple_passages(self) -> None:
        """Test simple 2x5 vertical and horizontal passages.
        
        Args:
            origin: Starting grid coordinates for test area
            
        Returns:
            Origin coordinates for next test
        """
        ox, oy = origin
        
        # Add test case info
        self.test_cases.append(TestCase(
            number=1,
            name="Simple Passages",
            description="2x5 vertical and horizontal passages",
            location=(ox, oy),
            text_offset=(0, -20)
        ))
        
        # Create rooms for vertical passage
        room1 = self.map.create_rectangular_room(ox, oy, 3, 3)  # Top room
        room2 = self.map.create_rectangular_room(ox, oy + 6, 3, 3)  # Bottom room
        
        # Create rooms for horizontal passage (offset to not intersect)
        room3 = self.map.create_rectangular_room(ox + 8, oy + 2, 3, 3)  # Left room  
        room4 = self.map.create_rectangular_room(ox + 14, oy + 2, 3, 3)  # Right room
        
        # Create vertical passage points (just start and end)
        vertical_points = [(ox + 1, oy + 3), (ox + 1, oy + 6)]
        
        # Create horizontal passage points (just start and end)
        horizontal_points = [(ox + 11, oy + 3), (ox + 14, oy + 3)]
        
        # Test vertical passage
        is_valid, crossed = self.map.occupancy.check_passage(
            vertical_points,
            RoomDirection.SOUTH
        )
        assert is_valid and not crossed, "Vertical passage should be valid"
        
        # Test horizontal passage
        is_valid, crossed = self.map.occupancy.check_passage(
            horizontal_points,
            RoomDirection.EAST
        )
        assert is_valid and not crossed, "Horizontal passage should be valid"
        
        # Return origin for next test (moved right and down)
        return ox + 7, oy + 10
