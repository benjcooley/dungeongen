import math
import random
from typing import List, TYPE_CHECKING

import skia

from algorithms.shapes import Circle, Rectangle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from graphics.conversions import grid_to_drawing
from map.enums import Layers, RockType
from map.mapelement import MapElement
from map.props.prop import Prop
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map

# Rock size ranges as fraction of grid cell
SMALL_ROCK_MIN_SIZE = 1/16
SMALL_ROCK_MAX_SIZE = 1/10
MEDIUM_ROCK_MIN_SIZE = 1/10 
MEDIUM_ROCK_MAX_SIZE = 1/6

class Rock(Prop):
    """A rock prop with irregular circular shape."""
    
    @classmethod
    def is_decoration(cls) -> bool:
        """Rocks are decorative floor items."""
        return True
        
    @classmethod
    def is_grid_aligned(cls) -> bool:
        """Whether this prop should be aligned to the grid."""
        return False
        
    @classmethod
    def is_wall_aligned(cls) -> bool:
        """Whether this prop should be aligned to room walls."""
        return False
        
    @classmethod
    def prop_size(cls) -> 'Point':
        """Get the nominal size of this rock in drawing units."""
        size = MEDIUM_ROCK_MAX_SIZE * 2 * CELL_SIZE  # Use maximum medium rock size as standard
        return (size, size)  # Rocks are circular, so width = height
        
    @classmethod
    def prop_grid_size(cls) -> tuple[float, float] | None:
        """Rocks don't have a standard grid size."""
        return None
    
    def __init__(self, center: Point, radius: float, rotation: Rotation = Rotation.ROT_0) -> None:
        """Initialize a rock with position and size.
        
        Args:
            center: Center position in map coordinates (center_x, center_y)
            radius: Final rock radius in drawing units (including any size variations)
            rotation: Rotation angle (affects perturbation)
        """
        # Create boundary shape centered at origin with exact radius
        boundary = Circle(0, 0, radius)
        
        # Initialize prop with center position and boundary
        super().__init__(center, boundary, rotation)
        
        # Store rock-specific properties
        self._radius = radius
        
        # Generate perturbed control points in local coordinates
        self._control_points = self._generate_control_points()
    
    def _generate_control_points(self) -> List[Point]:
        """Generate slightly perturbed control points for the rock shape in local coordinates."""
        points = []
        
        # Generate points around the circle with small random variations
        for i in range(8):  # Use 8 points for a smoother shape
            angle = (i * 2 * math.pi / 8)
            
            # Add random variation to radius (±25%)
            radius_variation = random.uniform(-0.25, 0.25)
            perturbed_radius = self._radius * (1 + radius_variation)
            
            # Calculate point position in local coordinates (centered at 0,0)
            x = perturbed_radius * math.cos(angle)
            y = perturbed_radius * math.sin(angle)
            
            points.append((x, y))
            
        return points

    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if a position is valid for a rock within the container.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            size: Rock radius
            container: The MapElement to place the rock in
            
        Returns:
            True if position is valid, False otherwise
        """
        from algorithms.shapes import Circle
        circle = Circle(x, y, size)
        return container.contains_circle(circle)

    @classmethod
    def get_valid_position(cls, size: float, container: 'MapElement') -> tuple[float, float] | None:
        """Try to find a valid position for a rock within the container.
        
        Args:
            size: Rock radius
            container: The MapElement to place the rock in
            
        Returns:
            Tuple of (x,y) coordinates if valid position found, None otherwise
        """
        bounds = container.bounds
        margin = max(size, CELL_SIZE * 0.25)  # Use larger of rock size or 25% cell size
        
        # Calculate valid range for random positions
        min_x = bounds.x + margin
        max_x = bounds.x + bounds.width - margin
        min_y = bounds.y + margin 
        max_y = bounds.y + bounds.height - margin
        
        # Verify the container is large enough
        if min_x >= max_x or min_y >= max_y:
            print("Container too small for rock!")
            return None
            
        # Try 30 random positions
        for attempt in range(30):
            # Generate random position within bounds
            x = random.uniform(min_x, max_x)
            y = random.uniform(min_y, max_y)
            
            if cls.is_valid_position(x, y, size, container):
                return (x, y)
                
        return None

    @classmethod
    def get_prop_boundary_shape(cls) -> Shape | None:
        """Get the rock's shape in local coordinates."""
        # Return a circle sized between medium min/max
        nominal_size = (MEDIUM_ROCK_MIN_SIZE + MEDIUM_ROCK_MAX_SIZE) / 2
        radius = nominal_size * CELL_SIZE 
        return Circle(0, 0, radius)
        
    def draw(self, canvas: skia.Canvas, layer: Layers = Layers.PROPS) -> None:
        """Draw the rock using a perturbed circular path on the specified layer."""
        if layer != Layers.PROPS:
            return
            
        # Create the rock path
        path = skia.Path()
        
        # Move to first point
        path.moveTo(self._control_points[0][0], self._control_points[0][1])
        
        # Add curved segments between points, including back to start
        num_points = len(self._control_points)
        for i in range(num_points + 1):
            curr_idx = i % num_points
            next_idx = (i + 1) % num_points
            curr_point = self._control_points[curr_idx]
            next_point = self._control_points[next_idx]
            
            # Use quadratic curve between points
            mid_x = (curr_point[0] + next_point[0]) / 2
            mid_y = (curr_point[1] + next_point[1]) / 2
            
            if i == 0:
                # First point - move to midpoint
                path.moveTo(mid_x, mid_y)
            else:
                # Subsequent points - curve through control point to next midpoint
                path.quadTo(curr_point[0], curr_point[1], mid_x, mid_y)

        # Draw fill first
        fill_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
            Color=self._map.options.prop_fill_color
        )
        canvas.drawPath(path, fill_paint)
        
        # Draw stroke on top
        stroke_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=self._map.options.prop_stroke_width,
            Color=self._map.options.prop_outline_color,
            StrokeJoin=skia.Paint.kRound_Join
        )
        canvas.drawPath(path, stroke_paint)
    
    @classmethod
    def add_rocks_to(cls, container: 'MapElement', count: int, rock_type: RockType = RockType.ANY) -> None:
        """Add a specified number of rocks to a map element.
        
        Args:
            container: The MapElement to add rocks to
            count: Number of rocks to add
            rock_type: Type of rocks to add (defaults to ANY which randomly selects types)
            
        Note: Does nothing if container is a Door element.
        """
        from map.door import Door
        
        # Skip if this is a door
        if isinstance(container, Door):
            return
            
        for _ in range(count):
            # Determine rock type
            actual_type = rock_type if rock_type != RockType.ANY else RockType.random_type()
            
            # Random rotation
            rotation = random.uniform(0, 2 * math.pi)
            
            # Get random radius within range for rock type
            if actual_type == RockType.SMALL:
                final_radius = random.uniform(SMALL_ROCK_MIN_SIZE, SMALL_ROCK_MAX_SIZE) * CELL_SIZE
            else:
                final_radius = random.uniform(MEDIUM_ROCK_MIN_SIZE, MEDIUM_ROCK_MAX_SIZE) * CELL_SIZE
            
            valid_pos = cls.get_valid_position(final_radius, container)
            
            if valid_pos:
                # Create rock at valid position with final radius
                rock = cls(valid_pos, final_radius, Rotation.from_radians(rotation))
                container.try_add_prop(rock)
    @classmethod
    def is_valid_position(cls, x: float, y: float, size: float, container: 'MapElement') -> bool:
        """Check if a position is valid for a rock within the container.
        
        Args:
            x: X coordinate to check
            y: Y coordinate to check
            size: Rock radius
            container: The MapElement to place the rock in
            
        Returns:
            True if position is valid, False otherwise
        """
        # Check center point
        if not container.shape.contains(x, y):
            return False
            
        # Check points around the perimeter
        num_probes = 8
        for i in range(num_probes):
            angle = (i * 2 * math.pi / num_probes)
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            if not container.shape.contains(px, py):
                return False
                
        return True
