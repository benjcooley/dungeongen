"""Dias (raised platform) prop implementation."""

from typing import TYPE_CHECKING
import skia
import math

from dungeongen.graphics.shapes import Rectangle
from dungeongen.graphics.aliases import Point
from dungeongen.constants import CELL_SIZE
from dungeongen.map._props.prop import Prop, PropType
from dungeongen.map.enums import Layers
from dungeongen.graphics.rotation import Rotation

# Dias is 3 tiles wide (radius = 1.5 tiles)
DIAS_RADIUS = CELL_SIZE * 1.5

# Boundary shape centered at origin (where flat edge midpoint is)
# The half-circle extends DIAS_RADIUS in the +Y direction from origin
DIAS_PROP_TYPE = PropType(
    is_wall_aligned=True,
    is_grid_aligned=True,
    boundary_shape=Rectangle(-DIAS_RADIUS, -DIAS_RADIUS, DIAS_RADIUS * 2, DIAS_RADIUS * 2),
    grid_size=(3, 2)
)

class Dias(Prop):
    """A raised platform prop - two concentric half-circles.
    
    Grid-aligned prop: 3 tiles wide x 2 tiles tall (at ROT_0).
    
    Drawing:
    - At ROT_0: flat edge at top, curve opens downward (+Y)
    - Rotation applies around grid_bounds center
    
    Position:
    - `position` is the TOP-LEFT of grid_bounds (see Prop.__init__ for details)
    - To center the dias at a specific point (e.g., wall center), use:
        position = (center_x - grid_width/2, center_y - grid_height/2)
    
    Wall Placement Helper (classmethod):
    - Use Dias.on_wall(wall_direction, wall_center_x, wall_center_y) for easier placement
    
    Rotation Guide:
    - NORTH wall (curve opens down into room): ROT_0
    - SOUTH wall (curve opens up into room): ROT_180  
    - EAST wall (curve opens left into room): ROT_90
    - WEST wall (curve opens right into room): ROT_270
    """
    
    def __init__(self, position: Point, rotation: Rotation = Rotation.ROT_0) -> None:
        """Create a dias at the specified position.
        
        Args:
            position: TOP-LEFT corner of grid bounds (not center!)
            rotation: Rotation to apply
        """
        super().__init__(
            DIAS_PROP_TYPE,
            position,
            rotation=rotation
        )
    
    def _draw_content(self, canvas: skia.Canvas, bounds: Rectangle, layer: Layers = Layers.PROPS) -> None:
        if layer != Layers.PROPS:
            return
            
        options = self._map.options if self._map else None
        
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=options.prop_fill_color if options else 0xFFFFFFFF
        )
        
        outline_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=options.prop_stroke_width if options else 2.0,
            Color=options.prop_outline_color if options else 0xFF000000
        )

        outer_radius = DIAS_RADIUS
        inner_radius = DIAS_RADIUS * 0.75
        
        # The drawing happens centered in grid_bounds.
        # Grid center is always 1 tile (CELL_SIZE) from the wall edge.
        # We want flat edge at the wall, so offset by 1 tile toward local -Y.
        # This works for all rotations because:
        # - ROT_0/180: local -Y points toward wall (N) or away (S, but flipped by rotation)
        # - ROT_90/270: local -Y maps to world X toward/away from wall after rotation
        offset_y = -CELL_SIZE  # Always 1 tile offset to position flat edge at wall
        
        outer_rect = skia.Rect.MakeLTRB(-outer_radius, -outer_radius + offset_y, 
                                         outer_radius, outer_radius + offset_y)
        inner_rect = skia.Rect.MakeLTRB(-inner_radius, -inner_radius + offset_y,
                                         inner_radius, inner_radius + offset_y)
        
        # Draw the bottom half (0° to 180°, where 0° is at 3 o'clock)
        # This creates a half-circle with flat edge at top of rect
        # useCenter=False draws just the arc, not pie-slice lines to center
        canvas.drawArc(outer_rect, 0, 180, False, fill_paint)
        canvas.drawArc(outer_rect, 0, 180, False, outline_paint)
        canvas.drawArc(inner_rect, 0, 180, False, outline_paint)

    @property
    def placement_point(self) -> tuple[float, float]:
        """Get the wall center point where this dias is placed.
        
        This is the position to use when placing wall-aligned props (like altars)
        on the dias. The prop's own wall-alignment behavior will handle the rest.
        
        Returns:
            Tuple of (x, y) - the center point on the wall where the dias is located
        """
        gb = self._grid_bounds
        center_x = gb.x + gb.width / 2
        center_y = gb.y + gb.height / 2
        
        # Return the wall center point (where the flat edge is)
        if self._rotation == Rotation.ROT_0:  # North wall
            return (center_x, gb.y)
        elif self._rotation == Rotation.ROT_180:  # South wall
            return (center_x, gb.y + gb.height)
        elif self._rotation == Rotation.ROT_90:  # East wall
            return (gb.x + gb.width, center_y)
        else:  # ROT_270 - West wall
            return (gb.x, center_y)
    
    @classmethod
    def create(cls, rotation: Rotation = Rotation.ROT_0) -> 'Dias':
        """Create a dias prop at origin with optional rotation."""
        return cls((0, 0), rotation=rotation)
    
    @classmethod
    def on_wall(cls, wall: str, center_x: float, center_y: float) -> 'Dias':
        """Create a dias centered on a wall.
        
        This helper calculates the correct position offset so the dias
        is visually centered at (center_x, center_y) on the specified wall.
        
        Args:
            wall: One of 'north', 'south', 'east', 'west'
            center_x: X coordinate of wall center point
            center_y: Y coordinate of wall center point
            
        Returns:
            A Dias positioned and rotated correctly for that wall.
            
        Example:
            # Place dias centered on north wall
            dias = Dias.on_wall('north', room.bounds.center_x, room.bounds.top)
        """
        grid_w_cells, grid_h_cells = DIAS_PROP_TYPE.grid_size  # (3, 2)
        grid_w = grid_w_cells * CELL_SIZE  # 192
        grid_h = grid_h_cells * CELL_SIZE  # 128
        
        if wall == 'north':
            # Flat edge at wall, curve extends down into room
            # Grid bounds: top-left at (center_x - w/2, wall_y)
            pos = (center_x - grid_w / 2, center_y)
            rotation = Rotation.ROT_0
        elif wall == 'south':
            # Flat edge at wall, curve extends up into room
            # Grid bounds: top-left at (center_x - w/2, wall_y - h)
            pos = (center_x - grid_w / 2, center_y - grid_h)
            rotation = Rotation.ROT_180
        elif wall == 'east':
            # Flat edge at wall, curve extends left into room
            # After 90° rotation, grid is h x w (128 x 192)
            pos = (center_x - grid_h, center_y - grid_w / 2)
            rotation = Rotation.ROT_90
        elif wall == 'west':
            # Flat edge at wall, curve extends right into room
            # After 270° rotation, grid is h x w (128 x 192)
            pos = (center_x, center_y - grid_w / 2)
            rotation = Rotation.ROT_270
        else:
            raise ValueError(f"wall must be 'north', 'south', 'east', or 'west', got '{wall}'")
        
        return cls(pos, rotation=rotation)
