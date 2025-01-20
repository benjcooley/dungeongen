"""Test cases for passage generation and validation."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Set, List, Tuple, Optional
import skia
from map.map import Map
from map.room import Room
from map.passage import Passage
from map._arrange.arrange_enums import RoomDirection
from options import Options
from debug_config import debug_draw, DebugDrawFlags
from debug_draw import debug_draw_init
from constants import CELL_SIZE

class TestTags(Enum):
    """Tags for grouping test cases."""
    ALL = auto()
    BASIC = auto()
    CORNERS = auto()
    INTERSECTIONS = auto()
    DEAD_ENDS = auto()
    PARALLEL = auto()
    INVALID = auto()

@dataclass
class TestCase:
    """Information about a test case."""
    number: int
    name: str
    description: str
    location: Tuple[int, int]  # Grid coordinates of test area
    text_offset: Tuple[int, int]  # Offset for drawing test info

class TestPassages:
    """Test cases for passage generation and validation."""
    
    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.current_case = 0
        
    def run_tests(self, tags: Set[TestTags]) -> None:
        """Run all test cases matching the given tags.
        
        Args:
            tags: Set of tags indicating which tests to run
        """
        # Create map and enable debug visualization
        options = Options()
        self.map = Map(options)
        debug_draw.enable(DebugDrawFlags.PASSAGE_CHECK)
        
        # Find test methods
        test_methods = [method for method in dir(self) 
                       if method.startswith('test_') and callable(getattr(self, method))]
        
        tests_run = 0
        print("\nRunning passage tests...")
        
        # Run each test method if its tags match
        for method in test_methods:
            test_func = getattr(self, method)
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            
            # Run test if tags match
            if TestTags.ALL in tags or any(tag in tags for tag in test_tags):
                print(f"Running test: {method}")
                tests_run += 1
        
        print(f"\nPassageTests tests run: {tests_run}")
    
    def _draw_test_info(self, canvas: skia.Canvas, transform: skia.Matrix) -> None:
        """Draw test case numbers and descriptions."""
        text_paint = skia.Paint(
            Color=skia.Color(0, 0, 0),
            AntiAlias=True,
            TextSize=14
        )
        
        for case in self.test_cases:
            # Convert grid location to map coordinates
            x = case.location[0] * CELL_SIZE
            y = case.location[1] * CELL_SIZE
            
            # Apply transform to get canvas coordinates
            points = [skia.Point(x, y)]
            transform.mapPoints(points)
            cx, cy = points[0].x, points[0].y
            
            # Draw case info
            cx += case.text_offset[0]
            cy += case.text_offset[1]
            canvas.drawString(f"{case.number}. {case.name}", cx, cy, text_paint)
            canvas.drawString(case.description, cx, cy + 16, text_paint)

def tag_test(*tags: TestTags):
    """Decorator to tag test methods with test categories."""
    def decorator(func):
        setattr(func, 'tags', set(tags))
        return func
    return decorator

@tag_test(TestTags.BASIC)
def test_simple_passages(self, origin: tuple[int, int] = (0, 0)) -> tuple[int, int]:
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
        
        # Create rooms to connect passages to
        room1 = self.map.create_rectangular_room(ox, oy, 3, 3)
        room2 = self.map.create_rectangular_room(ox, oy + 5, 3, 3)
        room3 = self.map.create_rectangular_room(ox + 7, oy + 7, 3, 3)
        room4 = self.map.create_rectangular_room(ox + 12, oy + 7, 3, 3)
        
        # Create vertical passage points (just start and end)
        vertical_points = [(ox + 1, oy + 2), (ox + 1, oy + 5)]
        
        # Create horizontal passage points (just start and end, offset to not intersect)
        horizontal_points = [(ox + 9, oy + 8), (ox + 12, oy + 8)]
        
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
