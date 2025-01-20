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
        # Enable debug visualization
        debug_draw.enable(DebugDrawFlags.OCCUPANCY, DebugDrawFlags.PASSAGE_CHECK)
        
        # Create canvas
        options = Options()
        surface = skia.Surface(options.canvas_width, options.canvas_height)
        canvas = surface.getCanvas()
        canvas.clear(skia.Color(255, 255, 255))
        
        # Create map
        dungeon_map = Map(options)
        
        # Initialize test grid - each test gets a 20x20 area
        next_loc = (0, 0)
        
        # Run each test method if its tags match
        test_methods = [method for method in dir(self) 
                       if method.startswith('test_') and callable(getattr(self, method))]
                       
        for method in test_methods:
            test_func = getattr(self, method)
            # Get test tags from method
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            
            # Run test if tags match
            if TestTags.ALL in tags or any(tag in tags for tag in test_tags):
                self.current_case += 1
                next_loc = test_func(dungeon_map, next_loc)
        
        # Calculate transform
        transform = dungeon_map._calculate_default_transform(
            options.canvas_width, options.canvas_height)
        
        # Draw the map
        dungeon_map.render(canvas, transform)
        
        # Draw debug visualization
        debug_draw_init(canvas)
        canvas.save()
        canvas.concat(transform)
        dungeon_map.occupancy.draw_debug(canvas)
        canvas.restore()
        
        # Draw test case info
        self._draw_test_info(canvas, transform)
        
        # Save output
        image = surface.makeImageSnapshot()
        image.save('test_passages_output.png', skia.kPNG)
    
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
