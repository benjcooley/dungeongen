"""Room map element definition."""

import math
from typing import List, TYPE_CHECKING, Tuple, Optional

import random
import skia
import math

from algorithms.math import Point2D
from algorithms.shapes import Rectangle, Circle, Shape
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.enums import Layers
from map.mapelement import MapElement
from map.props.columnarrangement import ColumnArrangement, RowOrientation
from constants import CELL_SIZE

# Constant to make rooms slightly larger to ensure proper passage connections
ROOM_OVERLAP_OFFSET = 4.0  # pixels
# Base corner size as fraction of cell size
CORNER_SIZE = 0.35
# How far corners are inset from room edges
CORNER_INSET = 0.12
# Minimum corner length as percentage of base size
MIN_CORNER_LENGTH = 0.5
# Maximum corner length as percentage of base size 
MAX_CORNER_LENGTH = 2.0
# Control point scale for curve (relative to corner size)
CURVE_CONTROL_SCALE = 0.8  # Increased from 0.5 for more concavity

from map.mapelement import MapElement
from graphics.conversions import grid_to_drawing, grid_to_drawing_size
from map.enums import Layers

if TYPE_CHECKING:
    from map.map import Map
    from options import Options
    from map.props.prop import Prop

class Room(MapElement):
    """A room in the dungeon.
    
    A room is a rectangular area that can connect to other rooms via doors and passages.
    The room's shape matches its bounds exactly.
    """
    
    def __init__(self, x: float, y: float, width: float, height: float, map_: 'Map') -> None:
        # Create slightly larger rectangle to ensure proper passage connections
        shape = Rectangle(
            x - ROOM_OVERLAP_OFFSET/2,
            y - ROOM_OVERLAP_OFFSET/2,
            width + ROOM_OVERLAP_OFFSET,
            height + ROOM_OVERLAP_OFFSET
        )
        super().__init__(shape=shape, map_=map_)
    
    def _draw_corner(self, canvas: skia.Canvas, corner: Point2D, left: Point2D, right: Point2D) -> None:
        """Draw a single corner decoration.
        
        Args:
            canvas: The canvas to draw on
            corner: Corner position
            left: Direction vector parallel to left wall (from corner's perspective)
            right: Direction vector parallel to right wall (from corner's perspective)
        """
        # Calculate base corner size
        base_size = CELL_SIZE * CORNER_SIZE
        
        # Calculate end points with constrained random lengths
        length1 = base_size * (MIN_CORNER_LENGTH + random.random() * (MAX_CORNER_LENGTH - MIN_CORNER_LENGTH))
        length2 = base_size * (MIN_CORNER_LENGTH + random.random() * (MAX_CORNER_LENGTH - MIN_CORNER_LENGTH))
        p1 = corner + left * length1
        p2 = corner + right * length2
        
        # Create and draw the corner path
        path = skia.Path()
        path.moveTo(corner.x, corner.y)
        path.lineTo(p1.x, p1.y)
        
        # Draw curved line between points with smooth inward curve
        # Control points are placed along the straight lines at a fraction of their length
        cp1 = p1 + (corner - p1) * CURVE_CONTROL_SCALE
        cp2 = p2 + (corner - p2) * CURVE_CONTROL_SCALE
        path.cubicTo(cp1.x, cp1.y, cp2.x, cp2.y, p2.x, p2.y)
        
        # Close the path
        path.lineTo(corner.x, corner.y)
        
        # Fill the corner with black
        corner_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=0xFF000000  # Black
        )
        canvas.drawPath(path, corner_paint)

    def draw_corners(self, canvas: skia.Canvas) -> None:
        """Draw corner decorations if this is a rectangular room."""
        if not isinstance(self._shape, Rectangle):
            return
            
        # Calculate corner positions with inset
        inset = CELL_SIZE * CORNER_INSET
        left = self._bounds.x + inset
        right = self._bounds.x + self._bounds.width - inset
        top = self._bounds.y + inset
        bottom = self._bounds.y + self._bounds.height - inset
        
        # Create corner points and wall vectors
        from algorithms.math import Point2D
        
        # Corner positions
        tl = Point2D(left, top)
        tr = Point2D(right, top)
        bl = Point2D(left, bottom)
        br = Point2D(right, bottom)
        
        # Wall direction vectors
        right_vec = Point2D(1, 0)
        down_vec = Point2D(0, 1)
        
        # Draw all four corners with appropriate wall vectors
        self._draw_corner(canvas, tl, right_vec, down_vec)      # Top-left
        self._draw_corner(canvas, tr, -right_vec, down_vec)     # Top-right  
        self._draw_corner(canvas, bl, right_vec, -down_vec)     # Bottom-left
        self._draw_corner(canvas, br, -right_vec, -down_vec)    # Bottom-right

    def create_columns(self, 
                      arrangement: ColumnArrangement,
                      orientation: RowOrientation = RowOrientation.HORIZONTAL,
                      margin: float = 0.5) -> List['Prop']:
        """Create columns in this room according to the specified arrangement pattern.
        
        Args:
            arrangement: Pattern to arrange columns in
            orientation: Orientation for ROWS arrangement (default: HORIZONTAL)
            margin: Margin in grid units from room edges (default: 1.0)
            
        Returns:
            List of created column props
            
        Raises:
            ValueError: If arrangement is invalid for this room type
        """
        from map.props.column import Column, ColumnType
        from map.props.rotation import Rotation
        import math
        
        columns = []
        
        # For circular rooms, only allow CIRCLE arrangement
        if isinstance(self._shape, Circle):
            if arrangement != ColumnArrangement.CIRCLE:
                raise ValueError("Only CIRCLE arrangement supported for circular rooms")
                
            # Calculate radius based on margin
            room_radius = self._shape.radius
            margin_grids = math.floor(margin)  # Convert to integer grid units
            radius = room_radius - ((margin_grids + 1) * CELL_SIZE)  # One grid in from margin
            
            if radius <= CELL_SIZE:  # Ensure we have space for columns
                return columns
            
            # Place 12 columns in a circle
            num_columns = 12
            center = self._shape.bounds.center
            
            for i in range(num_columns):
                angle = (i * 2 * math.pi / num_columns)
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                
                # Create column rotated to face center
                rotation = Rotation.from_radians(angle + math.pi/2)
                column = Column.create_round(0, 0)
                columns.append(column)
                    
            return columns
            
        # For rectangular rooms
        if isinstance(self._shape, Rectangle):
            rect = self._shape #type: Rectangle

            # Get room dimensions in grid units
            grid_width = int(rect.width / CELL_SIZE)
            grid_height = int(rect.height / CELL_SIZE)
            
            # Calculate usable area accounting for margin
            start_x = margin + 1
            start_y = margin + 1
            end_x = grid_width - margin - 1
            end_y = grid_height - margin - 1
            
            if arrangement == ColumnArrangement.GRID:
                # Place columns at each grid intersection within margins
                for x in range(int(start_x), int(end_x + 1)):
                    for y in range(int(start_y), int(end_y + 1)):
                        grid_x = x * CELL_SIZE
                        grid_y = y * CELL_SIZE
                        draw_x, draw_y = grid_to_drawing(grid_x, grid_y, self._options)
                        column = Column.create_square(draw_x + rect.x, draw_y + rect.y)
                        self.add_prop(column)
                        columns.append(column)
                            
            elif arrangement == ColumnArrangement.RECTANGLE:
                # Place columns around perimeter
                # Top and bottom rows
                for x in range(int(start_x), int(end_x + 1)):
                    for y in (int(start_y), int(end_y)):
                        grid_x = x * CELL_SIZE
                        grid_y = y * CELL_SIZE
                        draw_x, draw_y = grid_to_drawing(grid_x, grid_y, self._options)
                        column = Column.create_square(draw_x + rect.x, draw_y + rect.y)
                        columns.append(column)
                
                # Left and right columns (excluding corners)
                for y in range(int(start_y + 1), int(end_y)):
                    for x in (start_x, end_x):
                        grid_x = x * CELL_SIZE
                        grid_y = y * CELL_SIZE
                        draw_x, draw_y = grid_to_drawing(grid_x, grid_y, self._options)
                        column = Column.create_square(draw_x + rect.x, draw_y + rect.y)
                        columns.append(column)
                            
            elif arrangement == ColumnArrangement.ROWS:
                # Place columns in parallel rows
                if orientation == RowOrientation.HORIZONTAL:
                    # Debug room dimensions
                    print(f"Room bounds: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")
                    print(f"Grid dimensions: width={grid_width}, height={grid_height}")
                    print(f"Start coords: ({start_x}, {start_y}), End coords: ({end_x}, {end_y})")
                    
                    # Calculate total available dimensions
                    available_width = end_x - start_x
                    available_height = end_y - start_y
                    margin_grids = math.floor(margin)  # Convert to integer grid units
                    print(f"Available width: {available_width}, height: {available_height}, margin: {margin_grids}")
                    
                    # Need enough space for columns plus margins
                    min_space = margin_grids + 2  # margin + 2 spaces for columns
                    if available_height < min_space:
                        print(f"Not enough vertical space: {available_height} < {min_space}")
                        return columns
                        
                    # Calculate row positions with margins
                    row1 = start_y + margin_grids  # Remove +1 to use full available space
                    row2 = end_y - margin_grids
                    
                    # Verify minimum separation
                    if row2 - row1 < 2:
                        return columns
                    
                    # Place columns along each row
                    for x in range(int(start_x), int(end_x + 1)):
                        for y in (row1, row2):
                            grid_x = x * CELL_SIZE
                            grid_y = y * CELL_SIZE
                            draw_x, draw_y = grid_to_drawing(grid_x, grid_y, self._options)
                            column = Column.create_square(draw_x + rect.x, draw_y + rect.y)
                            self.add_prop(column)
                            columns.append(column)
                else:  # VERTICAL
                    # Calculate total available width
                    available_width = end_x - start_x
                    margin_grids = math.floor(margin)  # Convert to integer grid units
                    
                    # Need enough space for columns plus margins
                    min_space = (2 * margin_grids) + 3  # 2 margins + 3 spaces (2 for separation + 1 for columns)
                    if available_width < min_space:
                        return columns
                        
                    # Calculate column positions with margins
                    spacing = (available_width - 2*margin_grids) / 3  # Divide available space into thirds
                    col1 = start_x + spacing  # First third
                    col2 = end_x - spacing    # Last third
                    
                    print(f"Column positions: {col1}, {col2}")
                    
                    # Place columns along each column
                    for y in range(int(start_y), int(end_y + 1)):
                        for x in (col1, col2):
                            grid_x = x * CELL_SIZE
                            grid_y = y * CELL_SIZE
                            draw_x, draw_y = grid_to_drawing(grid_x, grid_y, self._options)
                            column = Column.create_square(draw_x + rect.x, draw_y + rect.y)
                            self.add_prop(column)
                            columns.append(column)
                                
            return columns
            
        raise ValueError(f"Unsupported room shape for column arrangement: {type(self._shape)}")

    def draw(self, canvas: 'skia.Canvas', layer: Layers = Layers.PROPS) -> None:
        """Draw the room and its props."""
        if layer == Layers.PROPS:
            self.draw_corners(canvas)
        super().draw(canvas, layer)
