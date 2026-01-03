"""Exit map element definition - dungeon entrance/exit.

An Exit is essentially a one-sided closed door. It has:
1. Floor chip shapes for all four directions (like Door), but only one is ever used
2. A skewed inverted U archway drawn on the overlay layer
"""

from enum import Enum, auto
import skia
from dungeongen.graphics.shapes import Rectangle, ShapeGroup
from dungeongen.map.mapelement import MapElement
from dungeongen.graphics.shapes import Shape
from dungeongen.graphics.conversions import grid_to_map
from dungeongen.map.enums import Layers, RoomDirection
from dungeongen.constants import CELL_SIZE
from typing import TYPE_CHECKING
from dungeongen.map.occupancy import ElementType

if TYPE_CHECKING:
    from dungeongen.map.occupancy import OccupancyGrid
    from dungeongen.map.map import Map
    from dungeongen.options import Options

# Use same constants as Door for the chip
EXIT_SIDE_ROUNDING = 8.0
EXIT_SIDE_EXTENSION = EXIT_SIDE_ROUNDING

# Isometric skew angle (degrees) - gives 3D perspective effect
EXIT_SKEW_ANGLE = 12.0  # About 12 degrees of skew
import math

# Cave door shape parameters
SHOULDER_FRAC = 0.55   # Where vertical walls meet the arch (as fraction of height)
KX_FRAC = 0.28         # Bezier handle X length (as fraction of width)
KY_FRAC = 0.85         # Bezier handle Y length (as fraction of arch height)


class Exit(MapElement):
    """An exit/entrance to the dungeon.
    
    Works like a one-sided closed door:
    - Has floor chips for all four directions (like Door's _left/_right/_top/_bottom_group)
    - Only one chip is ever used (the one connecting to the dungeon interior)
    - get_side_shape() uses same position-based logic as Door to return the correct chip
    - Draws a skewed inverted U archway extending away from the dungeon
    """
    
    def __init__(self, x: float, y: float, direction: RoomDirection) -> None:
        """Initialize an exit with position and direction.
        
        Args:
            x: X coordinate in map units
            y: Y coordinate in map units
            direction: Direction the exit leads OUT (away from dungeon)
        """
        if abs(x) > 4200 or abs(y) > 4200:
            raise ValueError(f"Exit position ({x}, {y}) exceeds reasonable limits (±4200)")
        
        self._x = x
        self._y = y
        self._width = self._height = CELL_SIZE
        self._direction = direction
        
        # Create ALL floor chips - exactly like Door's side groups
        # Even though only one will ever be used (the one opposite the exit direction)
        self._create_all_chips()
        
        # Exit's base shape is empty (like closed door) - chip is added via get_side_shape
        shape = ShapeGroup(includes=[], excludes=[])
        super().__init__(shape)
    
    def _create_all_chips(self) -> None:
        """Create all four floor chip shapes - identical to Door's side group geometry.
        
        Creates _left_group, _right_group, _top_group, _bottom_group just like Door.
        Only one of these will ever be used based on which direction the exit faces.
        """
        # Horizontal chips (left and right)
        side_width = self._width / 3
        middle_height = self._height * 0.6
        middle_y = self._y + (self._height - middle_height) / 2
        
        # Left chip (like Door's _left_group)
        left_side = Rectangle(
            self._x - EXIT_SIDE_EXTENSION + EXIT_SIDE_ROUNDING,
            self._y + EXIT_SIDE_ROUNDING,
            side_width + EXIT_SIDE_EXTENSION - (EXIT_SIDE_ROUNDING * 2),
            self._height - (EXIT_SIDE_ROUNDING * 2),
            inflate=EXIT_SIDE_ROUNDING
        )
        left_middle = Rectangle(
            self._x + side_width,
            middle_y,
            side_width / 2,
            middle_height
        )
        self._left_group = ShapeGroup(includes=[left_side, left_middle], excludes=[])
        
        # Right chip (like Door's _right_group)
        right_side = Rectangle(
            self._x + self._width - side_width + EXIT_SIDE_ROUNDING,
            self._y + EXIT_SIDE_ROUNDING,
            side_width + EXIT_SIDE_EXTENSION - (EXIT_SIDE_ROUNDING * 2),
            self._height - (EXIT_SIDE_ROUNDING * 2),
            inflate=EXIT_SIDE_ROUNDING
        )
        right_middle = Rectangle(
            self._x + side_width + side_width / 2,
            middle_y,
            side_width / 2,
            middle_height
        )
        self._right_group = ShapeGroup(includes=[right_side, right_middle], excludes=[])
        
        # Vertical chips (top and bottom)
        side_height = self._height / 3
        middle_width = self._width * 0.6
        middle_x = self._x + (self._width - middle_width) / 2
        
        # Top chip (like Door's _top_group)
        top_side = Rectangle(
            self._x + EXIT_SIDE_ROUNDING,
            self._y - EXIT_SIDE_EXTENSION + EXIT_SIDE_ROUNDING,
            self._width - (EXIT_SIDE_ROUNDING * 2),
            side_height + EXIT_SIDE_EXTENSION - (EXIT_SIDE_ROUNDING * 2),
            inflate=EXIT_SIDE_ROUNDING
        )
        top_middle = Rectangle(
            middle_x,
            self._y + side_height,
            middle_width,
            side_height / 2
        )
        self._top_group = ShapeGroup(includes=[top_side, top_middle], excludes=[])
        
        # Bottom chip (like Door's _bottom_group)
        bottom_side = Rectangle(
            self._x + EXIT_SIDE_ROUNDING,
            self._y + self._height - side_height + EXIT_SIDE_ROUNDING,
            self._width - (EXIT_SIDE_ROUNDING * 2),
            side_height + EXIT_SIDE_EXTENSION - (EXIT_SIDE_ROUNDING * 2),
            inflate=EXIT_SIDE_ROUNDING
        )
        bottom_middle = Rectangle(
            middle_x,
            self._y + side_height + side_height / 2,
            middle_width,
            side_height / 2
        )
        self._bottom_group = ShapeGroup(includes=[bottom_side, bottom_middle], excludes=[])
    
    def get_side_shape(self, connected: 'MapElement') -> ShapeGroup:
        """Get the chip shape for the side connecting to the given element.
        
        Uses same position-based logic as Door - returns the chip on the side
        where the connected element is located.
        """
        # Get center point of connected element
        conn_bounds = connected.bounds
        conn_cx = conn_bounds.x + conn_bounds.width / 2
        conn_cy = conn_bounds.y + conn_bounds.height / 2
        
        # Get exit center
        exit_cx = self._x + self._width / 2
        exit_cy = self._y + self._height / 2
        
        # Determine which chip to return based on where connected element is
        # For horizontal exits (EAST/WEST), connected element is left or right
        # For vertical exits (NORTH/SOUTH), connected element is above or below
        if self._direction in (RoomDirection.EAST, RoomDirection.WEST):
            return self._left_group if conn_cx < exit_cx else self._right_group
        else:
            return self._top_group if conn_cy < exit_cy else self._bottom_group
    
    @property
    def direction(self) -> RoomDirection:
        """Direction the exit leads (away from dungeon)."""
        return self._direction
    
    def draw(self, canvas: skia.Canvas, layer: 'Layers' = Layers.PROPS) -> None:
        """Draw the exit's cave door archway on the overlay layer."""
        if layer != Layers.OVERLAY:
            return
        
        # Paint for the archway - solid black fill
        paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=skia.Color(0, 0, 0)
        )
        
        # Archway dimensions
        arch_width = self._width * 0.58   # Wider arch
        arch_height = self._height * 0.42
        
        # Center of the cell
        cx = self._x + self._width / 2
        cy = self._y + self._height / 2
        
        # Create canonical door path (base at origin, pointing up in -Y)
        path = self._create_canonical_door_path(arch_width, arch_height)
        
        # Build transform: skew, rotate for direction, translate to position
        m = skia.Matrix()
        
        # 1. Apply skew (about origin, which is the base)
        # Flip skew direction for SOUTH and WEST to maintain consistent isometric look
        theta = math.radians(EXIT_SKEW_ANGLE)
        if self._direction in (RoomDirection.SOUTH, RoomDirection.WEST):
            k = -math.tan(theta)  # Flip skew for these directions
        else:
            k = math.tan(theta)   # Normal skew for NORTH and EAST
        m.postSkew(k, 0)
        
        # 2. Rotate based on direction
        if self._direction == RoomDirection.SOUTH:
            m.postRotate(180)
        elif self._direction == RoomDirection.WEST:
            m.postRotate(-90)  # Point left
        elif self._direction == RoomDirection.EAST:
            m.postRotate(90)   # Point right
        # NORTH needs no rotation (already pointing up)
        
        # 3. Translate to cell center
        m.postTranslate(cx, cy)
        
        path.transform(m)
        canvas.drawPath(path, paint)
    
    def _create_canonical_door_path(self, w: float, h: float) -> skia.Path:
        """Create a canonical cave door (∩) path centered at origin, pointing up (-Y).
        
        The door base is centered at (0, 0) and extends upward (negative Y).
        Use transforms to rotate/translate for different directions.
        
        Args:
            w: Width of the door
            h: Height of the door
            
        Returns:
            skia.Path with base at origin, arch extending in -Y direction
        """
        left = -w / 2
        right = w / 2
        mid = 0
        base_y = 0
        
        shoulder_y = -h * SHOULDER_FRAC
        apex_y = -h
        
        # Bezier handle lengths
        kx = w * KX_FRAC
        ky = abs(shoulder_y - apex_y) * KY_FRAC
        
        path = skia.Path()
        path.moveTo(left, base_y)
        path.lineTo(right, base_y)
        path.lineTo(right, shoulder_y)
        
        # Right shoulder -> apex (cubic)
        path.cubicTo(
            right, shoulder_y - ky,      # control 1
            mid + kx, apex_y,            # control 2
            mid, apex_y                  # end at apex
        )
        
        # Apex -> left shoulder (cubic)
        path.cubicTo(
            mid - kx, apex_y,            # control 1
            left, shoulder_y - ky,       # control 2
            left, shoulder_y             # end at left shoulder
        )
        
        path.close()
        return path
    
    
    @classmethod
    def from_grid(cls, grid_x: float, grid_y: float, direction: RoomDirection) -> 'Exit':
        """Create an exit using grid coordinates.
        
        Args:
            grid_x: X coordinate in grid units
            grid_y: Y coordinate in grid units
            direction: Direction the exit leads (away from dungeon)
            
        Returns:
            A new Exit instance
        """
        x, y = grid_to_map(grid_x, grid_y)
        return cls(x, y, direction)
    
    def draw_occupied(self, grid: 'OccupancyGrid', element_idx: int) -> None:
        """Draw this element's shape and blocked areas into the occupancy grid."""
        grid_x = int(self._x / CELL_SIZE)
        grid_y = int(self._y / CELL_SIZE)
        grid.mark_cell(grid_x, grid_y, ElementType.DOOR, element_idx)
