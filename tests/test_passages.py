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
