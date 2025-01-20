"""Test cases for passage generation and validation."""

from typing import Tuple
from map.room import Room
from map.passage import Passage
from map._arrange.arrange_enums import RoomDirection
from tests.test_runner import get_runner
from tests.test_tags import TestTags

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
        """Test simple 2x5 vertical and horizontal passages."""
        # Use origin (0,0) for first test
        ox, oy = 0, 0
        
        # Add test case info
        self.runner.add_test_case(
            number=1,
            name="Simple Passages",
            description="2x5 vertical and horizontal passages",
            location=(ox, oy),
            text_offset=(20, -20)  # Moved text right to be more visible
        )
        
        # Create rooms for vertical passage
        room1 = self.runner.map.create_rectangular_room(ox, oy, 3, 3)  # Top room
        room2 = self.runner.map.create_rectangular_room(ox, oy + 6, 3, 3)  # Bottom room
        
        # Create rooms for horizontal passage (closer to vertical passage)
        room3 = self.runner.map.create_rectangular_room(ox + 5, oy + 3, 3, 3)  # Left room  
        room4 = self.runner.map.create_rectangular_room(ox + 11, oy + 3, 3, 3)  # Right room
        
        # Add debug text labels
        self.runner.add_test_label("Vertical", (ox, oy - 1))
        self.runner.add_test_label("Horizontal", (ox + 5, oy + 2))
        
        # Create vertical passage points (just start and end)
        vertical_points = [(ox + 1, oy + 3), (ox + 1, oy + 6)]
        
        # Create horizontal passage points (just start and end)
        horizontal_points = [(ox + 8, oy + 4), (ox + 11, oy + 4)]
        
        # Test and create vertical passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            vertical_points,
            RoomDirection.SOUTH
        )
        print(f"Vertical passage valid: {is_valid}, crossed: {crossed}")
        assert is_valid and not crossed, "Vertical passage should be valid"
        
        if is_valid:
            passage = Passage.from_grid_path(vertical_points, RoomDirection.SOUTH, RoomDirection.SOUTH)
            self.runner.map.add_element(passage)
        
        # Test and create horizontal passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            horizontal_points,
            RoomDirection.EAST,
            allow_dead_end=True
        )
        print(f"Horizontal passage valid: {is_valid}, crossed: {crossed}")
        assert is_valid and not crossed, "Horizontal passage should be valid"
        
        if is_valid:
            passage = Passage.from_grid_path(horizontal_points, RoomDirection.EAST, RoomDirection.EAST)
            self.runner.map.add_element(passage)
