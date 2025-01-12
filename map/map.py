"""Map container class definition."""

import math
import random
from typing import Generic, Iterator, List, Optional, Sequence, Tuple, TypeVar, TYPE_CHECKING

import skia

from algorithms.shapes import Circle, Rectangle, Shape, ShapeGroup
from constants import CELL_SIZE
from graphics.conversions import grid_to_map
from graphics.crosshatch import draw_crosshatches
from map.enums import Layers
from typing import Generic, Iterator, List, Optional, Sequence, Tuple, TypeVar, TYPE_CHECKING
from map.grid import GridStyle, draw_region_grid
from map.mapelement import MapElement
from map.occupancy import OccupancyGrid
from map.region import Region

if TYPE_CHECKING:
    from map._arrange.arrange_utils import RoomDirection
    from map.door import Door, DoorType
    from map.room import Room, RoomType
    from map.passage import Passage
    from map.stairs import Stairs
    from options import Options

REGION_INFLATE = CELL_SIZE * 0.025

TMapElement = TypeVar('T', bound='MapElement')

class Map:
    """Container for all map elements with type-specific access."""
    
    def __init__(self, options: 'Options') -> None:
        self._elements: List[MapElement] = []
        self._options: Options = options
        self._bounds: Rectangle | None = None
        self._bounds_dirty: bool = True
        self._occupancy: OccupancyGrid | None = None
    
    @property
    def elements(self) -> Sequence[MapElement]:
        """Read only access to map elements."""
        return self._elements
    
    @property
    def element_count(self) -> int:
        """Get the number of map elements."""
        return len(self._elements)
    
    @property
    def occupancy(self) -> OccupancyGrid:
        """Get the current occupancy grid."""
        return self._occupancy
    
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

    def add_element(self, element: Generic[TMapElement]) -> TMapElement:
        """Add a map element.
        
        Args:
            element: The map element to add
            
        Returns:
            The added element
            
        Raises:
            ValueError: If the element's bounds exceed reasonable limits
        """
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
            
        element._map = self
        element._options = self._options
        self._elements.append(element)
        self._bounds_dirty = True
        return element
    
    def remove_element(self, element: Generic[TMapElement]) -> TMapElement:
        """Remove a map element."""
        if element in self._elements:
            self._elements.remove(element)
            element._map = None
            self._bounds_dirty = True
    
    @property
    def rooms(self) -> Iterator['Room']:
        """Returns a new iteralble of rooms in the map."""
        return (elem for elem in self._elements if isinstance(elem, Room))
    
    @property
    def doors(self) -> Iterator['Door']:
        """Returns a new iterable of all doors in the map."""
        return (elem for elem in self._elements if isinstance(elem, Door))
    
    @property
    def passages(self) -> Iterator['Passage']:
        """Returns a new iterable of all passages in the map."""
        return (elem for elem in self._elements if isinstance(elem, Passage))
    
    @property
    def stairs(self) -> Iterator['Stairs']:
        """Returns a new iterable all stairs in the map."""
        return (elem for elem in self._elements if isinstance(elem, Stairs))

    def _trace_connected_region(self, 
                              element: MapElement,
                              visited: set[MapElement],
                              region: list[MapElement]) -> None:
        """Recursively trace connected elements that aren't separated by closed doors."""
        from map.door import Door
        
        if element in visited:
            return
        
        visited.add(element)
        region.append(element)
        
        for connection in element.connections:
            # If connection is a closed door, add its side shape but don't traverse
            if isinstance(connection, Door) and not connection.open:
                region.append(connection.get_side_shape(element))
                continue
            self._trace_connected_region(connection, visited, region)
    

    def _recalculate_bounds(self) -> None:
        """Recalculate the bounding rectangle that encompasses all map elements."""
        if not self._elements:
            # Default to single cell at origin if empty
            return Rectangle(0, 0, CELL_SIZE, CELL_SIZE)
        
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

    def recalculate_occupied(self) -> None:
        """Recalculate which grid spaces are occupied by map elements."""
        # Update bounds and create new occupancy grid if needed
        bounds = self.bounds
        grid_width = int(bounds.width / CELL_SIZE) + 1
        grid_height = int(bounds.height / CELL_SIZE) + 1
        
        # Create new grid or clear existing one
        if self._occupancy is None or (self._occupancy.width != grid_width or self._occupancy.height != grid_height):
            self._occupancy = OccupancyGrid(grid_width, grid_height)
        else:
            self._occupancy.clear()
        
        # Mark occupied spaces
        for idx, element in enumerate(self._elements):
            element.draw_occupied(self._occupancy, idx)
    
    def is_occupied(self, x: int, y: int) -> bool:
        """Check if a grid position is occupied by any map element."""
        return self._occupancy.is_occupied(x, y)
    
    def get_element_at(self, x: int, y: int) -> Optional[MapElement]:
        """Get the map element at a grid position.
        
        Args:
            x: Grid x coordinate
            y: Grid y coordinate
            
        Returns:
            The MapElement at that position, or None if unoccupied
        """
        idx = self._occupancy.get_occupant(x, y)
        if idx >= 0:
            return self._elements[idx]
        return None
    
    def _make_regions(self) -> list[Region]:
        """Make shape regions for each contiguous area of the map.
        
        Returns:
            List of Regions, each containing a ShapeGroup and the MapElements in that region.
        """
        
        visited: set[MapElement] = set()
        regions: list[Region] = []
        
        # Find all connected regions
        for element in self._elements:
            if element in visited:
                continue
            
            # Trace this region
            region_elements: list[MapElement] = []
            self._trace_connected_region(element, visited, region_elements)
            
            # Create Region for this area if we found elements
            if region_elements:
                # Get shapes from elements and any door shapes
                shapes = []
                final_elements = []
                for item in region_elements:
                    if isinstance(item, MapElement):
                        shapes.append(item.shape.inflated(REGION_INFLATE))
                        final_elements.append(item)
                    else:  # Rectangle from door side
                        shapes.append(item)
                        
                regions.append(Region(
                    shape=ShapeGroup.combine(shapes),
                    elements=final_elements
                ))
        
        return regions

    def _calculate_default_transform(self, canvas_width: int, canvas_height: int) -> skia.Matrix:
        """Calculate a default transform to fit the map in the canvas.
        
        Returns:
            A Skia Matrix configured to fit the map in the canvas
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
        from map.room import Room, RoomType
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
        from map.room import Room, RoomType
        return self.add_element(Room.from_grid(grid_x, grid_y, grid_diameter, grid_diameter, room_type=RoomType.CIRCULAR))
    
    def create_connected_room(
        self,
        source_room: 'Room',
        direction: 'RoomDirection',
        distance: int,
        room_width: int,
        room_height: int,
        room_type: Optional['RoomType'] = None,
        start_door_type: Optional['DoorType'] = None,
        end_door_type: Optional['DoorType'] = None
    ) -> Tuple['Room', Optional['Door'], 'Passage', Optional['Door']]:
        """Create a new room connected to an existing room via a passage."""
        # Verify source room belongs to this map
        if source_room.map is not self:
            raise ValueError("Source room must belong to this map")
            
        from map._arrange.arrange_rooms import create_connected_room
        return create_connected_room(
            source_room, direction, distance,
            room_width, room_height, room_type,
            start_door_type, end_door_type
        )

    def generate(self, min_rooms: int = 3, max_rooms: int = 5, min_size: int = 4, max_size: int = 7) -> None:
        """Generate a random dungeon map.
        
        Args:
            min_rooms: Minimum number of rooms to generate
            max_rooms: Maximum number of rooms to generate 
            min_size: Minimum room size in grid units
            max_size: Maximum room size in grid units
        """
        # Import here to avoid circular dependencies
        from map._arrange.arrange_rooms import _RoomArranger, GrowDirection
        # from map._props.decorate_room import decorate_room
        from map.room import RoomType
        
        # Get initial room shape
        from map._arrange.room_shapes import get_random_room_shape
        initial_shape = get_random_room_shape()
        print(f"\nInitial room shape selected:")
        print(f"  Type: {initial_shape.room_type}")
        print(f"  Breadth: {initial_shape.breadth}")
        print(f"  Depth: {initial_shape.depth}")
        print(f"  Offset: {initial_shape.breadth_offset}")
        
        # Create starting room at origin using shape's dimensions
        start_room = self.create_rectangular_room(0, 0,
            initial_shape.breadth,  # Use breadth for width
            initial_shape.depth)    # Use depth for height
            
        # Import here to avoid circular dependencies
        from map._arrange.arrange_utils import RoomDirection
        
        # Choose random initial direction
        initial_direction = random.choice([
            RoomDirection.NORTH,
            RoomDirection.SOUTH, 
            RoomDirection.EAST,
            RoomDirection.WEST
        ])
        print(f"  Initial direction: {initial_direction}")
        
        # Create room arranger and generate linear layout
        arranger = _RoomArranger(self, min_size, max_size)
        rooms = arranger.arrange_linear(
            random.randint(min_rooms, max_rooms),
            start_room,
            direction=initial_direction,
            grow_direction=GrowDirection.FORWARD
        )
        
        # Decorate all elements
        # for element in self._elements:
        #     decorate_room(element)
    
    def render(self, canvas: skia.Canvas, transform: Optional[skia.Matrix] = None) -> None:
        """Render the map to a canvas.
        
        Args:
            canvas: The Skia canvas to render to
            transform: Optional Skia Matrix transform.
                      If None, calculates a transform to fit the map in the canvas.
        """
        # Get canvas dimensions
        canvas_width = canvas.imageInfo().width()
        canvas_height = canvas.imageInfo().height()
        
        # Calculate or use provided transform
        matrix = transform if transform is not None else self._calculate_default_transform(canvas_width, canvas_height)
        
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
        
        # Draw crosshatching pattern
        draw_crosshatches(self.options, crosshatch_shape, canvas)
        
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

        # Restore canvas state
        canvas.restore()
