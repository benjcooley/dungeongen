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
    def test_one_grid_passages(self) -> None:
        """Test passages between rooms separated by one grid cell."""
        # Use origin (0,0) for test
        ox, oy = 0, 0
        
        # Create rooms for vertical passage - one grid apart
        room1 = self.runner.map.create_rectangular_room(ox, oy, 3, 3)  # Top room
        room2 = self.runner.map.create_rectangular_room(ox, oy + 4, 3, 3)  # Bottom room
        
        # Create rooms for horizontal passage - one grid apart
        room3 = self.runner.map.create_rectangular_room(ox + 5, oy + 2, 3, 3)  # Left room  
        room4 = self.runner.map.create_rectangular_room(ox + 9, oy + 2, 3, 3)  # Right room
        
        # Create vertical passage points
        vertical_points = [room1.get_exit(RoomDirection.SOUTH), room2.get_exit(RoomDirection.NORTH)]
        
        # Create horizontal passage points
        horizontal_points = [room3.get_exit(RoomDirection.EAST), room4.get_exit(RoomDirection.WEST)]
        
        # Validate vertical passage
        is_valid_vertical, crossed_vertical = self.runner.map.occupancy.check_passage(
            vertical_points,
            RoomDirection.SOUTH
        )
        
        # Create and connect vertical passage
        vertical_passage = Passage.from_grid_path(vertical_points, 
            start_direction=RoomDirection.SOUTH, end_direction=RoomDirection.NORTH)
        self.runner.map.add_element(vertical_passage)
        room1.connect_to(vertical_passage)
        room2.connect_to(vertical_passage)
        
        # Validate horizontal passage
        is_valid_horizontal, crossed_horizontal = self.runner.map.occupancy.check_passage(
            horizontal_points,
            RoomDirection.EAST
        )
        
        # Create and connect horizontal passage
        horizontal_passage = Passage.from_grid_path(horizontal_points, 
            start_direction=RoomDirection.EAST, end_direction=RoomDirection.WEST)
        self.runner.map.add_element(horizontal_passage)
        room3.connect_to(horizontal_passage)
        room4.connect_to(horizontal_passage)
        
        # Verify passages
        assert is_valid_vertical and not crossed_vertical, "Vertical passage should be valid"
        assert is_valid_horizontal and not crossed_horizontal, "Horizontal passage should be valid"

    @tag_test(TestTags.BASIC)
    def test_crossing_passages(self) -> None:
        """Test passages that cross each other in a + pattern."""
        # Use origin (0,0) for test
        ox, oy = 0, 0
        
        # Create rooms in + pattern
        north_room = self.runner.map.create_rectangular_room(ox + 4, oy, 3, 3)
        south_room = self.runner.map.create_rectangular_room(ox + 4, oy + 8, 3, 3)
        west_room = self.runner.map.create_rectangular_room(ox, oy + 4, 3, 3)
        east_room = self.runner.map.create_rectangular_room(ox + 8, oy + 4, 3, 3)
        
        # Create vertical passage points
        vertical_points = [
            north_room.get_exit(RoomDirection.SOUTH),
            south_room.get_exit(RoomDirection.NORTH)
        ]
        
        # Create and connect vertical passage first
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

        # Verify horizontal passage checks
        assert is_valid_horizontal, "Horizontal passage should be valid"
        assert crossed_horizontal, "Horizontal passage should cross vertical passage"
        assert len(crossed_horizontal) == 1, "Should cross exactly one passage"
        cross_x, cross_y, cross_idx = crossed_horizontal[0]
        assert cross_idx == vertical_passage.get_map_index(), "Should cross the vertical passage"

    @tag_test(TestTags.BASIC)
    def test_passage_through_room(self) -> None:
        """Test that passages cannot pass through rooms."""
        # Use origin (0,0) for test
        ox, oy = 0, 0
        
        # Create three rooms:
        # [Room1]   [Room3]   [Room2]
        # Where Room3 blocks passage between Room1 and Room2
        room1 = self.runner.map.create_rectangular_room(ox, oy, 3, 3)  # Left room
        room2 = self.runner.map.create_rectangular_room(ox + 8, oy, 3, 3)  # Right room
        room3 = self.runner.map.create_rectangular_room(ox + 4, oy, 3, 3)  # Center room (blocking)
        
        # Try to create passage points through the middle room
        passage_points = [
            room1.get_exit(RoomDirection.EAST),
            room2.get_exit(RoomDirection.WEST)
        ]
        
        # Check passage - should fail because room3 blocks it
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points,
            RoomDirection.EAST
        )
        
        # Verify passage is invalid
        assert not is_valid, "Passage through room should be invalid"
        
    @tag_test(TestTags.BASIC)
    def test_horizontal_left_above(self) -> None:
        """Test passage generation between horizontally offset rooms - left room above."""
        room1, room2 = self._create_offset_room_pair(0, 0, "horizontal_left_above")
        
        # Try to generate passage points
        points = [
            room1.get_exit(RoomDirection.EAST),
            room2.get_exit(RoomDirection.WEST)
        ]
        
        # Generate full passage point sequence with one bend
        passage_points = Passage.generate_passage_points(
            points[0],
            RoomDirection.EAST,
            points[1],
            RoomDirection.WEST,
            bend_positions=[2]  # Place bend after initial segment
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,  # Access the points list from PassagePoints
            RoomDirection.EAST
        )
        
        # Create and connect passage regardless of validation
        passage = Passage.from_grid_path(passage_points.points)  # Access the points list
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)

        # Now do the assertions
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"

    @tag_test(TestTags.BASIC)
    def test_horizontal_left_below(self) -> None:
        """Test passage generation between horizontally offset rooms - left room below."""
        room1, room2 = self._create_offset_room_pair(0, 0, "horizontal_left_below")
        
        # Try to generate passage points
        points = [
            room1.get_exit(RoomDirection.EAST),
            room2.get_exit(RoomDirection.WEST)
        ]
        
        # Generate full passage point sequence with one bend
        passage_points = Passage.generate_passage_points(
            points[0],
            RoomDirection.EAST,
            points[1],
            RoomDirection.WEST,
            bend_positions=[2]  # Add bend after initial segment
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,  # Access the points list from PassagePoints
            RoomDirection.EAST
        )
        
        # Create and connect passage regardless of validation
        passage = Passage.from_grid_path(passage_points.points)  # Access the points list
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)

        # Now do the assertions
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"

    @tag_test(TestTags.BASIC)
    def test_vertical_left_top(self) -> None:
        """Test passage generation between vertically offset rooms - top room to left."""
        room1, room2 = self._create_offset_room_pair(0, 0, "vertical_left_top")
        
        # Try to generate passage points
        points = [
            room1.get_exit(RoomDirection.SOUTH),
            room2.get_exit(RoomDirection.NORTH)
        ]
        
        # Generate full passage point sequence with one bend
        passage_points = Passage.generate_passage_points(
            points[0],
            RoomDirection.SOUTH,
            points[1],
            RoomDirection.NORTH,
            bend_positions=[2]  # Place bend after initial segment
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,  # Access the points list from PassagePoints
            RoomDirection.SOUTH
        )
        
        # Create and connect passage regardless of validation
        passage = Passage.from_grid_path(passage_points.points)  # Access the points list
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)

        # Now do the assertions
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"

    @tag_test(TestTags.BASIC)
    def test_vertical_right_top(self) -> None:
        """Test passage generation between vertically offset rooms - top room to right."""
        room1, room2 = self._create_offset_room_pair(0, 0, "vertical_right_top")
        
        # Try to generate passage points
        points = [
            room1.get_exit(RoomDirection.SOUTH),
            room2.get_exit(RoomDirection.NORTH)
        ]
        
        # Generate full passage point sequence with one bend
        passage_points = Passage.generate_passage_points(
            points[0],
            RoomDirection.SOUTH,
            points[1],
            RoomDirection.NORTH,
            bend_positions=[2]  # Add bend after initial segment
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,  # Access the points list from PassagePoints
            RoomDirection.SOUTH
        )
        
        # Create and connect passage regardless of validation
        passage = Passage.from_grid_path(passage_points.points)  # Access the points list
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)

        # Now do the assertions
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"

    def _create_l_shaped_rooms(self, ox: int, oy: int, diagonal_dist: int) -> tuple[Room, Room]:
        """Create a pair of rooms separated by the given diagonal distance.
        
        Args:
            ox: Origin x coordinate
            oy: Origin y coordinate
            diagonal_dist: Number of grid cells diagonally between rooms
            
        Returns:
            Tuple of (north_room, west_room)
        """
        # Create rooms with specified diagonal spacing
        north_room = self.runner.map.create_rectangular_room(ox + diagonal_dist, oy, 3, 3)
        west_room = self.runner.map.create_rectangular_room(ox, oy + diagonal_dist, 3, 3)
        return north_room, west_room

    @tag_test(TestTags.BASIC)
    def test_l_shaped_passages(self) -> None:
        """Test basic L-shaped passage generation with 3-grid diagonal spacing."""
        # Use origin (0,0) for test
        ox, oy = 0, 0
        
        # Create rooms with 3-grid diagonal spacing
        room1, room2 = self._create_l_shaped_rooms(ox, oy, 3)
        
        # Get exit points
        start_dir = RoomDirection.SOUTH
        end_dir = RoomDirection.EAST
        
        points = [
            room1.get_exit(start_dir),
            room2.get_exit(end_dir)
        ]
        
        # Generate passage point sequence for L-shape
        passage_points = Passage.generate_passage_points(
            points[0],
            start_dir,
            points[1],
            end_dir,
            bend_positions=[]  # No manual bends needed for L-shape
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,
            start_dir
        )
        
        # Create and connect passage
        passage = Passage.from_grid_path(passage_points.points)
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)
        
        # Add debug label
        self.runner.add_test_label("Basic L-shape", (ox, oy - 1))

        # Verify passage
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"
        
    @tag_test(TestTags.BASIC)
    def test_l_shaped_passages_with_bends(self) -> None:
        """Test L-shaped passage generation with 5-grid diagonal spacing and multiple bends."""
        # Use origin (0,0) for test with more space between rooms
        ox, oy = 0, 0
        
        # Create rooms with 5-grid diagonal spacing
        room1, room2 = self._create_l_shaped_rooms(ox, oy, 5)
        
        # Get exit points
        start_dir = RoomDirection.SOUTH
        end_dir = RoomDirection.EAST
        
        points = [
            room1.get_exit(start_dir),
            room2.get_exit(end_dir)
        ]
        
        # Generate passage with 2 bends, avoiding first and last steps
        passage_points = Passage.generate_passage_points(
            points[0],
            start_dir,
            points[1],
            end_dir,
            bend_positions=[2, 3]  # Two bends in middle of path
        )
        
        assert passage_points is not None, "Failed to generate passage points"
        
        # Validate passage
        is_valid, crossed = self.runner.map.occupancy.check_passage(
            passage_points.points,
            start_dir
        )
        
        # Create and connect passage
        passage = Passage.from_grid_path(passage_points.points)
        self.runner.map.add_element(passage)
        room1.connect_to(passage)
        room2.connect_to(passage)
        
        # Add debug label
        self.runner.add_test_label("L-shape with bends", (ox, oy - 1))

        # Verify passage
        assert is_valid, "Generated passage should be valid"
        assert not crossed, "Generated passage should not cross others"

    def _create_l_shaped_pair(self, ox: int, oy: int, config: str) -> tuple[Room, Room]:
        """Create a pair of rooms in L-shaped configuration.
        
        Args:
            ox: Origin x coordinate
            oy: Origin y coordinate
            config: One of:
                - l_north_east: First room north, second room east
                - l_north_west: First room north, second room west
                - l_south_east: First room south, second room east
                - l_south_west: First room south, second room west
                
        Returns:
            Tuple of (room1, room2) positioned in L-shape
        """
        if config == "l_north_east":
            room1 = self.runner.map.create_rectangular_room(ox + 3, oy, 3, 3)      # North room
            room2 = self.runner.map.create_rectangular_room(ox + 6, oy + 3, 3, 3)  # East room
        elif config == "l_north_west":
            room1 = self.runner.map.create_rectangular_room(ox + 3, oy, 3, 3)      # North room
            room2 = self.runner.map.create_rectangular_room(ox, oy + 3, 3, 3)      # West room
        elif config == "l_south_east":
            room1 = self.runner.map.create_rectangular_room(ox + 3, oy + 6, 3, 3)  # South room
            room2 = self.runner.map.create_rectangular_room(ox + 6, oy + 3, 3, 3)  # East room
        else:  # l_south_west
            room1 = self.runner.map.create_rectangular_room(ox + 3, oy + 6, 3, 3)  # South room
            room2 = self.runner.map.create_rectangular_room(ox, oy + 3, 3, 3)      # West room
            
        return room1, room2

    def _get_l_shaped_directions(self, config: str) -> tuple[RoomDirection, RoomDirection]:
        """Get the appropriate start/end directions for L-shaped passage configuration.
        
        Args:
            config: The L-shape configuration name
            
        Returns:
            Tuple of (start_direction, end_direction) for the passage
        """
        if config == "l_north_east":
            return RoomDirection.SOUTH, RoomDirection.WEST
        elif config == "l_north_west":
            return RoomDirection.SOUTH, RoomDirection.EAST
        elif config == "l_south_east":
            return RoomDirection.NORTH, RoomDirection.WEST
        else:  # l_south_west
            return RoomDirection.NORTH, RoomDirection.EAST

    def _create_offset_room_pair(self, ox: int, oy: int, config: str) -> tuple[Room, Room]:
        """Create a pair of rooms in the specified offset configuration.
        
        Args:
            ox: Origin x coordinate
            oy: Origin y coordinate
            config: One of:
                - horizontal_left_above: Left room above right room
                - horizontal_left_below: Left room below right room
                - vertical_left_top: Top room to left of bottom room
                - vertical_right_top: Top room to right of bottom room
                
        Returns:
            Tuple of (room1, room2) positioned according to config
        """
        if config == "horizontal_left_above":
            room1 = self.runner.map.create_rectangular_room(ox, oy, 3, 3)
            room2 = self.runner.map.create_rectangular_room(ox + 8, oy + 4, 3, 3)
        elif config == "horizontal_left_below":
            room1 = self.runner.map.create_rectangular_room(ox, oy + 4, 3, 3)
            room2 = self.runner.map.create_rectangular_room(ox + 8, oy, 3, 3)
        elif config == "vertical_left_top":
            room1 = self.runner.map.create_rectangular_room(ox + 20, oy + 20, 3, 3)
            room2 = self.runner.map.create_rectangular_room(ox + 24, oy + 28, 3, 3)
        else:  # vertical_right_top
            room1 = self.runner.map.create_rectangular_room(ox + 4, oy, 3, 3)
            room2 = self.runner.map.create_rectangular_room(ox, oy + 8, 3, 3)
            
        return room1, room2

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
        
        # Generate vertical passage points with no bends (straight)
        vertical_start = room1.get_exit(RoomDirection.SOUTH)
        vertical_end = room2.get_exit(RoomDirection.NORTH)
        vertical_points = Passage.generate_passage_points(
            vertical_start,
            RoomDirection.SOUTH,
            vertical_end,
            RoomDirection.NORTH,
            bend_positions=[]  # No bends for straight passage
        )
        print(f"\nTesting vertical passage points: {vertical_points}")
        
        # Generate horizontal passage points with no bends (straight)
        horizontal_start = room3.get_exit(RoomDirection.EAST)
        horizontal_end = room4.get_exit(RoomDirection.WEST)
        horizontal_points = Passage.generate_passage_points(
            horizontal_start,
            RoomDirection.EAST,
            horizontal_end,
            RoomDirection.WEST,
            bend_positions=[]  # No bends for straight passage
        )
        
        # Enable debug visualization
        debug_draw.enable(DebugDrawFlags.PASSAGE_CHECK)

        # First validate the passages
        print("\nChecking vertical passage...")
        print(f"Start point: {vertical_points[0]}")
        print(f"End point: {vertical_points[1]}")
        print(f"Direction: {RoomDirection.SOUTH}")
        
        is_valid_vertical, crossed_vertical = self.runner.map.occupancy.check_passage(
            vertical_points.points,  # Access the points list from PassagePoints
            RoomDirection.SOUTH
        )
        print(f"Vertical passage valid: {is_valid_vertical}, crossed: {crossed_vertical}")
        
        # Check horizontal passage
        is_valid_horizontal, crossed_horizontal = self.runner.map.occupancy.check_passage(
            horizontal_points.points,  # Access the points list from PassagePoints
            RoomDirection.EAST
        )
        print(f"Horizontal passage valid: {is_valid_horizontal}, crossed: {crossed_horizontal}")

        # Create and connect passages after validation
        vertical_passage = Passage.from_grid_path(vertical_points.points)  # Access the points list
        self.runner.map.add_element(vertical_passage)
        # Connect vertical passage to rooms
        room1.connect_to(vertical_passage)
        room2.connect_to(vertical_passage)

        horizontal_passage = Passage.from_grid_path(horizontal_points.points)  # Access the points list
        self.runner.map.add_element(horizontal_passage)
        # Connect horizontal passage to rooms
        room3.connect_to(horizontal_passage)
        room4.connect_to(horizontal_passage)

        # Do assertions after all elements are added
        assert is_valid_vertical and not crossed_vertical, "Vertical passage should be valid"
        assert is_valid_horizontal and not crossed_horizontal, "Horizontal passage should be valid"
