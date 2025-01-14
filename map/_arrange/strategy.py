"""Strategy system for room arrangement."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from map.room import Room
from map.map import Map

class StrategyType(Enum):
    """Types of room arrangement strategies."""
    LINEAR = auto()
    SYMMETRIC = auto()

@dataclass
class StrategyParams:
    """Base parameters for all strategies."""
    min_rooms: int = 1
    max_rooms: int = 3
    
class Strategy(ABC):
    """Abstract base class for room arrangement strategies."""
    
    def __init__(self, dungeon_map: Map, params: StrategyParams):
        self._map = dungeon_map
        self._params = params
        
    @property
    def map(self) -> Map:
        """The map being generated."""
        return self._map
        
    @property
    def params(self) -> StrategyParams:
        """Strategy parameters."""
        return self._params
        
    @abstractmethod
    def execute(self, rooms_left: int, source_room: Room) -> List[Room]:
        """Execute the strategy.
        
        Args:
            rooms_left: Maximum number of rooms that can be created
            source_room: Room to grow from
            
        Returns:
            List of newly created rooms
        """
        pass
