"""Strategy system for room arrangement."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from map.room import Room
from map.map import Map

class StrategyType(Enum):
    """Types of room arrangement strategies."""
    LINEAR = auto()

@dataclass
class StrategyParams:
    """Parameters that can be tuned for strategies."""
    min_rooms: int = 1
    max_rooms: int = 3
    min_spacing: int = 2
    max_spacing: int = 4
    branch_chance: float = 0.3
    
class Strategy:
    """Base class for room arrangement strategies."""
    
    def __init__(self, dungeon_map: Map, params: StrategyParams):
        self.dungeon_map = dungeon_map
        self.params = params
        
    def execute(self, rooms_left: int, source_room: Room) -> List[Room]:
        """Execute the strategy.
        
        Args:
            rooms_left: Maximum number of rooms that can be created
            source_room: Room to grow from
            
        Returns:
            List of newly created rooms
        """
        raise NotImplementedError
