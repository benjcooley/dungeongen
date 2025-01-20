"""Test cases for passage generation and validation."""

from typing import Tuple
from map.room import Room
from map.passage import Passage
from map.enums import RoomDirection
from tests.test_runner import get_runner
from tests.test_tags import TestTags
from debug_config import debug_draw, DebugDrawFlags

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
        self.runner.setup()  # Initialize test environment

    @tag_test(TestTags.BASIC)
    def test_simple_passages(self) -> None:
        """Test simple linear vertical and horizontal passages."""
        self._test_simple_passages()

    @tag_test(TestTags.BASIC)
    def test_crossing_passages(self) -> None:
        """Test passages that cross each other in a + pattern."""
        # Use origin (0,0) for test
        ox, oy = 0, 0
        
        # Create rooms in + pattern
        north_room = self.runner.map.create_rectangular_room(ox + 3, oy, 3, 3)
        south_room = self.runner.map.create_rectangular_room(ox + 3, oy + 6, 3, 3)
        west_room = self.runner.map.create_rectangular_room(ox, oy + 3, 3, 3)
        east_room = self.runner.map.create_rectangular_room(ox + 6, oy + 3, 3, 3)
        
        # Create vertical passage points
        vertical_points = [
            north_room.get_exit(RoomDirection.SOUTH),
            south_room.get_exit(RoomDirection.NORTH)
        ]
        
        # Check vertical passage
        is_valid_vertical, crossed_vertical = self.runner.map.occupancy.check_passage(
            vertical_points,
            RoomDirection.SOUTH
        )
        
        # Create and connect vertical passage
        vertical_passage = Passage.from_grid_path(vertical_points)
        self.runner.map.add_element(vertical_passage)
        north_room.connect_to(vertical_passage)
        south_room.connect_to(vertical_passage)
        
        # Create horizontal passage points
        horizontal_points = [
            west_room.get_exit(RoomDirection.EAST),
            east_room.get_exit(RoomDirection.WEST)
        ]
        
        # Check horizontal passage
        is_valid_horizontal, crossed_horizontal = self.runner.map.occupancy.check_passage(
            horizontal_points,
            RoomDirection.EAST
        )
        
        # Create and connect horizontal passage
        horizontal_passage = Passage.from_grid_path(horizontal_points)
        self.runner.map.add_element(horizontal_passage)
        west_room.connect_to(horizontal_passage)
        east_room.connect_to(horizontal_passage)
        
        # Connect crossing passages
        horizontal_passage.connect_to(vertical_passage)

        # Verify all passage checks after setup is complete
        assert is_valid_vertical and not crossed_vertical, "Vertical passage should be valid"
        assert is_valid_horizontal, "Horizontal passage should be valid"
        assert crossed_horizontal, "Horizontal passage should cross vertical passage"
        assert len(crossed_horizontal) == 1, "Should cross exactly one passage"
        cross_x, cross_y, cross_idx = crossed_horizontal[0]
        assert cross_idx == vertical_passage.get_map_index(), "Should cross the vertical passage"
        # Verify crossing point is at expected location
        assert cross_x == ox + 3 and cross_y == oy + 3, "Crossing should occur at center point"

    def _test_simple_passages(self) -> None:
        """Test simple linear vertical and horizontal passages."""
        # Use origin (0,0) for first test
        ox, oy = 0, 0
        
        # Add test case info
        self.runner.add_test_case(
            number=1,
            name="Simple Passages",
            description="Test linear vertical and horizontal passages",
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
        horizontal_points = [room3.get_exit(RoomDirection.EAST), room4.get_exit(RoomDirection.WEST)]  # Shortened to avoid overlap
        
        # Enable debug visualization
        debug_draw.enable(DebugDrawFlags.PASSAGE_CHECK)

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

        # Do assertions after all elements are added
        assert is_valid_vertical and not crossed_vertical, "Vertical passage should be valid"
        assert is_valid_horizontal and not crossed_horizontal, "Horizontal passage should be valid"
