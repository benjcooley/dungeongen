# Dungeon Map Generator

A Python-based dungeon map generator that creates stylized, crosshatched dungeon layouts using Skia graphics. This is a reimplementation of [Watabou's One Page Dungeon Generator](https://watabou.itch.io/one-page-dungeon).

## Attribution

This project is inspired by and reimplements the excellent work of Watabou:
- Original generator: [One Page Dungeon](https://watabou.itch.io/one-page-dungeon)
- Creator: [Watabou on itch.io](https://watabou.itch.io)
- Support the original creator: [Watabou on Patreon](https://www.patreon.com/watawatabou)

Please consider supporting Watabou's work through [Patreon](https://www.patreon.com/watawatabou) if you find this or the original generator useful!

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

Copyright 2024 Claude (AI Development Advisor)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Credits

This project is a reimplementation of Watabou's One Page Dungeon Generator:
- Original creator: [Watabou](https://watabou.itch.io)
- Human Advisor/Producer: Benjamin Cooley
- Implementation: Claude 3.5 Sonnet and OpenAI ChatGPT 4o

Please consider supporting the original creator through [Patreon](https://www.patreon.com/watawatabou)!
