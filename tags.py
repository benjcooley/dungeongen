"""Tags used to influence random distributions in map generation."""

from enum import Enum, auto

class Tags:
    """Tags that can be used to customize random distributions."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    
    def __str__(self) -> str:
        """Return the tag name in lowercase for use as a string."""
        return self.name.lower()
