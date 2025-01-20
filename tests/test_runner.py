"""Test runner for all test cases."""

from typing import Set, List, Tuple, Optional
import skia
from dataclasses import dataclass
from debug_draw import debug_draw_init
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
            
    def setup(self, tags: Set[TestTags] = { TestTags.ALL }, options: Options = None) -> None:
        """Setup test environment.
        
        Args:
            tags: Set of tags indicating which tests to run
            options: Options instance to use for map creation
        """
        # Create fresh map and enable debug visualization
        self.options = options or Options()
        self.map = Map(self.options)
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
        
    def add_test_label(self, text: str, position: Tuple[int, int]) -> None:
        """Add a text label at grid coordinates."""
        if not hasattr(self, 'labels'):
            self.labels = []
        self.labels.append((text, position))
        
    def draw_test_info(self, canvas: skia.Canvas, transform: skia.Matrix) -> None:
        """Draw test case numbers and descriptions."""
        text_paint = skia.Paint(
            AntiAlias=True,
            Color=skia.Color(0, 0, 0),
            Style=skia.Paint.kFill_Style
        )
        
        text_font = skia.Font(None, 30.0)
        bold_font = skia.Font(None, 30.0)
        bold_font.setEmbolden(True)
        
        # Draw labels first
        if hasattr(self, 'labels'):
            for text, pos in self.labels:
                x = pos[0] * CELL_SIZE
                y = pos[1] * CELL_SIZE
                points = [skia.Point(x, y)]
                transform.mapPoints(points)
                point = points[0]
                blob = skia.TextBlob(text, bold_font)
                canvas.drawTextBlob(blob, point.x(), point.y(), text_paint)  # Draw at room position
        
        for case in self.test_cases:
            # Convert grid location to map coordinates
            x = case.location[0] * CELL_SIZE
            y = case.location[1] * CELL_SIZE
            
            # Apply transform to get canvas coordinates
            points = [skia.Point(x, y)]
            transform.mapPoints(points)
            point = points[0]
            
            # Draw case info
            x = point.x() + case.text_offset[0] + (4 * CELL_SIZE)
            y = point.y() + case.text_offset[1] - (2 * CELL_SIZE)
            title_blob = skia.TextBlob(f"{case.number}. {case.name}", text_font)
            desc_blob = skia.TextBlob(case.description, text_font)
            canvas.drawTextBlob(title_blob, x, y, text_paint)
            canvas.drawTextBlob(desc_blob, x, y + 60, text_paint)
            
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
        from rich import print as rprint
        rprint("\n[bold blue]Running passage tests...[/bold blue]")
        
        # Create visualization surface
        surface = skia.Surface(self.options.canvas_width, self.options.canvas_height)
        canvas = surface.getCanvas()
        canvas.clear(skia.Color(255, 255, 255))
        
        failures = []
        
        # Run each test method if its tags match
        for method in test_methods:
            test_func = getattr(passage_tests, method)
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            
            # Run test if tags match
            if TestTags.ALL in tags or any(tag in tags for tag in test_tags):
                from rich import print as rprint
                
                rprint(f"\n[bold]Running test:[/bold] {method}")
                try:
                    test_func()
                    rprint(f"[green]PASSED ✅[/green]")
                except AssertionError as e:
                    import traceback
                    rprint(f"[red]FAILED ❌: {str(e)}[/red]")
                    rprint(f"[red]{traceback.format_exc()}[/red]")
                    failures.append((method, str(e)))
                except Exception as e:
                    import traceback
                    rprint(f"[red]ERROR ❌: {str(e)}[/red]")
                    rprint(f"[red]{traceback.format_exc()}[/red]")
                    failures.append((method, str(e)))
                tests_run += 1
                
        # Calculate transform once
        transform = self.map._calculate_default_transform(self.options.canvas_width, self.options.canvas_height)
        
        # Draw the map with transform
        map.render(canvas, transform)
        
        # Debug draw the occupancy grid with same transform
        debug_draw_init(canvas)
        canvas.save()
        canvas.concat(transform)
        map.occupancy.draw_debug(canvas)
        canvas.restore()
        
        # Save visualization
        image = surface.makeImageSnapshot()
        image.save('test_output.png', skia.kPNG)
        
        # Print summary using rich
        from rich import print as rprint
        from rich.panel import Panel
        from rich.text import Text

        summary = []
        summary.append(Text("\nPassageTests Summary", style="bold"))
        summary.append(f"Tests run: {tests_run}")
        
        if failures:
            summary.append(Text(f"\nFailures: {len(failures)} ❌", style="red bold"))
            for test, error in failures:
                summary.append(Text(f"  • {test}: {error}", style="red"))
        else:
            summary.append(Text("\nAll tests passed! ✅", style="green bold"))
            
        rprint(Panel.fit("\n".join(str(line) for line in summary)))

def get_runner() -> TestRunner:
    """Get the singleton test runner instance."""
    return TestRunner()
