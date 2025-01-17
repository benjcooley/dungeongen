"""Logging configuration for the dungeon generator."""

import logging
from rich.logging import RichHandler
from enum import Flag, auto
from typing import Set

class LogTags(Flag):
    """Tags for controlling different areas of logging output."""
    NONE = 0
    GENERATION = auto()    # Room/passage generation
    ARRANGEMENT = auto()   # Room arrangement
    DECORATION = auto()    # Room decoration and props
    VALIDATION = auto()    # Shape validation and intersection
    OCCUPANCY = auto()     # Occupancy grid operations
    DEBUG = auto()         # Debug information
    ALL = (GENERATION | ARRANGEMENT | DECORATION | 
           VALIDATION | OCCUPANCY | DEBUG)

class DungeonLogger:
    """Centralized logging configuration for the dungeon generator."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not DungeonLogger._initialized:
            # Set up rich handler
            rich_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_path=False,
                width=200,  # Increase width to prevent wrapping
            )
            rich_handler.setFormatter(logging.Formatter(
                '%(message)s',
                datefmt='[%X]'
            ))
            
            # Configure root logger
            self.logger = logging.getLogger('dungeon')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(rich_handler)
            
            # Initialize enabled tags
            self.enabled_tags: Set[LogTags] = set()
            
            DungeonLogger._initialized = True
    
    def set_level(self, level: int) -> None:
        """Set the logging level."""
        self.logger.setLevel(level)
    
    def enable_tags(self, *tags: LogTags) -> None:
        """Enable specific logging tags."""
        self.enabled_tags.update(tags)
    
    def disable_tags(self, *tags: LogTags) -> None:
        """Disable specific logging tags."""
        self.enabled_tags.difference_update(tags)
    
    def log(self, tag: LogTags, message: str, *args, **kwargs) -> None:
        """Log a message if its tag is enabled."""
        if tag in self.enabled_tags:
            self.logger.info(message, *args, **kwargs)
    
    def debug(self, tag: LogTags, message: str, *args, **kwargs) -> None:
        """Log a debug message if its tag is enabled."""
        if tag in self.enabled_tags:
            self.logger.debug(message, *args, **kwargs)
    
    def warning(self, tag: LogTags, message: str, *args, **kwargs) -> None:
        """Log a warning message if its tag is enabled."""
        if tag in self.enabled_tags:
            self.logger.warning(message, *args, **kwargs)
    
    def error(self, tag: LogTags, message: str, *args, **kwargs) -> None:
        """Log an error message regardless of tag."""
        self.logger.error(message, *args, **kwargs)

# Global logger instance
logger = DungeonLogger()
