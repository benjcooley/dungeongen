"""Debug drawing configuration."""

from enum import Flag, auto

class HatchPattern(Enum):
    """Available hatch patterns for debug visualization."""
    DIAGONAL = auto()      # 45-degree diagonal lines
    CROSS = auto()         # Crossed diagonal lines
    HORIZONTAL = auto()    # Horizontal lines
    VERTICAL = auto()      # Vertical lines
    GRID = auto()         # Grid pattern

class DebugDrawFlags(Flag):
    """Flags controlling different aspects of debug visualization."""
    NONE = 0
    PROP_BOUNDS = auto()      # Draw red bounds around props
    GRID = auto()             # Draw basic grid visualization
    GRID_BOUNDS = auto()      # Draw blue grid-aligned prop bounds
    OCCUPANCY = auto()        # Draw occupied grid cells
    ALL = (PROP_BOUNDS | GRID | GRID_BOUNDS | OCCUPANCY)

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
        
        if self.hatch_pattern == HatchPattern.DIAGONAL:
            matrix.setRotate(45)
            effect = skia.PathEffect.MakeLine2D(spacing, matrix)
        elif self.hatch_pattern == HatchPattern.CROSS:
            # Combine two diagonal patterns
            effect1 = skia.PathEffect.MakeLine2D(spacing, skia.Matrix().setRotate(45))
            effect2 = skia.PathEffect.MakeLine2D(spacing, skia.Matrix().setRotate(-45))
            effect = skia.PathEffect.MakeSum(effect1, effect2)
        elif self.hatch_pattern == HatchPattern.HORIZONTAL:
            effect = skia.PathEffect.MakeLine2D(spacing, matrix)
        elif self.hatch_pattern == HatchPattern.VERTICAL:
            matrix.setRotate(90)
            effect = skia.PathEffect.MakeLine2D(spacing, matrix)
        else:  # GRID
            # Combine horizontal and vertical patterns
            effect1 = skia.PathEffect.MakeLine2D(spacing, skia.Matrix())
            effect2 = skia.PathEffect.MakeLine2D(spacing, skia.Matrix().setRotate(90))
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

# Global debug draw instance
debug_draw = DebugDraw()
