# Contributing to DungeonGen

Thank you for your interest in contributing to DungeonGen! This guide covers how to contribute, including guidelines for AI-assisted development.

## Getting Started

### Prerequisites

- Python 3.10 or later
- Git

### Development Setup

```bash
git clone https://github.com/benjcooley/dungeongen.git
cd dungeongen
pip install -e ".[dev]"
```

This installs the package in editable mode with development dependencies (pytest, pyright).

### Running Tests

```bash
pytest
```

### Running the Web Preview

```bash
python -m dungeongen.webview.app
```

## Code Style Guide

### Python Style

- **PEP 8** compliant with some flexibility on line length (100 chars preferred)
- **Type hints** required for all public functions and methods
- **Docstrings** required for all public classes and functions (Google style)

### Naming Conventions

```python
# Classes: PascalCase
class DungeonGenerator:
    pass

# Functions and methods: snake_case
def generate_dungeon(seed: int) -> Dungeon:
    pass

# Constants: UPPER_SNAKE_CASE
CELL_SIZE = 40
MAX_ROOM_SIZE = 12

# Private members: leading underscore
class Map:
    def __init__(self):
        self._elements = []  # Private
        
    def _calculate_bounds(self):  # Private method
        pass
```

### Import Organization

```python
# Standard library
import math
import random
from typing import List, Optional, Dict

# Third-party
import numpy as np
import skia

# Local imports (absolute within package)
from dungeongen.layout import DungeonGenerator
from dungeongen.map.map import Map
from dungeongen.graphics.shapes import Rectangle
```

### Type Hints

```python
from typing import List, Optional, Dict, Tuple

def process_rooms(
    rooms: List[Room],
    options: Optional[Options] = None
) -> Dict[str, Room]:
    """Process rooms and return mapping."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def generate(self, seed: Optional[int] = None) -> Dungeon:
    """Generate a complete dungeon layout.
    
    Creates rooms, passages, doors, and other elements based on
    the configured parameters.
    
    Args:
        seed: Random seed for deterministic generation. If None,
            uses a random seed.
    
    Returns:
        A Dungeon instance containing all generated elements.
    
    Raises:
        ValueError: If parameters are invalid.
    """
```

## Architecture Rules

Please read [ARCHITECTURE.md](ARCHITECTURE.md) before contributing. Key rules:

### Separation of Concerns

1. **Layout system** (`dungeongen.layout`) must NOT import from map system
2. **Map system** (`dungeongen.map`) receives layout data only via the adapter
3. **Graphics primitives** are shared utilities used by both systems
4. **Props** are self-contained with their own rendering logic

### Coordinate Systems

- **Layout** uses integer grid coordinates (0, 0 is top-left)
- **Map** uses pixel coordinates (`grid * CELL_SIZE`)
- Use `grid_to_map()` and `map_to_grid()` for conversion

### Element Connections

Map elements connect in chains:
```
Room → Door → Passage → Door → Room
```

Don't break this pattern. Doors and exits are traversal boundaries.

## AI-Assisted Contributions

DungeonGen welcomes AI-assisted development. If you're using AI tools (Cursor, Copilot, Claude, etc.), follow these guidelines:

### Before Starting

1. **Read ARCHITECTURE.md** - Share it with your AI assistant for context
2. **Understand the separation** - Layout vs Map systems
3. **Check existing patterns** - Look at similar code before writing new code

### Prompt Guidelines

Good prompts for AI assistants working on this codebase:

```
I'm working on dungeongen. Please read ARCHITECTURE.md first.
I want to add [feature]. It should go in the [layout/map] system because [reason].
```

### Code Quality Checklist

Before submitting AI-generated code:

- [ ] Type hints on all public APIs
- [ ] Docstrings on public classes/functions
- [ ] No imports from map→layout or layout→map (except via adapter)
- [ ] Tests pass (`pytest`)
- [ ] No new linter errors (`pyright`)
- [ ] Follows existing patterns in the codebase

### Common AI Mistakes to Avoid

1. **Mixing coordinate systems** - Don't use grid coords in map rendering
2. **Breaking encapsulation** - Don't access private `_members` from outside
3. **Over-engineering** - Keep it simple; match existing patterns
4. **Missing type hints** - AI often omits them; add them
5. **Wrong imports** - Check the package structure

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

- Follow the style guide
- Add tests for new functionality
- Update documentation if needed

### 3. Test

```bash
pytest
python -m dungeongen.webview.app  # Manual visual check
```

### 4. Commit

Write clear commit messages:

```
Add water ripple density parameter

- Add ripple_density to WaterFieldParams
- Update water rendering to use new parameter
- Add tests for ripple generation
```

### 5. Submit PR

- Describe what changes and why
- Reference any related issues
- Note if AI-assisted (we're curious, not judgmental!)

## Types of Contributions

### Bug Fixes

- Include a test that reproduces the bug
- Fix should be minimal and focused

### New Features

- Discuss in an issue first for larger features
- Follow existing architectural patterns
- Add documentation

### Documentation

- Fix typos, clarify explanations
- Add examples
- Keep consistent style

### Performance

- Include benchmarks showing improvement
- Don't sacrifice readability for marginal gains

## Testing Guidelines

### Unit Tests

```python
def test_dungeon_generation_deterministic():
    """Same seed should produce same dungeon."""
    params = GenerationParams()
    gen = DungeonGenerator(params)
    
    d1 = gen.generate(seed=42)
    d2 = gen.generate(seed=42)
    
    assert len(d1.rooms) == len(d2.rooms)
    for rid in d1.rooms:
        assert d1.rooms[rid].x == d2.rooms[rid].x
```

### Visual Tests

Some things need visual verification:
- Rendering output
- Water appearance
- Prop placement

Run the web preview and check manually.

## Questions?

- Open an issue for questions
- Check existing issues first
- Be specific about what you're trying to do

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

