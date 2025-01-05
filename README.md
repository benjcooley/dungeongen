# Dungeon Map Generator

A Python-based dungeon map generator that creates stylized, crosshatched dungeon layouts using Skia graphics.

![Example Map Output](map_output.png)

## Features

- Procedural dungeon map generation
- Rectangular and circular rooms
- Connecting passages and doors
- Decorative props (rocks, coffins)
- Artistic crosshatching effects
- Grid-based layout system
- Poisson disk sampling for prop placement
- Vector graphics output (PNG, PDF, SVG)

## Requirements

- Python 3.8+
- skia-python 87.5+

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the main script to generate a sample dungeon map:

```bash
python main.py
```

This will create a map with:
- A rectangular starting room
- A connecting passage
- A circular end room
- Decorative props
- Doors (both open and closed)

The output will be saved as `map_output.png`.

## Project Structure

```
.
├── algorithms/
│   ├── lines.py         # Line intersection utilities
│   ├── poisson.py       # Poisson disk sampling
│   ├── shapes.py        # Basic shape definitions
│   └── spacialhash.py   # Spatial hashing for optimization
├── graphics/
│   ├── conversions.py   # Grid/pixel coordinate conversion
│   └── crosshatch.py    # Crosshatching pattern generator
├── map/
│   ├── door.py         # Door element implementation
│   ├── passage.py      # Passage element implementation
│   └── room.py         # Room element implementation
└── main.py             # Main entry point
```

## Key Components

### Map Elements

- **Rooms**: Rectangular or circular areas that form the main spaces
- **Passages**: Corridors connecting rooms
- **Doors**: Connectors that can be open or closed
- **Props**: Decorative elements like rocks and coffins

### Graphics

- **Crosshatching**: Artistic wall texturing
- **Vector Output**: Clean, scalable graphics
- **Grid System**: Consistent layout measurements

### Algorithms

- **Poisson Disk Sampling**: For natural-looking prop placement
- **Spatial Hashing**: Efficient neighbor lookups
- **Shape Operations**: Boolean operations for complex shapes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your chosen license here]

## Credits

[Add credits/acknowledgments here]
