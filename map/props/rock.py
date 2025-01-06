import math
import random
import skia
from typing import List, TYPE_CHECKING

from algorithms.shapes import Circle, Shape
from algorithms.types import Point
from constants import CELL_SIZE
from map.enums import Layers, RockType
from map.props.prop import Prop
from map.props.rotation import Rotation

if TYPE_CHECKING:
    from map.map import Map
    from map.mapelement import MapElement

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
    def prop_size(cls) -> Point:
        """Get the size of this prop in drawing units.
        
        Returns:
            Tuple of (width, height) in drawing units
        """
        # Use maximum possible size for collision detection
        max_size = MEDIUM_ROCK_MAX_SIZE * CELL_SIZE * 2
        return (max_size, max_size)
        
    @classmethod
    def create_small(cls) -> 'Rock':
        """Create a small rock."""
        radius = random.uniform(SMALL_ROCK_MIN_SIZE, SMALL_ROCK_MAX_SIZE) * CELL_SIZE
        rotation = random.uniform(0, 2 * math.pi)
        return cls((0, 0), radius, Rotation.from_radians(rotation))
        
    @classmethod
    def create_medium(cls) -> 'Rock':
        """Create a medium rock."""
        radius = random.uniform(MEDIUM_ROCK_MIN_SIZE, MEDIUM_ROCK_MAX_SIZE) * CELL_SIZE
        rotation = random.uniform(0, 2 * math.pi)
        return cls((0, 0), radius, rotation)
        
    @classmethod
    def create_large(cls) -> 'Rock':
        """Create a large rock."""
        radius = random.uniform(MEDIUM_ROCK_MAX_SIZE, MEDIUM_ROCK_MAX_SIZE * 1.5) * CELL_SIZE
        rotation = random.uniform(0, 2 * math.pi)
        return cls((0, 0), radius, Rotation.from_radians(rotation))
