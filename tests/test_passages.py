"""Test cases for passage generation and validation."""

from typing import Tuple
from map.room import Room
from map.passage import Passage
from map.enums import RoomDirection
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
        vertical_points = [room1.get_exit(RoomDirection.SOUTH), room2.get_exit(RoomDirection.NORTH)]  # Shortened to avoid overlap
        print(f"\nTesting vertical passage points: {vertical_points}")
        
        # Create horizontal passage points (just start and end)
        horizontal_points = [room3.get_exit(RoomDirection.EAST), room3.get_exit(RoomDirection.WEST)]  # Shortened to avoid overlap
        
        # First validate the passages
        print("\nChecking vertical passage...")
        print(f"Start point: {vertical_points[0]}")
        print(f"End point: {vertical_points[1]}")
        print(f"Direction: {RoomDirection.SOUTH}")
        
        is_valid_vertical, crossed_vertical = self.runner.map.occupancy.check_passage(
            vertical_points,
            RoomDirection.SOUTH
        )
        print(f"Vertical passage valid: {is_valid_vertical}, crossed: {crossed_vertical}")
        
        # Check horizontal passage
        is_valid_horizontal, crossed_horizontal = self.runner.map.occupancy.check_passage(
            horizontal_points,
            RoomDirection.EAST
        )
        print(f"Horizontal passage valid: {is_valid_horizontal}, crossed: {crossed_horizontal}")

        # Create and connect passages after validation
        vertical_passage = Passage.from_grid_path(vertical_points)
        self.runner.map.add_element(vertical_passage)
        # Connect vertical passage to rooms
        room1.connect_to(vertical_passage)
        room2.connect_to(vertical_passage)

        horizontal_passage = Passage.from_grid_path(horizontal_points)
        self.runner.map.add_element(horizontal_passage)
        # Connect horizontal passage to rooms
        room3.connect_to(horizontal_passage)
        room4.connect_to(horizontal_passage)

        # Finally do the assertions
        assert is_valid_vertical and not crossed_vertical, "Vertical passage should be valid"
        assert is_valid_horizontal and not crossed_horizontal, "Horizontal passage should be valid"
