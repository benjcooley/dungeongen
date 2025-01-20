"""Test runner for all test cases."""

import os
import traceback
from typing import Set, List, Tuple, Optional
import skia
from dataclasses import dataclass
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from debug_draw import debug_draw_init
from map.map import Map 
from options import Options
from debug_config import debug_draw, DebugDrawFlags
from constants import CELL_SIZE
from tests.test_tags import TestTags
from tests.test_passages import TestPassages

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
        self.options = options or Options()
        debug_draw.enable(DebugDrawFlags.PASSAGE_CHECK)
        self.test_cases = []
        self.current_case = 0
        self.tags = tags
        
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
        
    def draw_test_info(self, canvas: skia.Canvas, test_name: str, test_desc: str) -> None:
        """Draw test case info at top left of canvas."""
        text_paint = skia.Paint(
            AntiAlias=True,
            Color=skia.Color(0, 0, 0),
            Style=skia.Paint.kFill_Style
        )
        
        title_font = skia.Font(None, 72.0)
        title_font.setEmbolden(True)
        desc_font = skia.Font(None, 54.0)
        
        # Draw test name and description
        title_blob = skia.TextBlob(test_name, title_font)
        desc_blob = skia.TextBlob(test_desc, desc_font)
        canvas.drawTextBlob(title_blob, 20, 30, text_paint)
        canvas.drawTextBlob(desc_blob, 20, 60, text_paint)
            
    def run_tests(self, tags: Set[TestTags] | None = None) -> None:
        """Run all test cases matching the given tags.
        
        Args:
            tags: Set of tags indicating which tests to run
        """
        # Ensure test results directory exists
        os.makedirs('test_results', exist_ok=True)
        
        self.setup(tags)
        
        passage_tests = TestPassages()
        
        # Find test methods
        test_methods = [method for method in dir(passage_tests) 
                       if method.startswith('test_') and callable(getattr(passage_tests, method))]
        
        tests_run = 0
        rprint("\n[bold blue]Running passage tests...[/bold blue]")
        
        failures = []
        
        # Run each test method if its tags match
        for method in test_methods:
            test_func = getattr(passage_tests, method)
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            
            # Run test if tags match
            test_tags = getattr(test_func, 'tags', {TestTags.ALL})
            run_tags = tags if tags is not None else self.tags
            if TestTags.ALL in run_tags or any(tag in run_tags for tag in test_tags):
                # Create fresh map for each test
                self.map = Map(self.options)
                
                # Create visualization surface
                surface = skia.Surface(self.options.canvas_width, self.options.canvas_height)
                canvas = surface.getCanvas()
                canvas.clear(skia.Color(255, 255, 255))
                
                rprint(f"\n[bold]Running test:[/bold] {method}")
                try:
                    test_func()
                    rprint(f"[green]PASSED ✅[/green]")
                    
                    # Calculate transform
                    transform = self.map._calculate_default_transform(
                        self.options.canvas_width, 
                        self.options.canvas_height
                    )
                    
                    # Draw the map with transform
                    self.map.render(canvas, transform)
                    
                    # Debug draw the occupancy grid
                    debug_draw_init(canvas)
                    canvas.save()
                    canvas.concat(transform)
                    self.map.occupancy.draw_debug(canvas)
                    canvas.restore()

                    # Draw test info with clean state
                    self.draw_test_info(canvas, method, test_func.__doc__ or "")

                    # Save test case image
                    image = surface.makeImageSnapshot()
                    image.save(f'test_results/test_{method}.png', skia.kPNG)
                    
                except AssertionError as e:
                    rprint(f"[red]FAILED ❌: {str(e)}[/red]")
                    rprint(f"[red]{traceback.format_exc()}[/red]")
                    failures.append((method, str(e)))
                except Exception as e:
                    rprint(f"[red]ERROR ❌: {str(e)}[/red]")
                    rprint(f"[red]{traceback.format_exc()}[/red]")
                    failures.append((method, str(e)))
                tests_run += 1
        
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
