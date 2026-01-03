"""Water layer for dungeon maps.

Generates and manages water regions for a dungeon map using:
- Pipeline C noise field (Gaussian basins + fBM)
- Marching squares contour extraction
- Chaikin smoothing

Integrates with the map drawing system.
"""

from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass, field
import numpy as np

from graphics.noise import (
    Perlin2D, fbm, gaussian_basins, 
    normalize, box_blur, apply_gamma
)
from algorithms.marching_squares import extract_contours
from algorithms.chaikin import smooth_polygon, thin_points, catmull_rom_to_bezier


Point = Tuple[float, float]
Contour = List[Point]


# Water depth level presets (threshold values)
# Higher threshold = less water (more selective about what counts as "deep enough")
class WaterDepth:
    """Preset water depth levels."""
    DRY = 0.0        # No water - skip water generation entirely
    PUDDLES = 0.75   # ~30-40% coverage - scattered puddles
    POOLS = 0.60     # ~50-60% coverage - moderate pools
    LAKES = 0.45     # ~70-80% coverage - larger connected bodies
    FLOODED = 0.30   # ~85-95% coverage - heavy water, mostly submerged


@dataclass
class WaterShape:
    """A complete water shape with outer boundary and optional islands.
    
    The outer contour defines the water body. Inner contours (if any)
    define dry islands within the water. Uses even-odd fill rule for rendering.
    """
    outer: Contour                    # Outer water boundary
    islands: List[Contour]            # Inner dry areas (holes)
    bounds: Tuple[float, float, float, float]  # Bounding box of outer contour
    area: float                       # Area of outer contour (not subtracting islands)
    
    @property
    def all_contours(self) -> List[Contour]:
        """All contours for even-odd rendering."""
        return [self.outer] + self.islands


@dataclass
class WaterFieldParams:
    """Parameters for water field generation (Pipeline C)."""
    
    # Resolution scale (0.2 = 20% resolution = faster, coarser shapes)
    resolution_scale: float = 0.2
    
    # Gaussian basins (in scaled coordinates)
    num_basins: int = 6
    sigma_range: Tuple[float, float] = (15, 40)  # Basin radius in scaled pixels
    
    # Low-frequency fBM
    lf_scale: float = 0.018  # Noise sample scale for grid-scale blobs
    lf_octaves: int = 3
    lf_gain: float = 0.55
    lf_blur_radius: int = 2
    lf_blur_passes: int = 1
    
    # Mix and post-processing
    basins_weight: float = 0.60  # Weight of basins vs fBM
    post_blur_radius: int = 1
    post_blur_passes: int = 1
    gamma: float = 1.20
    
    # Contour extraction  
    depth: float = 0.80  # Water threshold (use WaterDepth presets, default=POOLS)
    smooth_iterations: int = 2  # Fewer needed with thinning
    min_area: float = 25.0  # Minimum contour area in scaled pixels




class WaterLayer:
    """Generates and manages water for a dungeon map."""
    
    def __init__(
        self,
        width: int,
        height: int,
        seed: int,
        params: Optional[WaterFieldParams] = None
    ):
        """Initialize water layer.
        
        Args:
            width: Map width in map units
            height: Map height in map units
            seed: Random seed for reproducibility
            params: Field generation parameters
        """
        self.width = width
        self.height = height
        self.seed = seed
        self.params = params or WaterFieldParams()
        
        # Calculate scaled dimensions for faster generation
        scale = self.params.resolution_scale
        self._scaled_width = max(1, int(width * scale))
        self._scaled_height = max(1, int(height * scale))
        self._scale_factor = 1.0 / scale  # To scale contours back up
        
        self._field: Optional[np.ndarray] = None
        self._shapes: List[WaterShape] = []
        self._picture: Optional['skia.Picture'] = None  # Pre-baked drawing
    
    @property
    def field(self) -> np.ndarray:
        """Lazy-generate the water field."""
        if self._field is None:
            self._field = self._generate_field()
        return self._field
    
    @property
    def shapes(self) -> List[WaterShape]:
        """Get extracted water shapes (outer + islands grouped)."""
        return self._shapes
    
    def generate(self, floor_mask: Optional[Callable[[float, float], bool]] = None) -> List[WaterShape]:
        """Generate water shapes (outer contours + grouped islands).
        
        Args:
            floor_mask: Optional function that returns True for valid floor positions.
                       Water will only appear where floor_mask returns True.
                       
        Returns:
            List of WaterShape objects (outer + islands grouped)
        """
        # DRY = no water, skip entirely
        if self.params.depth <= 0:
            self._shapes = []
            return self._shapes
        
        # Generate the field at scaled resolution
        field = self.field
        
        # Apply floor mask if provided (at scaled coords)
        if floor_mask is not None:
            field = self._apply_floor_mask(field, floor_mask)
        
        # Extract contours at scaled resolution
        contours = extract_contours(
            field=field,
            threshold=self.params.depth,
            origin=(0.0, 0.0),
            cell_size=1.0,
            sample_fn=lambda x, y: self._sample_field(field, x, y)
        )
        
        # Process contours at scaled resolution, then scale up
        scale = self._scale_factor
        scaled_boundary = (0.0, 0.0, float(self._scaled_width - 1), float(self._scaled_height - 1))
        
        smoothed_contours = []
        for contour in contours:
            # Thin at scaled resolution
            thinned = thin_points(contour, min_distance=2.0)
            
            # Smooth at scaled resolution
            smoothed = smooth_polygon(
                thinned,
                iterations=self.params.smooth_iterations,
                boundary_rect=scaled_boundary
            )
            
            # Check area at scaled resolution
            area = self._polygon_area(smoothed)
            if area < self.params.min_area:
                continue
            
            # Scale up to full resolution
            scaled_contour = [(p[0] * scale, p[1] * scale) for p in smoothed]
            scaled_area = area * scale * scale
            
            xs = [p[0] for p in scaled_contour]
            ys = [p[1] for p in scaled_contour]
            bounds = (min(xs), min(ys), max(xs), max(ys))
            
            smoothed_contours.append((scaled_contour, bounds, scaled_area))
        
        # Group contours by containment (outer + islands)
        self._shapes = self._group_contours(smoothed_contours)
        
        return self._shapes
    
    def _group_contours(
        self,
        contours: List[Tuple[Contour, Tuple[float, float, float, float], float]]
    ) -> List[WaterShape]:
        """Group contours by containment - outer contours with their islands.
        
        Args:
            contours: List of (contour, bounds, area) tuples
            
        Returns:
            List of WaterShape with outer + nested islands
        """
        if not contours:
            return []
        
        # Sort by area descending (largest first = outer contours)
        sorted_contours = sorted(contours, key=lambda x: -x[2])
        
        # Track which contours are islands (inside another)
        n = len(sorted_contours)
        parent = [-1] * n  # parent[i] = index of containing contour, -1 if root
        
        # For each contour, find smallest containing contour
        for i in range(n):
            contour_i, bounds_i, area_i = sorted_contours[i]
            # Take a point from this contour to test containment
            test_point = contour_i[0]
            
            # Check larger contours (earlier in sorted list) for containment
            for j in range(i):
                contour_j, bounds_j, area_j = sorted_contours[j]
                
                # Quick bounds check first
                if not self._point_in_bounds(test_point, bounds_j):
                    continue
                
                # Full point-in-polygon test
                if self._point_in_polygon(test_point, contour_j):
                    # This contour is inside contour j
                    # But we want the smallest containing one, so keep checking
                    # Since we sorted by area descending, later matches are smaller
                    parent[i] = j
        
        # Build WaterShapes from root contours + their islands
        shapes = []
        for i in range(n):
            if parent[i] == -1:
                # This is a root (outer water boundary)
                outer, bounds, area = sorted_contours[i]
                
                # Find all direct children (islands)
                # Note: children of children are ponds on islands, they become
                # separate WaterShapes (water inside dry inside water)
                islands = []
                for j in range(n):
                    if parent[j] == i:
                        islands.append(sorted_contours[j][0])
                
                shapes.append(WaterShape(
                    outer=outer,
                    islands=islands,
                    bounds=bounds,
                    area=area
                ))
        
        # Also create WaterShapes for "ponds on islands" (grandchildren become roots)
        for i in range(n):
            if parent[i] != -1 and parent[parent[i]] != -1:
                # This contour's parent is also inside something
                # So this is a pond on an island - it's water again
                outer, bounds, area = sorted_contours[i]
                
                # Find its direct children (islands within the pond)
                islands = []
                for j in range(n):
                    if parent[j] == i:
                        islands.append(sorted_contours[j][0])
                
                shapes.append(WaterShape(
                    outer=outer,
                    islands=islands,
                    bounds=bounds,
                    area=area
                ))
        
        return shapes
    
    @staticmethod
    def _point_in_bounds(
        point: Point,
        bounds: Tuple[float, float, float, float]
    ) -> bool:
        """Quick check if point is within bounding box."""
        x, y = point
        min_x, min_y, max_x, max_y = bounds
        return min_x <= x <= max_x and min_y <= y <= max_y
    
    @staticmethod
    def _point_in_polygon(point: Point, polygon: Contour) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        x, y = point
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def _generate_field(self) -> np.ndarray:
        """Generate the water height field using Pipeline C at scaled resolution."""
        p = self.params
        w, h = self._scaled_width, self._scaled_height
        
        # 1. Generate Gaussian basins at scaled resolution
        basins = gaussian_basins(
            width=w,
            height=h,
            seed=self.seed + 101,
            num_basins=p.num_basins,
            sigma_range=p.sigma_range
        )
        
        # 2. Generate low-frequency fBM at scaled resolution
        perlin = Perlin2D(seed=self.seed)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        x = xx * p.lf_scale
        y = yy * p.lf_scale
        
        lf = normalize(fbm(perlin, x, y, octaves=p.lf_octaves, gain=p.lf_gain))
        lf = box_blur(lf, radius=p.lf_blur_radius, passes=p.lf_blur_passes)
        lf = normalize(lf)
        
        # 3. Mix basins and fBM
        field = normalize(
            basins * p.basins_weight + lf * (1.0 - p.basins_weight)
        )
        
        # 4. Post-process
        field = box_blur(field, radius=p.post_blur_radius, passes=p.post_blur_passes)
        field = normalize(field)
        field = apply_gamma(field, p.gamma)
        
        # 5. Invert so water pools grow from centers, not edges
        field = 1.0 - field
        
        return field
    
    def _apply_floor_mask(
        self,
        field: np.ndarray,
        floor_mask: Callable[[float, float], bool]
    ) -> np.ndarray:
        """Set field to 1.0 (no water) where floor_mask is False."""
        masked = field.copy()
        scale = self._scale_factor
        for y in range(self._scaled_height):
            for x in range(self._scaled_width):
                # Convert scaled coords to full coords for mask check
                if not floor_mask(float(x) * scale, float(y) * scale):
                    masked[y, x] = 1.0
        return masked
    
    def _sample_field(self, field: np.ndarray, x: float, y: float) -> float:
        """Sample field at scaled coordinates with bounds checking."""
        ix = int(round(x))
        iy = int(round(y))
        if 0 <= ix < self._scaled_width and 0 <= iy < self._scaled_height:
            return float(field[iy, ix])
        return 1.0  # Outside bounds = no water
    
    def get_picture(self, style=None) -> 'skia.Picture':
        """Get a pre-recorded Skia Picture for fast repeated drawing.
        
        The picture contains all water shapes and can be drawn multiple times
        with different clips efficiently.
        
        Note: Picture is regenerated if style changes from cached version.
        """
        import skia
        from drawing.water import render_water_shapes, WaterStyle
        
        # Check if we need to regenerate (style changed or no cache)
        style_key = (
            style.stroke_width if style else None,
            style.ripple_insets if style else None
        ) if style else None
        
        if self._picture is None or getattr(self, '_picture_style_key', None) != style_key:
            if self._shapes:
                # Record water drawing commands into a Picture
                recorder = skia.PictureRecorder()
                bounds = skia.Rect.MakeWH(self.width, self.height)
                canvas = recorder.beginRecording(bounds)
                
                render_water_shapes(canvas, self._shapes, style)
                
                self._picture = recorder.finishRecordingAsPicture()
                self._picture_style_key = style_key
        
        return self._picture
    
    def draw(self, canvas: 'skia.Canvas', style=None) -> None:
        """Draw water to canvas using pre-recorded picture for speed."""
        picture = self.get_picture(style)
        if picture:
            canvas.drawPicture(picture)
    
    @staticmethod
    def _polygon_area(points: List[Point]) -> float:
        """Calculate polygon area using shoelace formula."""
        if len(points) < 3:
            return 0.0
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0

