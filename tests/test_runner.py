"""Test runner for all test cases."""

from typing import Set, List, Tuple, Optional
import skia
from dataclasses import dataclass
from map.map import Map 
from options import Options
from debug_config import debug_draw, DebugDrawFlags
from constants import CELL_SIZE
from tests.test_tags import TestTags

@dataclass
class TestCase:
    """Information about a test case."""
    number: int
    name: str
    description: str
    location: Tuple[int, int]  # Grid coordinates of test area
    text_offset: Tuple[int, int]  # Offset for drawing test info

class TestRunner:
    """Singleton test runner that manages test execution and visualization."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize instance
            cls._instance.test_cases = []
            cls._instance.current_case = 0
            cls._instance.map = None
        return cls._instance
        
    def __init__(self):
        """Initialize test runner if not already initialized."""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
    def setup(self, tags: Set[TestTags] = {TestTags.ALL}) -> None:
        """Setup test environment.
        
        Args:
            tags: Set of tags indicating which tests to run
        """
        # Create fresh map and enable debug visualization
        options = Options()
        self.map = Map(options)
        debug_draw.enable(DebugDrawFlags.PASSAGE_CHECK)
        self.test_cases = []
        self.current_case = 0
        
    def add_test_case(self, number: int, name: str, description: str,
                      location: Tuple[int, int], text_offset: Tuple[int, int]) -> None:
        """Add a test case to be tracked."""
        self.test_cases.append(TestCase(
            number=number,
            name=name, 
            description=description,
            location=location,
            text_offset=text_offset
        ))
        
    def draw_test_info(self, canvas: skia.Canvas, transform: skia.Matrix) -> None:
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
            
    def run_tests(self, tags: Set[TestTags] = {TestTags.ALL}) -> None:
        """Run all test cases matching the given tags.
        
        Args:
            tags: Set of tags indicating which tests to run
        """
        self.setup(tags)
        
        from tests.test_passages import TestPassages
        passage_tests = TestPassages()
        
        # Find test methods
        test_methods = [method for method in dir(passage_tests) 
                       if method.startswith('test_') and callable(getattr(passage_tests, method))]
        
        tests_run = 0
        print("\nRunning passage tests...")
        
        # Create visualization surface
        surface = skia.Surface(800, 600)
        canvas = surface.getCanvas()
        canvas.clear(skia.Color(255, 255, 255))
        
        failures = []
        
        # Run each test method if its tags match
        for method in test_methods:
            test_func = getattr(passage_tests, method)
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            
            # Run test if tags match
            if TestTags.ALL in tags or any(tag in tags for tag in test_tags):
                print(f"\nRunning test: {method}")
                try:
                    test_func()
                except AssertionError as e:
                    print(f"FAILED: {str(e)}")
                    failures.append((method, str(e)))
                except Exception as e:
                    print(f"ERROR: {str(e)}")
                    failures.append((method, str(e)))
                tests_run += 1
                
                # Draw debug visualization after each test
                self.map.render(canvas)
                if debug_draw.is_enabled(DebugDrawFlags.PASSAGE_CHECK):
                    self.map.occupancy.draw_debug(canvas)
        
        # Save visualization
        image = surface.makeImageSnapshot()
        image.save('test_output.png', skia.kPNG)
        
        # Print summary
        print(f"\nPassageTests summary:")
        print(f"Tests run: {tests_run}")
        if failures:
            print(f"Failures: {len(failures)}")
            for test, error in failures:
                print(f"  {test}: {error}")
        else:
            print("All tests passed!")

def get_runner() -> TestRunner:
    """Get the singleton test runner instance."""
    return TestRunner()
