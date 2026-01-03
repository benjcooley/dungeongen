"""Flask web application for dungeon layout visualization."""
import random
import base64
import io
from flask import Flask, render_template, request, jsonify

from dungeongen.layout import DungeonGenerator, GenerationParams, DungeonSize, SymmetryType, DungeonArchetype, DungeonValidator
from dungeongen.layout import SVGRenderer
from .adapter import convert_dungeon

app = Flask(__name__)


@app.route('/')
def index():
    """Main page with dungeon visualization."""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """Generate a new dungeon and return SVG."""
    data = request.json or {}
    
    # Parse parameters from request
    params = GenerationParams()
    
    # Size
    size_map = {
        'tiny': DungeonSize.TINY,
        'small': DungeonSize.SMALL,
        'medium': DungeonSize.MEDIUM,
        'large': DungeonSize.LARGE,
        'xlarge': DungeonSize.XLARGE,
    }
    params.size = size_map.get(data.get('size', 'medium'), DungeonSize.MEDIUM)
    
    # Archetype
    archetype_map = {
        'classic': DungeonArchetype.CLASSIC,
        'warren': DungeonArchetype.WARREN,
        'temple': DungeonArchetype.TEMPLE,
        'crypt': DungeonArchetype.CRYPT,
        'cavern': DungeonArchetype.CAVERN,
        'fortress': DungeonArchetype.FORTRESS,
        'lair': DungeonArchetype.LAIR,
    }
    params.archetype = archetype_map.get(data.get('archetype', 'classic'), DungeonArchetype.CLASSIC)
    
    # Symmetry
    symmetry_map = {
        'none': SymmetryType.NONE,
        'bilateral': SymmetryType.BILATERAL,
        'radial2': SymmetryType.RADIAL_2,
        'radial4': SymmetryType.RADIAL_4,
        'partial': SymmetryType.PARTIAL,
    }
    params.symmetry = symmetry_map.get(data.get('symmetry', 'none'), SymmetryType.NONE)
    
    # Packing density (Sparse, Normal, Tight)
    pack_level = data.get('pack', 'normal')
    if pack_level == 'sparse':
        params.density = 0.2
    elif pack_level == 'tight':
        params.density = 0.8
    else:  # normal
        params.density = 0.5
    
    # Room size preference (Cozy, Mixed, Grand)
    roomsize_level = data.get('roomsize', 'mixed')
    if roomsize_level == 'cozy':
        params.room_size_bias = -1.0  # Only small rooms
    elif roomsize_level == 'grand':
        params.room_size_bias = 0.8  # Larger rooms
    else:  # mixed
        params.room_size_bias = 0.0  # Balanced
    
    if data.get('round_rooms', False):
        params.round_room_chance = 0.3
    else:
        params.round_room_chance = 0.05
    
    if data.get('halls', True):
        params.hall_chance = 0.15
    else:
        params.hall_chance = 0.0
    
    # Cross-connect level (None, Low, Med, High)
    cross_level = data.get('cross', 'med')
    if cross_level == 'none':
        params.loop_factor = 0.0
        params.extra_room_connections = 0.0
        params.extra_passage_junctions = 0.0
    elif cross_level == 'low':
        params.loop_factor = 0.15
        params.extra_room_connections = 0.1
        params.extra_passage_junctions = 0.05
    elif cross_level == 'med':
        params.loop_factor = 0.3
        params.extra_room_connections = 0.2
        params.extra_passage_junctions = 0.15
    else:  # high
        params.loop_factor = 0.5
        params.extra_room_connections = 0.4
        params.extra_passage_junctions = 0.3
    
    # Passage width: 1 grid cell (standard D&D corridor)
    params.passage_width = 1
    
    # Symmetry breaking
    params.symmetry_break = float(data.get('symmetry_break', 0.2))
    
    # Water depth level
    water_level = data.get('water', 'dry')
    water_depth_map = {
        'dry': 0.0,
        'puddles': 0.75,
        'pools': 0.60,
        'lakes': 0.45,
        'flooded': 0.30,
    }
    water_depth = water_depth_map.get(water_level, 0.0)
    params.water_enabled = water_depth > 0
    params.water_threshold = water_depth  # Store for adapter
    
    # Water tuning sliders (temporary debug controls)
    water_scale = data.get('water_scale', 0.018)  # Noise scale
    water_res = data.get('water_res', 0.2)  # Resolution scale
    water_stroke = data.get('water_stroke', 3.5)  # Shoreline stroke width
    water_ripple = data.get('water_ripple', 8.0)  # Ripple inset distance
    
    # Display options
    show_numbers = data.get('show_numbers', True)
    
    # Seed
    seed = data.get('seed')
    if seed is not None and seed != '':
        try:
            seed = int(seed)
        except ValueError:
            seed = hash(seed) % (2**31)
    else:
        seed = random.randint(0, 2**31)
    
    # Generate dungeon
    generator = DungeonGenerator(params)
    dungeon = generator.generate(seed=seed)
    
    # Validate dungeon (skip for tight packing - rules don't apply)
    violations = []
    validation_summary = ""
    if pack_level != 'tight':
        validator = DungeonValidator(dungeon)
        violations = validator.validate()
        validation_summary = validator.summary()
    
    # Render normal SVG (Map view)
    renderer = SVGRenderer(
        grid_size=20,
        show_grid=True,
        show_labels=data.get('show_labels', False)
    )
    svg = renderer.render(dungeon, violations=violations)
    
    # Render debug SVG (occupancy grid)
    debug_svg = renderer.render(dungeon, violations=violations, occupancy=generator.occupancy)
    
    # Render using dungeongen (high-quality SVG render)
    render_svg = None
    render_error = None
    try:
        render_svg = render_dungeon_to_svg(
            dungeon, 
            water_depth=water_depth,
            water_scale=water_scale,
            water_res=water_res,
            water_stroke=water_stroke,
            water_ripple=water_ripple,
            show_numbers=show_numbers
        )
        if render_svg:
            print(f"[Render] Success: {len(render_svg)} bytes SVG")
        else:
            render_error = "render_dungeon_to_svg returned None"
            print(f"[Render] Failed: {render_error}")
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        render_error = f"{type(e).__name__}: {e}\n\n{error_traceback}"
        print(f"[Render] Exception: {e}")
        traceback.print_exc()
    
    return jsonify({
        'svg': svg,
        'debug_svg': debug_svg,
        'render_svg': render_svg,
        'render_available': render_svg is not None,
        'render_error': render_error,
        'seed': seed,
        'room_count': len(dungeon.rooms),
        'passage_count': len(dungeon.passages),
        'door_count': len(dungeon.doors),
        'stair_count': len(dungeon.stairs),
        'exit_count': len(dungeon.exits),
        'violations': len(violations),
        'validation': validation_summary,
    })


def render_dungeon_to_svg(dungeon, grid_size=20, padding=40, water_depth=0.0, water_scale=0.018, water_res=0.2, water_stroke=3.5, water_ripple=8.0, show_numbers=True):
    """Render dungeon using dungeongen and return as SVG string.
    
    Renders with same framing as layout SVG so rooms align when switching views.
    Returns resolution-independent SVG.
    """
    import sys
    sys.path.insert(0, '/Users/benjamincooley/projects/dungeongen')
    import skia
    
    # Get dungeon bounds (same as SVG renderer uses)
    bounds = dungeon.bounds  # (min_x, min_y, max_x, max_y) in grid coords
    
    # Calculate canvas size to match SVG renderer exactly
    canvas_width = (bounds[2] - bounds[0]) * grid_size + padding * 2
    canvas_height = (bounds[3] - bounds[1]) * grid_size + padding * 2
    
    # Convert to dungeongen format with water settings
    # The adapter normalizes coords: dungeon grid (bounds[0], bounds[1]) -> map grid (0, 0)
    dungeon_map = convert_dungeon(
        dungeon, 
        water_depth=water_depth,
        water_scale=water_scale,
        water_res=water_res,
        water_stroke=water_stroke,
        water_ripple=water_ripple,
        show_numbers=show_numbers
    )
    
    # dungeongen uses 64 map units per grid cell (CELL_SIZE constant)
    # SVG uses grid_size (20) pixels per grid cell
    # Scale converts map units to pixels: 20/64 = 0.3125
    map_units_per_grid = 64
    scale = grid_size / map_units_per_grid
    
    # The adapter normalized coords so map (0,0) = dungeon (bounds[0], bounds[1])
    # In SVG, dungeon (bounds[0], bounds[1]) is at pixel (padding, padding)
    # So map (0,0) should also be at pixel (padding, padding)
    offset_x = padding
    offset_y = padding
    
    # Create SVG canvas using Skia
    stream = skia.DynamicMemoryWStream()
    canvas = skia.SVGCanvas.Make(skia.Rect.MakeWH(canvas_width, canvas_height), stream)
    
    # Draw white background
    bg_paint = skia.Paint(Color=skia.Color(255, 255, 255))
    canvas.drawRect(skia.Rect.MakeWH(canvas_width, canvas_height), bg_paint)
    
    # Build transform: scale then translate
    transform = skia.Matrix()
    transform.setScale(scale, scale)
    transform.postTranslate(offset_x, offset_y)
    
    # Render the map
    dungeon_map.render(canvas, transform)
    
    # Finalize the SVG
    del canvas  # Must delete canvas to flush to stream
    
    # Get SVG data as string
    data = stream.detachAsData()
    return data.bytes().decode('utf-8')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050, use_reloader=False)

