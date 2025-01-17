"""Debug drawing configuration."""

from enum import Flag, auto

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
            DebugDraw._initialized = True
    
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
