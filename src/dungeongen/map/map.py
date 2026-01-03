"""Map container class definition."""

import math
import random
from typing import Generic, Iterator, List, Optional, Sequence, Tuple, TypeVar, TYPE_CHECKING
from dungeongen.map.enums import Tags
from dungeongen.logging_config import logger, LogTags
from dungeongen.debug_config import debug_draw, DebugDrawFlags

import skia

from dungeongen.graphics.shapes import Circle, Rectangle, Shape, ShapeGroup
from dungeongen.constants import CELL_SIZE
from dungeongen.graphics.conversions import grid_to_map
from dungeongen.drawing.crosshatch import draw_crosshatches
from dungeongen.drawing.crosshatch_tiled import draw_crosshatches_tiled, generate_hatch_tile, HatchTileData
from dungeongen.drawing.water import WaterStyle
from dungeongen.map.enums import Layers
from typing import Generic, Iterator, List, Optional, Sequence, Tuple, TypeVar, TYPE_CHECKING
from dungeongen.map.grid import GridStyle, draw_region_grid
from dungeongen.map.mapelement import MapElement
from dungeongen.map.occupancy import ElementType, OccupancyGrid
from dungeongen.map.region import Region
from dungeongen.map.room import Room, RoomType
from dungeongen.map.water_layer import WaterLayer, WaterFieldParams, WaterDepth
from dungeongen.options import Options

if TYPE_CHECKING:
    from dungeongen.map._arrange.arrange_utils import RoomDirection
    from dungeongen.map.door import Door, DoorType
    from dungeongen.map.room import Room, RoomType
    from dungeongen.map.passage import Passage
    from dungeongen.map.exit import Exit

REGION_INFLATE = CELL_SIZE * 0.025

TMapElement = TypeVar('TMapElement', bound='MapElement')

_invalid_map: Optional['Map'] = None

class Map:
    """Container for all map elements with type-specific access."""
    
    def __init__(self, options: 'Options') -> None:
        self._elements: List[MapElement] = []
        self._options: Options = options
        self._bounds = Rectangle(0, 0, CELL_SIZE, CELL_SIZE)  # Default to single cell at origin
        self._bounds_dirty: bool = True
        self.occupancy = OccupancyGrid(200, 200)  # Initialize with default size
        self._hatch_tile: Optional[HatchTileData] = None  # Cached crosshatch tile
        self._water_layer: Optional[WaterLayer] = None  # Water generation layer
        self._water_depth: float = WaterDepth.DRY  # Water depth level (0 = disabled)
    
    @staticmethod
    def get_invalid_map() -> 'Map':
        """Get a shared instance of the 'invalid' map. Used instead of None for field defaults."""
        global _invalid_map
        if not _invalid_map:
            _invalid_map = Map(Options.get_invalid_options())
        return _invalid_map
    
    @property
    def is_invalid(self) -> bool:
        """Check if this map is the 'invalid' map."""
        return self == Map.get_invalid_map()
    
    @property
    def hatch_tile(self) -> HatchTileData:
        """Get cached crosshatch tile, generating if needed."""
        if self._hatch_tile is None:
            self._hatch_tile = generate_hatch_tile(self._options, grid_cells=4, seed=4242)
        return self._hatch_tile
    
    def set_water(self, depth: float, seed: int = 42, lf_scale: float = 0.018, resolution_scale: float = 0.2,
                  stroke_width: float = 3.5, ripple_inset: float = 8.0) -> None:
        """Enable water generation with the given depth level.
        
        Args:
            depth: Water depth from WaterDepth constants (DRY, PUDDLES, POOLS, LAKES, FLOODED)
            seed: Random seed for water generation
            lf_scale: Noise scale for water features (0.016 = grid-scale blobs)
            resolution_scale: Resolution scale (0.3 = 30% res, faster/coarser)
            stroke_width: Shoreline stroke width
            ripple_inset: Distance to inset ripple lines from shore
        """
        self._water_depth = depth
        self._water_lf_scale = lf_scale
        self._water_res_scale = resolution_scale
        self._water_stroke_width = stroke_width
        self._water_ripple_inset = ripple_inset
        if depth > 0:
            # Will be initialized lazily when bounds are known
            self._water_seed = seed
        else:
            self._water_layer = None
    
    @property
    def water_layer(self) -> Optional[WaterLayer]:
        """Get water layer, generating if needed."""
        if self._water_depth <= 0:
            return None
        
        if self._water_layer is None:
            # Generate water based on map bounds
            bounds = self.bounds
            width = int(bounds.width)
            height = int(bounds.height)
            
            if width > 0 and height > 0:
                params = WaterFieldParams(
                    depth=self._water_depth,
                    lf_scale=getattr(self, '_water_lf_scale', 0.015),
                    resolution_scale=getattr(self, '_water_res_scale', 0.5)
                )
                self._water_layer = WaterLayer(width, height, self._water_seed, params)
                self._water_layer.generate()
        
        return self._water_layer

    @property
    def elements(self) -> Sequence[MapElement]:
        """Read only access to map elements."""
        return self._elements
    
    @property
    def element_count(self) -> int:
        """Get the number of map elements."""
        return len(self._elements)
    
    @property 
    def options(self) -> 'Options':
        """Get the current options."""
        return self._options
    
    @property 
    def bounds(self) -> Rectangle:
        """Get the current bounding rectangle, recalculating if needed."""
        if self._bounds_dirty or self._bounds is None:
            self._recalculate_bounds()
        return self._bounds

    def add_element(self, element: TMapElement) -> TMapElement:
        """Add a map element.
        
        Args:
            element: The map element to add
            
        Returns:
            The added element
            
        Raises:
            ValueError: If the element's bounds exceed reasonable limits
        """
        if self.is_invalid:
            raise ValueError("Cannot add elements to the 'invalid' map")
        
        # Validate element bounds
        bounds = element.bounds
        MAX_DIMENSION = 100 * CELL_SIZE  # 100 grid cells
        
        if (abs(bounds.x) > MAX_DIMENSION or 
            abs(bounds.y) > MAX_DIMENSION or
            bounds.width > MAX_DIMENSION or 
            bounds.height > MAX_DIMENSION):
            raise ValueError(
                f"Element bounds exceed reasonable limits (±{MAX_DIMENSION}): "
                f"pos=({bounds.x}, {bounds.y}), "
                f"size={bounds.width}x{bounds.height}"
            )

        if not element.map.is_invalid:
            element.map.remove_element(element)

        element._map = self
        element._options = self._options
        self._elements.append(element)
        self._bounds_dirty = True

        element.draw_occupied(self.occupancy, len(self._elements) - 1)

        return element
    
    def remove_element(self, element: MapElement) -> None:
        """Remove a map element."""
        if self.is_invalid:
            raise ValueError("Cannot remove elements from the 'invalid' map")        
        if element in self._elements:
            self._elements.remove(element)
            element._map = Map.get_invalid_map()
            self._bounds_dirty = True
            self.recalculate_occupied()
    
    @property
    def rooms(self) -> Iterator['Room']:
        """Returns a new iteralble of rooms in the map."""
        return (elem for elem in self._elements if isinstance(elem, Room))
    
    @property
    def doors(self) -> Iterator['Door']:
        """Returns a new iterable of all doors in the map."""
        from dungeongen.map.door import Door
        return (elem for elem in self._elements if isinstance(elem, Door))
    
    @property
    def exits(self) -> Iterator['Exit']:
        """Returns a new iterable of all exits in the map."""
        from dungeongen.map.exit import Exit
        return (elem for elem in self._elements if isinstance(elem, Exit))
    
    @property
    def passages(self) -> Iterator['Passage']:
        """Returns a new iterable of all passages in the map."""
        from dungeongen.map.passage import Passage
        return (elem for elem in self._elements if isinstance(elem, Passage))
    
    @property
    def stairs(self) -> Iterator['Stairs']:
        """Returns a new iterable all stairs in the map."""
        return (elem for elem in self._elements if isinstance(elem, Stairs))

    def _trace_connected_region(self, 
                              element: MapElement,
                              visited: set[MapElement],
                              region: list[MapElement]) -> None:
        """Recursively trace connected elements that aren't separated by closed doors or exits."""
        from dungeongen.map.door import Door
        from dungeongen.map.exit import Exit
        
        if element in visited:
            return
        
        visited.add(element)
        region.append(element)
        
        for connection in element.connections:
            # If connection is a closed door, add its side shape but don't traverse
            if isinstance(connection, Door) and not connection.open:
                region.append(connection.get_side_shape(element))
                continue
            # If connection is an exit, add its chip shape but don't traverse (it's terminal)
            if isinstance(connection, Exit):
                region.append(connection.get_side_shape(element))
                continue
            self._trace_connected_region(connection, visited, region)
    

    def _recalculate_bounds(self) -> None:
        """Recalculate the bounding rectangle that encompasses all map elements."""
        if not self._elements:
            # Keep existing bounds if empty
            return
        
        # Start with first element's bounds
        bounds = self._elements[0].bounds
        
        # Expand to include all other elements
        for element in self._elements[1:]:
            elem_bounds = element.bounds
            bounds = Rectangle(
                min(bounds.x, elem_bounds.x),
                min(bounds.y, elem_bounds.y),
                max(bounds.x + bounds.width, elem_bounds.x + elem_bounds.width) - min(bounds.x, elem_bounds.x),
                max(bounds.y + bounds.height, elem_bounds.y + elem_bounds.height) - min(bounds.y, elem_bounds.y)
            )
        
        self._bounds = bounds
        self._bounds_dirty = False
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied by any map element."""
        return self.occupancy.is_occupied(x, y)
    
    def get_element_at(self, x: int, y: int) -> Optional[MapElement]:
        """Get the map element at a grid position.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            
        Returns:
            The MapElement at that position, or None if unoccupied
        """
        idx = self.occupancy.get_element_index(x, y)
        if idx >= 0:
            return self._elements[idx]
        return None
    
    def _make_regions(self) -> list[Region]:
        """Make shape regions for each contiguous area of the map.
        
        Returns:
            List of Regions, each containing a ShapeGroup and the MapElements in that region.
        """
        from dungeongen.map.exit import Exit
        
        visited: set[MapElement] = set()
        regions: list[Region] = []
        
        # Find all connected regions
        for element in self._elements:
            if element in visited:
                continue
            
            # Skip Exits as starting points - they provide chips to connected regions
            # but shouldn't start their own regions
            if isinstance(element, Exit):
                visited.add(element)
                continue
            
            # Trace this region
            region_elements: list[MapElement] = []
            self._trace_connected_region(element, visited, region_elements)
            
            # Create Region for this area if we found elements
            if region_elements:
                # Get shapes from elements and any door/exit side shapes
                shapes = []
                final_elements = []
                for item in region_elements:
                    if isinstance(item, MapElement):
                        shapes.append(item.shape.inflated(REGION_INFLATE))
                        final_elements.append(item)
                    else:  # ShapeGroup from door/exit side
                        shapes.append(item)
                        
                regions.append(Region(
                    shape=ShapeGroup.combine(shapes),
                    elements=final_elements
                ))
        
        return regions

    def calculate_fit_transform(self, canvas_width: int, canvas_height: int) -> skia.Matrix:
        """Calculate a transform matrix that scales and centers the map to fit a canvas.
        
        The transform will:
        - Scale the map uniformly to fit within the canvas dimensions
        - Center the map horizontally and vertically
        - Apply padding based on options.map_border_cells
        
        Args:
            canvas_width: Width of the target canvas in pixels
            canvas_height: Height of the target canvas in pixels
            
        Returns:
            A Skia Matrix with scale and translation to fit the map in the canvas
        """
        bounds = self.bounds
        
        # Convert padding from grid units to drawing units
        padding_x, padding_y = grid_to_map(self.options.map_border_cells, self.options.map_border_cells)
        
        # Add padding to bounds for scale calculation
        padded_width = bounds.width + (2 * padding_x)
        padded_height = bounds.height + (2 * padding_y)
        
        # Calculate scale to fit padded bounds in canvas
        scale_x = canvas_width / padded_width
        scale_y = canvas_height / padded_height
        scale = min(scale_x, scale_y)
        
        # Calculate translation to center the map with padding
        translate_x = ((canvas_width - (bounds.width * scale)) / 2) - (bounds.x * scale)
        translate_y = ((canvas_height - (bounds.height * scale)) / 2) - (bounds.y * scale)
        
        # Create transform matrix
        matrix = skia.Matrix()
        matrix.setScale(scale, scale)
        matrix.postTranslate(translate_x, translate_y)
        return matrix

    def create_rectangular_room(self, grid_x: float, grid_y: float, grid_width: float, grid_height: float) -> 'Room':
        """Create a rectangular room at the specified grid position.
        
        Args:
            grid_x: Grid x coordinate
            grid_y: Grid y coordinate
            grid_width: Width in grid units
            grid_height: Height in grid units
            
        Returns:
            The created Room instance
        """
        if self.is_invalid:
            raise ValueError("Cannot create room in the 'invalid' map")
        from dungeongen.map.room import Room, RoomType
        return self.add_element(Room.from_grid(grid_x, grid_y, grid_width, grid_height, room_type=RoomType.RECTANGULAR))
    
    def create_circular_room(self, grid_x: float, grid_y: float, grid_diameter: float) -> 'Room':
        """Create a circular room at the specified grid position.
        
        Args:
            grid_x: Grid x coordinate
            grid_y: Grid y coordinate
            grid_diameter: Diameter in grid units
            
        Returns:
            The created Room instance
        """
        if self.is_invalid:
            raise ValueError("Cannot create room in the 'invalid' map")
        from dungeongen.map.room import Room, RoomType
        return self.add_element(Room.from_grid(grid_x, grid_y, grid_diameter, grid_diameter, room_type=RoomType.CIRCULAR))
    
    def recalculate_occupied(self) -> None:
        """Recalculate which grid spaces are occupied by map elements."""
        self.occupancy.clear()
        for idx, element in enumerate(self._elements):
            element.draw_occupied(self.occupancy, idx)    

    def render(self, canvas: skia.Canvas, transform: Optional[skia.Matrix] = None) -> None:
        """Render the map to a canvas.
        
        Args:
            canvas: The Skia canvas to render to
            transform: Optional Skia Matrix transform.
                      If None, calculates a transform to fit the map in the canvas.
        """
        if self.is_invalid:
            raise ValueError("Cannot render the 'invalid' map")          
        # Get canvas dimensions
        canvas_width = canvas.imageInfo().width()
        canvas_height = canvas.imageInfo().height()
        
        # Calculate or use provided transform
        matrix = transform if transform is not None else self.calculate_fit_transform(canvas_width, canvas_height)
        
        # Clear canvas with background color
        background_paint = skia.Paint(
            Color=self.options.crosshatch_background_color
        )
        canvas.drawRect(
            skia.Rect.MakeWH(canvas_width, canvas_height),
            background_paint
        )
        
        # Get all regions and create crosshatch shape
        regions = self._make_regions()
        crosshatch_shapes = []
        for region in regions:
            # Create inflated version of the region's shape
            crosshatch_shapes.append(region.shape.inflated(self.options.crosshatch_border_size))
        
        # Combine all regions into single crosshatch shape
        crosshatch_shape = ShapeGroup.combine(crosshatch_shapes)
        
        # Save canvas state and apply transform
        canvas.save()
        canvas.concat(matrix)
        
        # Draw filled gray background for crosshatch areas
        shading_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self.options.crosshatch_shading_color
        )
        crosshatch_shape.draw(canvas, shading_paint)
        
        # Draw crosshatching pattern using optimized tiled system
        draw_crosshatches_tiled(canvas, crosshatch_shape, self.hatch_tile, self.options)
        
        # Draw room regions
        for region in regions:
            # 1. Save state and apply clip
            canvas.save()
            
            # 2. Clip to region shape
            canvas.clipPath(region.shape.to_path(), skia.ClipOp.kIntersect, True)  # antialiased
            
            # 3. Draw shadows first (no offset, but account for stroke width)
            shadow_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self.options.room_shadow_color,
                StrokeWidth=0
            )
            # Draw shadow shape
            region.shape.draw(canvas, shadow_paint)
            
            # 4. Draw the filled room on top of shadow (with offset)
            room_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self.options.room_color
            )
            canvas.save()
            canvas.translate(
                self.options.room_shadow_offset_x + (self.options.border_width * 0.5),
                self.options.room_shadow_offset_y + (self.options.border_width * 0.5)
            )
            region.shape.draw(canvas, room_paint)
            canvas.restore()

            # 5. Draw region element shadows
            for element in region.elements:
                element.draw(canvas, Layers.SHADOW)

            # 5. Draw grid if enabled (still clipped by mask)
            if self.options.grid_style not in (None, GridStyle.NONE):
                draw_region_grid(canvas, region, self.options)

            # 5.5. Draw water if enabled (clipped by region shape)
            if self.water_layer and self.water_layer.shapes:
                # Translate water to map coordinates (water is generated at 0,0)
                canvas.save()
                canvas.translate(self.bounds.x, self.bounds.y)
                
                # Create custom style from map settings
                water_style = WaterStyle(
                    stroke_width=getattr(self, '_water_stroke_width', 3.0),
                    ripple_width=getattr(self, '_water_stroke_width', 3.0) * 0.5,  # Ripples thinner than shore
                    ripple_insets=(
                        getattr(self, '_water_ripple_inset', 12.0),
                        getattr(self, '_water_ripple_inset', 12.0) * 2
                    )
                )
                
                # Draw using pre-recorded picture for speed
                self.water_layer.draw(canvas, style=water_style)
                
                canvas.restore()

            # 6. Draw region elements props
            for element in region.elements:
                element.draw(canvas, Layers.PROPS)

            # 7. Restore transform and clear clip mask
            canvas.restore()
            
        # Draw region borders with rounded corners
        border_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self.options.border_width,
            Color=self.options.border_color,
            StrokeJoin=skia.Paint.kRound_Join  # Round the corners
        )
        
        # Create a single unified path for all regions
        unified_border = skia.Path()
        for region in regions:
            unified_border.addPath(region.shape.to_path())
            
        # Draw the unified border path
        canvas.drawPath(unified_border, border_paint)

        # Draw doors layer after borders
        for element in self._elements:
            element.draw(canvas, Layers.OVERLAY)

        # Draw text layer (room numbers)
        for element in self._elements:
            element.draw(canvas, Layers.TEXT)

        # Draw element numbers if enabled
        if debug_draw.is_enabled(DebugDrawFlags.ELEMENT_NUMBERS):
            number_paint = skia.Paint(
                Color=skia.Color(0, 0, 0),  # Black text
                AntiAlias=True
            )
            font = skia.Font(skia.Typeface('Arial'), CELL_SIZE/2)
            
            for idx, element in enumerate(self._elements):
                # Get element center
                bounds = element.bounds
                center_x = bounds.x + bounds.width/2
                center_y = bounds.y + bounds.height/2
                
                # Measure text for centering
                text = str(idx)
                text_width = font.measureText(text)
                
                # Draw centered text
                canvas.drawString(
                    text,
                    center_x - text_width/2,  # Center horizontally
                    center_y + font.getSize()/3,  # Approximate vertical centering
                    font,
                    number_paint
                )

        # Restore canvas state
        canvas.restore()

    def render_to_png(self, filename: str, width: int = 1200, height: int = 1200) -> None:
        """Render the map to a PNG file.
        
        Args:
            filename: Output filename (should end in .png)
            width: Image width in pixels (default 1200)
            height: Image height in pixels (default 1200)
        """
        surface = skia.Surface(width, height)
        canvas = surface.getCanvas()
        self.render(canvas)
        image = surface.makeImageSnapshot()
        image.save(filename, skia.kPNG)

    def render_to_svg(self, filename: str, width: int = 1200, height: int = 1200) -> None:
        """Render the map to an SVG file.
        
        Args:
            filename: Output filename (should end in .svg)
            width: Image width in pixels (default 1200)
            height: Image height in pixels (default 1200)
        """
        stream = skia.FILEWStream(filename)
        canvas = skia.SVGCanvas.Make((width, height), stream)
        self.render(canvas)
        del canvas  # Flush and close the SVG
        stream.flush()
