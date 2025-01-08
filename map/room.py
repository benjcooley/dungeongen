"""Room map element definition."""

import math
from typing import List, TYPE_CHECKING, Tuple, Optional

import random
import skia

from map.props.column import Column, ColumnType

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
                      margin: float = 0,
                      column_type: ColumnType = ColumnType.ROUND) -> List['Prop']:
        """Create columns in this room according to the specified arrangement pattern.
        
        Args:
            arrangement: Pattern to arrange columns in
            orientation: Orientation for ROWS arrangement (default: HORIZONTAL)
            margin: Optional margin in grid units from room edges (default: 0)
            
        Returns:
            List of created column props
            
        Raises:
            ValueError: If arrangement is invalid for this room type
        """
        columns = []
        column_angles = None
        
        # For circular rooms, only allow CIRCLE arrangement
        if isinstance(self._shape, Circle):
            if arrangement != ColumnArrangement.CIRCLE:
                raise ValueError("Only CIRCLE arrangement supported for circular rooms")
                
            circle = self._shape  # type: Circle
            # Place columns away from wall based on margin
            radius = circle.radius - ((margin + 1) * CELL_SIZE)
            center = circle.bounds.center
            
            # Use 8 columns for now
            num_columns = 8
            column_angles = []
            for i in range(num_columns):
                angle = (i * 2 * math.pi / num_columns)
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                
                if column_type == ColumnType.SQUARE:
                    # For square columns, angle them to face center
                    # Add pi/2 to make the flat face point toward center
                    column = Column.create_square(x, y, angle + math.pi/2)
                else:
                    column = Column.create_round(x, y)
                    
                columns.append(column)
                column_angles.append(angle)
                    
            # Add all columns at once
            for column in columns:
                self.add_prop(column)
            return columns
            
        # For rectangular rooms
        if isinstance(self._shape, Rectangle):
            rect = self._shape #type: Rectangle

            # Get room dimensions in grid units
            grid_width = int(rect.width / CELL_SIZE)
            grid_height = int(rect.height / CELL_SIZE)
            
            # Calculate valid column placement rectangle
            left = 1 + margin
            right = grid_width - (1 + margin)
            top = 1 + margin
            bottom = grid_height - (1 + margin)
            
            # Calculate all positions in grid coordinates first
            grid_positions = []  # List of (x,y) grid coordinates
            
            if arrangement == ColumnArrangement.GRID:
                # Place columns in a grid pattern with 2-unit spacing
                for x in range(int(left), int(right) + 1):
                    for y in range(int(top), int(bottom) + 1):
                        grid_positions.append((x, y))
                            
            elif arrangement == ColumnArrangement.RECTANGLE:
                # Place columns around perimeter
                # Top and bottom rows
                for x in range(int(left), int(right) + 1):
                    grid_positions.append((x, int(top)))  # Top row
                    grid_positions.append((x, int(bottom)))  # Bottom row
                
                # Left and right columns (excluding corners)
                for y in range(int(top) + 1, int(bottom)):
                    grid_positions.append((int(left), y))  # Left column
                    grid_positions.append((int(right), y))  # Right column
                            
            elif arrangement == ColumnArrangement.ROWS:
                if orientation == RowOrientation.HORIZONTAL:
                    if bottom - top < 2:  # Not enough vertical space for two rows
                        return columns
                    # Place columns in two horizontal rows
                    for x in range(int(left), int(right) + 1):
                        grid_positions.append((x, int(top)))      # Top row
                        grid_positions.append((x, int(bottom)))   # Bottom row
                else:  # VERTICAL 
                    if right - left < 2:  # Not enough horizontal space for two columns
                        return columns
                    # Place columns in two vertical rows
                    for y in range(int(top), int(bottom) + 1):
                        grid_positions.append((int(left), y))     # Left column
                        grid_positions.append((int(right), y))    # Right column

            # Convert grid positions to map space and create columns
            for grid_x, grid_y in grid_positions:
                map_x = rect.left + (grid_x * CELL_SIZE)
                map_y = rect.top + (grid_y * CELL_SIZE)
                column = Column.create_square(map_x, map_y)
                columns.append(column)
                                
            # Add all columns at once
            for column in columns:
                self.add_prop(column)
            return columns
            
        raise ValueError(f"Unsupported room shape for column arrangement: {type(self._shape)}")

    def draw(self, canvas: 'skia.Canvas', layer: Layers = Layers.PROPS) -> None:
        """Draw the room and its props."""
        if layer == Layers.PROPS:
            self.draw_corners(canvas)
        super().draw(canvas, layer)
