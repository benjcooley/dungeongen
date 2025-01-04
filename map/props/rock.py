"""Rock prop implementation."""

import random
import math
import skia
from typing import List, Tuple, TYPE_CHECKING
from map.enums import Layers, RockType
from map.mapelement import MapElement

# Rock sizes as fraction of grid cell
SMALL_ROCK_SIZE = 1/12
MEDIUM_ROCK_SIZE = 1/8

from graphics.conversions import grid_to_drawing
from map.props.prop import Prop
from map.props.rotation import Rotation
from algorithms.shapes import Circle, Point, Shape

if TYPE_CHECKING:
    from map.map import Map

# Rock sizes as fraction of grid cell
SMALL_ROCK_SIZE = 1/12
MEDIUM_ROCK_SIZE = 1/8

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
            
            # Add random variation to radius (±25%)
            radius_variation = random.uniform(-0.25, 0.25)
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
            
            # Calculate rock size and try to find valid position
            size = (SMALL_ROCK_SIZE if actual_type == RockType.SMALL else MEDIUM_ROCK_SIZE) * container._map.options.cell_size
            valid_pos = cls.get_valid_position(size, container)
            
            if valid_pos:
                # Create rock at valid position
                # Calculate rock size based on type
                size = (SMALL_ROCK_SIZE if actual_type == RockType.SMALL else MEDIUM_ROCK_SIZE) * container._map.options.cell_size
            
                # Create rock with calculated size
                rock = cls(valid_pos[0], valid_pos[1], size, container._map, rotation)
                container.try_add_prop(rock)

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
        margin = size + (container._map.options.cell_size * 0.25)  # Add rock size to margin
        
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
            
            # Check center point
            if not container.shape.contains(x, y):
                continue
                
            # Check points around the perimeter
            valid = True
            num_probes = 8  # Increased from 6 for better coverage
            for i in range(num_probes):
                angle = (i * 2 * math.pi / num_probes)
                px = x + size * math.cos(angle)
                py = y + size * math.sin(angle)
                if not container.shape.contains(px, py):
                    valid = False
                    break
                    
            if valid:
                return (x, y)
                
        return None

