"""Rock prop implementation."""

import random
import math
import skia
from typing import List, Tuple, TYPE_CHECKING
from map.enums import Layers

from graphics.conversions import grid_to_drawing
from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Circle, Point, Shape

if TYPE_CHECKING:
    from map.map import Map

# Rock sizes as fraction of grid cell
SMALL_ROCK_SIZE = 1/8
MEDIUM_ROCK_SIZE = 1/5

class Rock(Prop):
    """A rock prop with irregular circular shape."""
    
    def __init__(self, x: float, y: float, size: float, map_: 'Map', rotation: float = 0.0) -> None:
        """Initialize a rock with position and size.
        
        Args:
            x: Center X coordinate
            y: Center Y coordinate
            size: Rock size (radius) in drawing units
            map_: Parent map instance
            rotation: Rotation angle (affects perturbation but not overall shape)
        """
        # Calculate bounds (square that contains the perturbed circle)
        bounds_size = size * 2 * 1.2  # Add 20% margin for variations
        bounds_x = x - bounds_size/2
        bounds_y = y - bounds_size/2
        
        super().__init__(bounds_x, bounds_y, bounds_size, bounds_size, map_, rotation)
        
        self._radius = size
        self._center_x = x
        self._center_y = y
        
        # Generate perturbed control points
        self._control_points = self._generate_control_points()
    
    def _generate_control_points(self) -> List[Tuple[float, float]]:
        """Generate slightly perturbed control points for the rock shape."""
        points = []
        
        # Generate points around the circle with small random variations
        for i in range(8):  # Use 8 points for a smoother shape
            angle = (i * 2 * math.pi / 8) + self.rotation
            
            # Add small random variation to radius (±10%)
            radius_variation = random.uniform(-0.1, 0.1)
            perturbed_radius = self._radius * (1 + radius_variation)
            
            # Calculate point position
            x = self._center_x + perturbed_radius * math.cos(angle)
            y = self._center_y + perturbed_radius * math.sin(angle)
            
            points.append((x, y))
            
        return points
    
    def draw(self, canvas: skia.Canvas, layer: 'Layers' = Layers.PROPS) -> None:
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
    def small_rock(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: float = 0.0) -> 'Rock':
        """Create a small rock at the given grid position."""
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        size = map_.options.cell_size * SMALL_ROCK_SIZE
        return cls(x, y, size, map_, rotation)
    
    @classmethod
    def medium_rock(cls, grid_x: float, grid_y: float, map_: 'Map', rotation: float = 0.0) -> 'Rock':
        """Create a medium rock at the given grid position."""
        x, y = grid_to_drawing(grid_x, grid_y, map_.options)
        size = map_.options.cell_size * MEDIUM_ROCK_SIZE
        return cls(x, y, size, map_, rotation)
    
    def _is_valid_position(self, container: Shape) -> bool:
        """Check if the rock's position is valid within the container shape.
        
        Tests multiple points around the rock's perimeter to ensure it fits.
        """
        # Test center point first
        if not container.contains(self._center_x, self._center_y):
            return False
            
        # Test points around the perimeter
        num_probes = 6
        for i in range(num_probes):
            angle = (i * 2 * math.pi / num_probes)
            x = self._center_x + self._radius * math.cos(angle)
            y = self._center_y + self._radius * math.sin(angle)
            if not container.contains(x, y):
                return False
                
        return True
