"""Debug drawing configuration."""

from enum import Flag, auto, Enum
from typing import Callable
import skia

class HatchPattern(Enum):
    """Available hatch patterns for debug visualization."""
    DIAGONAL = auto()      # 45-degree diagonal lines
    CROSS = auto()         # Crossed diagonal lines
    HORIZONTAL = auto()    # Horizontal lines
    VERTICAL = auto()      # Vertical lines
    GRID = auto()         # Grid pattern

class DebugLayer(Enum):
    """Layers for ordering debug visualization."""
    BACKGROUND = 0
    GRID = 1
    OCCUPANCY = 2
    PASSAGES = 3
    PROPS = 4
    OVERLAY = 5

class DebugDrawFlags(Flag):
    """Flags controlling different aspects of debug visualization."""
    NONE = 0
    PROP_BOUNDS = auto()      # Draw red bounds around props
    GRID = auto()             # Draw basic grid visualization
    GRID_BOUNDS = auto()      # Draw blue grid-aligned prop bounds
    OCCUPANCY = auto()        # Draw occupied grid cells
    ELEMENT_NUMBERS = auto()  # Draw element index numbers
    PASSAGE_CHECK = auto()    # Draw passage validation visualization
    LABELS = auto()          # Draw debug text labels
    ALL = (PROP_BOUNDS | GRID | GRID_BOUNDS | OCCUPANCY | ELEMENT_NUMBERS | PASSAGE_CHECK | LABELS)

class DebugDraw:
    """Centralized debug drawing configuration."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not DebugDraw._initialized:
            self.enabled_flags: DebugDrawFlags = DebugDrawFlags.NONE
            self.hatch_pattern: HatchPattern = HatchPattern.DIAGONAL
            self._canvas = None
            self._draw_closures = []  # List of (layer, closure) tuples
            DebugDraw._initialized = True

    def create_hatch_paint(self, color: int, spacing: float = 4.0) -> 'skia.Paint':
        """Create a paint with the current hatch pattern.
        
        Args:
            color: Color to use for the pattern
            spacing: Spacing between pattern lines
            
        Returns:
            Configured skia.Paint object
        """
        import skia
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=1.0,
            Color=color
        )

        # Create matrix for pattern orientation
        matrix = skia.Matrix()
        
        # Create a path for the line pattern
        path = skia.Path()
        path.moveTo(0, 0)
        path.lineTo(spacing, 0)

        if self.hatch_pattern == HatchPattern.DIAGONAL:
            path.transform(skia.Matrix().setRotate(45))
            effect = skia.Path1DPathEffect.Make(path, spacing, 0, skia.Path1DPathEffect.Style.kRotate_Style)
        elif self.hatch_pattern == HatchPattern.CROSS:
            # Combine two diagonal patterns
            path1 = skia.Path().moveTo(0, 0).lineTo(spacing, 0)
            path2 = skia.Path().moveTo(0, 0).lineTo(spacing, 0)
            path1.transform(skia.Matrix().setRotate(45))
            path2.transform(skia.Matrix().setRotate(-45))
            effect1 = skia.Path1DPathEffect.Make(path1, spacing, 0, skia.Path1DPathEffect.Style.kRotate_Style)
            effect2 = skia.Path1DPathEffect.Make(path2, spacing, 0, skia.Path1DPathEffect.Style.kRotate_Style)
            effect = skia.PathEffect.MakeSum(effect1, effect2)
        elif self.hatch_pattern == HatchPattern.HORIZONTAL:
            effect = skia.Path1DPathEffect.Make(path, spacing, 0, skia.Path1DPathEffect.Style.kTranslate_Style)
        elif self.hatch_pattern == HatchPattern.VERTICAL:
            path.transform(skia.Matrix().setRotate(90))
            effect = skia.Path1DPathEffect.Make(path, spacing, 0, skia.Path1DPathEffect.Style.kTranslate_Style)
        else:  # GRID
            # Combine horizontal and vertical patterns
            path1 = skia.Path().moveTo(0, 0).lineTo(spacing, 0)
            path2 = skia.Path().moveTo(0, 0).lineTo(spacing, 0)
            path2.transform(skia.Matrix().setRotate(90))
            effect1 = skia.Path1DPathEffect.Make(path1, spacing, 0, skia.Path1DPathEffect.Style.kTranslate_Style)
            effect2 = skia.Path1DPathEffect.Make(path2, spacing, 0, skia.Path1DPathEffect.Style.kTranslate_Style)
            effect = skia.PathEffect.MakeSum(effect1, effect2)

        paint.setPathEffect(effect)
        return paint
    
    def enable(self, *flags: DebugDrawFlags) -> None:
        """Enable specific debug drawing flags."""
        for flag in flags:
            self.enabled_flags |= flag
    
    def disable(self, *flags: DebugDrawFlags) -> None:
        """Disable specific debug drawing flags."""
        for flag in flags:
            self.enabled_flags &= ~flag
    
    def is_enabled(self, flag: DebugDrawFlags) -> bool:
        """Check if a specific debug drawing flag is enabled."""
        return bool(self.enabled_flags & flag)
        
    def set_canvas(self, canvas: 'skia.Canvas') -> None:
        """Set the canvas for debug drawing."""
        self._canvas = canvas
        
    def submit_debug_draw(self, draw_closure: Callable[[skia.Canvas], None], layer: DebugLayer) -> None:
        """Submit a debug draw closure to be executed later.
        
        Args:
            draw_closure: Callable that takes a canvas parameter
            layer: Debug layer to draw on
        """
        self._draw_closures.append((layer, draw_closure))
        
    def execute_debug_draws(self) -> None:
        """Execute all submitted debug draw closures in layer order."""
        if not self._canvas:
            return
            
        # Sort by layer
        self._draw_closures.sort(key=lambda x: x[0].value)
        
        # Execute each closure
        for layer, closure in self._draw_closures:
            closure(self._canvas)
            
        # Clear closures after drawing
        self._draw_closures = []

# Global debug draw instance
debug_draw = DebugDraw()
