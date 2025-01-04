"""Map container class definition."""

from typing import List, Iterator, Optional, TYPE_CHECKING

import skia
import math
from graphics.crosshatch import draw_crosshatches
from map.grid import GridStyle
if TYPE_CHECKING:
    from options import Options
from map.occupancy import OccupancyGrid
from algorithms.shapes import ShapeGroup, Rectangle, Circle
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.mapelement import MapElement
from map.room import Room
from map.door import Door
from map.passage import Passage

class Map:
    """Container for all map elements with type-specific access."""
    
    def __init__(self, options: 'Options') -> None:
        self._elements: List[MapElement] = []
        self.options = options
        self._bounds: Rectangle | None = None
        self._bounds_dirty: bool = True
        self._occupancy: OccupancyGrid | None = None
    
    def add_element(self, element: MapElement) -> None:
        """Add a map element."""
        self._elements.append(element)
        self._bounds_dirty = True
    
    def remove_element(self, element: MapElement) -> None:
        """Remove a map element."""
        if element in self._elements:
            self._elements.remove(element)
            self._bounds_dirty = True
    
    @property
    def rooms(self) -> Iterator[Room]:
        """Get all rooms in the map."""
        return (elem for elem in self._elements if isinstance(elem, Room))
    
    @property
    def doors(self) -> Iterator[Door]:
        """Get all doors in the map."""
        return (elem for elem in self._elements if isinstance(elem, Door))
    
    @property
    def passages(self) -> Iterator[Passage]:
        """Get all passages in the map."""
        return (elem for elem in self._elements if isinstance(elem, Passage))
    
    def _trace_connected_region(self, 
                              element: MapElement,
                              visited: set[MapElement],
                              region: list[MapElement]) -> None:
        """Recursively trace connected elements that aren't separated by closed doors."""
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
    
    @property
    def bounds(self) -> Rectangle:
        """Get the current bounding rectangle, recalculating if needed."""
        if self._bounds_dirty or self._bounds is None:
            self._recalculate_bounds()
        return self._bounds

    def _recalculate_bounds(self) -> None:
        """Recalculate the bounding rectangle that encompasses all map elements."""
        if not self._elements:
            # Default to single cell at origin if empty
            return Rectangle(0, 0, self.options.cell_size, self.options.cell_size)
        
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
        grid_width = int(bounds.width / self.options.cell_size) + 1
        grid_height = int(bounds.height / self.options.cell_size) + 1
        
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

    def create_rectangular_room(self, grid_x: float, grid_y: float, grid_width: float, grid_height: float) -> Room:
        """Create a rectangular room using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            grid_width: Width in grid units
            grid_height: Height in grid units
            
        Returns:
            A new rectangular Room instance
        """
        x, y = grid_to_drawing(grid_x, grid_y, self.options)
        width, height = grid_to_drawing_size(grid_width, grid_height, self.options)
        room = Room(x, y, width, height, self)
        self.add_element(room)
        return room
    
    def create_circular_room(self, grid_cx: float, grid_cy: float, grid_radius: float) -> Room:
        """Create a circular room using grid coordinates.
        
        Args:
            grid_cx: Center X coordinate in grid units
            grid_cy: Center Y coordinate in grid units
            grid_radius: Radius in grid units
            
        Returns:
            A new Room instance with a circular shape
        """
        cx, cy = grid_to_drawing(grid_cx, grid_cy, self.options)
        radius, _ = grid_to_drawing_size(grid_radius, 0, self.options)
        
        # Create a Room with a Circle shape
        room = Room.__new__(Room)  # Create instance without calling __init__
        shape = Circle(cx, cy, radius)
        MapElement.__init__(room, shape=shape, map_=self)
        self.add_element(room)
        return room
    
    def get_regions(self) -> list[ShapeGroup]:
        """Get ShapeGroups for each contiguous region of the map.
        
        Returns:
            List of ShapeGroups, each representing a contiguous region not separated
            by closed doors.
        """
        visited: set[MapElement] = set()
        regions: list[ShapeGroup] = []
        
        # Find all connected regions
        for element in self._elements:
            if element in visited:
                continue
            
            # Trace this region
            region: list[MapElement] = []
            self._trace_connected_region(element, visited, region)
            
            # Create ShapeGroup for this region
            if region:
                # Get shapes from elements and any door shapes
                shapes = []
                for item in region:
                    if isinstance(item, MapElement):
                        shapes.append(item.shape)
                    else:  # Rectangle from door side
                        shapes.append(item)
                regions.append(ShapeGroup.combine(shapes))
        
        return regions

    def _calculate_default_transform(self, canvas_width: int, canvas_height: int) -> skia.Matrix:
        """Calculate a default transform to fit the map in the canvas.
        
        Returns:
            A Skia Matrix configured to fit the map in the canvas
        """
        bounds = self.bounds
        
        # Calculate scale to fit in canvas with padding
        padding = 20  # pixels of padding around the map
        scale_x = (canvas_width - 2 * padding) / bounds.width
        scale_y = (canvas_height - 2 * padding) / bounds.height
        scale = min(scale_x, scale_y)
        
        # Calculate translation to center the map
        translate_x = (canvas_width - bounds.width * scale) / 2 - bounds.x * scale
        translate_y = (canvas_height - bounds.height * scale) / 2 - bounds.y * scale
        
        # Create transform matrix
        matrix = skia.Matrix()
        matrix.setScale(scale, scale)
        matrix.postTranslate(translate_x, translate_y)
        return matrix

    def _draw_region_grid(self, canvas: skia.Canvas, region: ShapeGroup) -> None:
        """Draw grid dots for a region.
        
        Args:
            canvas: The canvas to draw on
            region: The region to draw grid for
        """
        # Create grid paint
        grid_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self.options.grid_color
        )
        
        # Calculate grid bounds in cells
        bounds = region.recalculate_bounds()
        start_x = math.floor(bounds.x / self.options.cell_size)
        start_y = math.floor(bounds.y / self.options.cell_size)
        end_x = math.ceil((bounds.x + bounds.width) / self.options.cell_size)
        end_y = math.ceil((bounds.y + bounds.height) / self.options.cell_size)
        
        # Draw grid dots
        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                # Convert to drawing coordinates
                px = x * self.options.cell_size
                py = y * self.options.cell_size
                
                # Check if point is within region
                if region.contains(px, py):
                    # Draw dot at grid intersection
                    canvas.drawCircle(
                        px, py,
                        self.options.grid_dot_size,
                        grid_paint
                    )

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
        regions = self.get_regions()
        crosshatch_shapes = []
        for region in regions:
            # Create inflated version of included shapes
            inflated_includes = [shape.inflated(self.options.crosshatch_inflation) 
                               for shape in region.includes]
            # Excluded shapes are not inflated
            crosshatch_shapes.append(ShapeGroup(
                includes=inflated_includes,
                excludes=region.excludes
            ))
        
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
        
        # Draw room regions with shadows
        for region in regions:
            # Create shadow paint
            shadow_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self.options.room_shadow_color
            )
            
            # Draw shadow shape
            region.draw(canvas, shadow_paint)
            
            # Create room paint
            room_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                Color=self.options.room_color
            )
            
            # Create mask using region shape
            mask_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
                BlendMode=skia.BlendMode.kSrc
            )
            
            # Save canvas state for clipping
            canvas.save()
            
            # Create clipping mask using region shape
            canvas.translate(0, 0)  # Reset translation
            region.draw(canvas, mask_paint)
            
            # Draw room shape with offset, clipped by mask
            canvas.translate(
                -self.options.room_shadow_offset_x,
                -self.options.room_shadow_offset_y
            )
            region.draw(canvas, room_paint)
            
            # Draw grid if enabled
            if self.options.grid_style not in (None, GridStyle.NONE):
                self._draw_region_grid(canvas, region)
            
            # Restore canvas state
            canvas.restore()
            
        # Draw element details after all regions are drawn
        for element in self._elements:
            if any(element.shape in region_shape.includes for region_shape in regions):
                element.draw(canvas)
        
        # Create paint for map elements
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=1.0,
            Color=skia.ColorBLACK
        )
        
        # Draw region borders last with rounded corners
        border_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self.options.border_width,
            Color=self.options.border_color,
            StrokeJoin=skia.Paint.kRound_Join  # Round the corners
        )
        for region in regions:
            region.draw(canvas, border_paint)

        # Restore canvas state
        canvas.restore()
