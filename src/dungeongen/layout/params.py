"""Generation parameters and configuration."""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, Optional


class DungeonSize(Enum):
    TINY = auto()      # 4-6 rooms
    SMALL = auto()     # 6-10 rooms
    MEDIUM = auto()    # 10-16 rooms
    LARGE = auto()     # 16-24 rooms
    XLARGE = auto()    # 24-40 rooms


class SymmetryType(Enum):
    NONE = auto()
    BILATERAL = auto()   # Mirror across one axis
    RADIAL_2 = auto()    # 2-fold rotational symmetry (180°)
    RADIAL_4 = auto()    # 4-fold rotational symmetry (90°)
    PARTIAL = auto()     # Symmetric core, organic edges


class DungeonArchetype(Enum):
    """Structural patterns that define dungeon character."""
    CLASSIC = auto()     # Branching paths, dead-ends, treasure rooms
    WARREN = auto()      # Dense maze of small interconnected chambers
    TEMPLE = auto()      # Grand central nave, symmetrical wings
    CRYPT = auto()       # Linear corridor with side chambers
    CAVERN = auto()      # Organic, irregular flowing spaces
    FORTRESS = auto()    # Defensive layers, chokepoints
    LAIR = auto()        # Central boss chamber with approaches


# Room count ranges for each size
ROOM_COUNTS = {
    DungeonSize.TINY: (4, 6),
    DungeonSize.SMALL: (6, 10),
    DungeonSize.MEDIUM: (10, 16),
    DungeonSize.LARGE: (16, 24),
    DungeonSize.XLARGE: (24, 40),
}

# Base room size pools (width, height) for different biases
ROOM_TEMPLATES = {
    # Cozy: mostly tiny rooms, max 5x5 (rare), some small elongated
    'cozy': [
        (2, 3), (3, 2), (3, 3), (2, 4), (4, 2),  # Tiny (high frequency)
        (2, 3), (3, 2), (3, 3), (3, 3),  # More weight on tiny
        (3, 4), (4, 3), (3, 5), (5, 3),  # Small elongated
        (4, 4),  # 4x4 square (less common)
        (5, 5),  # 5x5 square (rare - only 1 entry)
        (3, 7), (7, 3),  # Narrow halls (rare)
    ],
    'small': [
        (2, 3), (3, 2), (3, 3), (2, 4), (4, 2), (3, 4), (4, 3),
        (3, 5), (5, 3), (4, 4), (4, 5), (5, 4),
    ],
    'medium': [
        (4, 4), (4, 5), (5, 4), (5, 5), (4, 6), (6, 4), (5, 6), (6, 5),
        (5, 7), (7, 5), (3, 7), (7, 3),
    ],
    'large': [
        (6, 6), (6, 7), (7, 6), (7, 7), (6, 8), (8, 6), (7, 8), (8, 7), (8, 8),
        (5, 9), (9, 5), (7, 9), (9, 7),
    ],
}

# Circular room radii
# Circular room radii - only values that give odd diameters (3x3, 5x5, 7x7, 9x9)
# A radius of R gives a (2R+1) x (2R+1) bounding box
# radius=1 → 3x3, radius=2 → 5x5, radius=3 → 7x7, radius=4 → 9x9
CIRCLE_RADII = {
    'cozy': [1, 1, 1, 2],  # Mostly 3x3, some 5x5 (25% chance)
    'small': [1, 2],       # 3x3, 5x5
    'medium': [2, 3],      # 5x5, 7x7
    'large': [3, 4],       # 7x7, 9x9
}

# Junction meta-room templates
# Each junction has (arm_length, center_width) - arm_length is how far side passages extend
# These are rendered as passage cells, not room cells
JUNCTION_TEMPLATES = {
    'cozy': {
        't_junction': [(2, 1), (3, 1)],      # T-split: 2-3 cell arms
        'cross': [(2, 1), (3, 1)],           # 4-way: 2-3 cell arms  
        'y_split': [(2, 1), (3, 1)],         # Y-split (branches forward)
    },
    'small': {
        't_junction': [(3, 1), (4, 1), (5, 1)],
        'cross': [(3, 1), (4, 1)],
        'y_split': [(3, 1), (4, 1)],
    },
    'medium': {
        't_junction': [(4, 1), (5, 1), (6, 1)],
        'cross': [(4, 1), (5, 1)],
        'y_split': [(4, 1), (5, 1)],
    },
    'large': {
        't_junction': [(5, 1), (6, 1), (7, 1)],
        'cross': [(5, 1), (6, 1)],
        'y_split': [(5, 1), (6, 1)],
    },
}


@dataclass
class GenerationParams:
    """Parameters controlling dungeon generation."""
    
    # Archetype - defines overall structure
    archetype: DungeonArchetype = DungeonArchetype.CLASSIC
    
    # Size
    size: DungeonSize = DungeonSize.MEDIUM
    room_count: Optional[Tuple[int, int]] = None  # Override auto count
    
    # Rooms
    room_size_bias: float = 0.0  # -1.0 (small) to 1.0 (large)
    round_room_chance: float = 0.15  # Chance of circular rooms
    hall_chance: float = 0.1  # Chance of long narrow halls
    
    # Layout
    density: float = 0.5  # 0.0 (sparse) to 1.0 (tight)
    symmetry: SymmetryType = SymmetryType.NONE
    symmetry_break: float = 0.2  # 0.0 (perfect) to 1.0 (heavy breaking)
    linearity: float = 0.3  # 0.0 (branching) to 1.0 (linear)
    loop_factor: float = 0.3  # Extra connections beyond MST (Jaquaying)
    
    # Passages
    passage_width: int = 1  # Default passage width in grid units (1 = standard D&D corridor)
    winding: float = 0.0  # 0.0 (direct) to 1.0 (winding)
    
    # Second pass connections (Jaquaying - creates loops, shortcuts, alternate paths)
    extra_room_connections: float = 0.2  # 0.0 (none) to 1.0 (many) - chance to add room-to-room beyond MST
    extra_passage_junctions: float = 0.15  # 0.0 (none) to 1.0 (many) - chance to add T-junctions to passages
    
    # Multi-level
    levels: int = 1
    stair_frequency: float = 0.1
    
    # Water
    water_enabled: bool = False
    water_threshold: float = 0.15  # Noise threshold (-1 to 1), higher = less water
    
    # Seed
    seed: Optional[int] = None
    
    def get_room_count_range(self) -> Tuple[int, int]:
        """Get the room count range for this configuration."""
        if self.room_count:
            return self.room_count
        return ROOM_COUNTS[self.size]
    
    def get_room_templates(self) -> list:
        """Get room size templates based on bias.
        
        bias < -0.5 (cozy): only cozy templates (max 5x5, mostly tiny)
        bias < 0.0: small rooms
        bias < 0.5: small + medium
        bias >= 0.5: add large rooms  
        bias >= 0.8 (grand): more large rooms
        """
        templates = []
        
        # Cozy mode: use dedicated cozy templates (max 5x5)
        if self.room_size_bias < -0.5:
            return ROOM_TEMPLATES['cozy']
        
        # Always include small rooms
        templates.extend(ROOM_TEMPLATES['small'])
        
        # Add medium rooms for balanced/grand
        if self.room_size_bias >= 0.0:
            templates.extend(ROOM_TEMPLATES['medium'])
        
        # Add large rooms for grand settings
        if self.room_size_bias >= 0.5:
            templates.extend(ROOM_TEMPLATES['large'])
        
        # Double weight large for very grand
        if self.room_size_bias >= 0.8:
            templates.extend(ROOM_TEMPLATES['large'])
        
        return templates
    
    def get_circle_radii(self) -> list:
        """Get circular room radii based on bias.
        
        bias < -0.5 (cozy): only 3x3 circles
        bias < 0.3: small + medium circles  
        bias >= 0.3: medium + large circles
        """
        if self.room_size_bias < -0.5:
            return CIRCLE_RADII['cozy']  # Mostly 3x3, some 5x5
        elif self.room_size_bias < 0.3:
            return CIRCLE_RADII['small'] + CIRCLE_RADII['medium']
        else:
            return CIRCLE_RADII['medium'] + CIRCLE_RADII['large']
    
    def get_junction_templates(self) -> dict:
        """Get junction meta-room templates based on bias.
        
        Returns dict with 't_junction', 'cross', 'y_split' keys,
        each containing list of (arm_length, center_width) tuples.
        """
        if self.room_size_bias < -0.5:
            return JUNCTION_TEMPLATES['cozy']
        elif self.room_size_bias < 0.0:
            return JUNCTION_TEMPLATES['small']
        elif self.room_size_bias < 0.5:
            return JUNCTION_TEMPLATES['medium']
        else:
            return JUNCTION_TEMPLATES['large']

