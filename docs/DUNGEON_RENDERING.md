# Dungeon Rendering Deep Dive

This document explains how DungeonGen renders dungeon maps, including region grouping, clipping, layered drawing, and shadow effects.

## Overview

The rendering system transforms a layout `Dungeon` into a visual map with:
- Crosshatch "wall" texture around rooms
- Filled floor areas with shadows
- Dot grid overlays
- Water features
- Props (columns, altars, etc.)
- Borders, doors, and room numbers

## Rendering Pipeline

```
1. Create Regions          → Group connected elements
2. Build Crosshatch Shape  → Union of inflated regions
3. Draw Background         → Solid color fill
4. Draw Crosshatch         → Tiled hatch pattern
5. For each Region:
   a. Clip to region shape
   b. Draw shadow
   c. Draw room fill (offset)
   d. Draw element shadows (Layers.SHADOW)
   e. Draw grid
   f. Draw water
   g. Draw props (Layers.PROPS)
   h. Restore clip
6. Draw Borders            → Unified outline
7. Draw Overlays           → Doors (Layers.OVERLAY)
8. Draw Text              → Room numbers (Layers.TEXT)
```

## Region System

### What is a Region?

A **Region** groups map elements (rooms, passages) that are connected and not separated by closed doors. Each region is rendered as a contiguous floor area.

```python
class Region:
    shape: Shape              # Combined geometry (ShapeGroup)
    elements: List[MapElement]  # Rooms, passages in this region
```

### Why Regions?

1. **Crosshatch clipping**: The inflated union of all region shapes defines where crosshatch appears
2. **Shadow/fill isolation**: Each region gets its own shadow and fill pass
3. **Closed door handling**: Closed doors break connectivity, creating separate regions
4. **Exit handling**: Exits add a "chip" shape but don't extend the region

### Region Tracing

```python
def _trace_connected_region(element, visited, region):
    if element in visited:
        return
    
    visited.add(element)
    region.append(element)
    
    for connection in element.connections:
        # Closed doors: add side shape, but don't traverse
        if isinstance(connection, Door) and not connection.open:
            region.append(connection.get_side_shape(element))
            continue
        
        # Exits: add chip shape, terminal (no traversal)
        if isinstance(connection, Exit):
            region.append(connection.get_side_shape(element))
            continue
        
        # Recurse into connected elements
        _trace_connected_region(connection, visited, region)
```

### Building Region Shapes

```python
def _make_regions(self):
    visited = set()
    regions = []
    
    for element in self._elements:
        if element in visited or isinstance(element, Exit):
            continue
        
        region_elements = []
        self._trace_connected_region(element, visited, region_elements)
        
        if region_elements:
            # Collect shapes (inflated slightly for overlap)
            shapes = []
            final_elements = []
            for item in region_elements:
                if isinstance(item, MapElement):
                    shapes.append(item.shape.inflated(REGION_INFLATE))
                    final_elements.append(item)
                else:  # Side shape from door/exit
                    shapes.append(item)
            
            regions.append(Region(
                shape=ShapeGroup.combine(shapes),
                elements=final_elements
            ))
    
    return regions
```

## Crosshatch Area

The crosshatch pattern fills a border around all rooms/passages:

```python
# Inflate each region's shape by crosshatch_border_size
crosshatch_shapes = []
for region in regions:
    crosshatch_shapes.append(region.shape.inflated(options.crosshatch_border_size))

# Combine all into single shape
crosshatch_shape = ShapeGroup.combine(crosshatch_shapes)
```

This creates a "halo" of crosshatch around the dungeon interior.

## Layer System

Map elements draw in multiple passes using the `Layers` enum:

```python
class Layers(Enum):
    SHADOW = auto()    # Drop shadows (first)
    PROPS = auto()     # Main prop content
    OVERLAY = auto()   # Doors, overlays (on top of borders)
    TEXT = auto()      # Room numbers (last)
```

Each element's `draw(canvas, layer)` is called once per layer:

```python
# Within region rendering:
for element in region.elements:
    element.draw(canvas, Layers.SHADOW)
# ... draw grid, water ...
for element in region.elements:
    element.draw(canvas, Layers.PROPS)

# After all regions:
for element in self._elements:
    element.draw(canvas, Layers.OVERLAY)
for element in self._elements:
    element.draw(canvas, Layers.TEXT)
```

## Shadow and Fill Rendering

### The Offset Trick

Shadows and fills use an offset to create depth:

```
Without offset:               With offset:
┌─────────┐                  ┌─────────┐
│  FILL   │                  │░░FILL░░░│──┐
│         │                  │░░░░░░░░░│  │ Shadow behind
└─────────┘                  └─────────┘──┘
```

The fill is drawn **offset** from the shadow, creating the illusion that the floor is floating above the shadow layer.

### Implementation

```python
# 1. Clip to region shape
canvas.save()
canvas.clipPath(region.shape.to_path(), skia.ClipOp.kIntersect, True)

# 2. Draw shadow (no offset)
shadow_paint = skia.Paint(
    Style=skia.Paint.kFill_Style,
    Color=options.room_shadow_color  # Light gray
)
region.shape.draw(canvas, shadow_paint)

# 3. Draw fill (with offset)
room_paint = skia.Paint(
    Style=skia.Paint.kFill_Style,
    Color=options.room_color  # White
)
canvas.save()
canvas.translate(
    options.room_shadow_offset_x + (options.border_width * 0.5),
    options.room_shadow_offset_y + (options.border_width * 0.5)
)
region.shape.draw(canvas, room_paint)
canvas.restore()

# 4. Restore clip
canvas.restore()
```

The extra `border_width * 0.5` ensures the fill covers the shadow right up to where the border will be drawn.

## Grid Overlay

Dot grids are drawn within each region's clip:

```python
if options.grid_style == GridStyle.DOTS:
    draw_region_grid(canvas, region, options)
```

The grid respects the region clip, so dots only appear on floor areas.

## Water Integration

Water is generated at map bounds and drawn within region clips:

```python
if self.water_layer and self.water_layer.shapes:
    canvas.save()
    # Translate water to map coordinates
    canvas.translate(self.bounds.x, self.bounds.y)
    
    water_style = WaterStyle(
        stroke_width=self._water_stroke_width,
        ripple_insets=(self._water_ripple_inset, self._water_ripple_inset * 2)
    )
    
    # Draw using pre-recorded picture for speed
    self.water_layer.draw(canvas, style=water_style)
    canvas.restore()
```

Because water is drawn while clipped to the region, it automatically stays within floor areas.

## Border Rendering

Borders are drawn **after** all regions, as a unified outline:

```python
border_paint = skia.Paint(
    Style=skia.Paint.kStroke_Style,
    StrokeWidth=options.border_width,
    Color=options.border_color,
    StrokeJoin=skia.Paint.kRound_Join  # Rounded corners
)

# Combine all region paths
unified_border = skia.Path()
for region in regions:
    unified_border.addPath(region.shape.to_path())

# Draw single unified stroke
canvas.drawPath(unified_border, border_paint)
```

Drawing borders as a single path ensures consistent stroke width at intersections.

## Door Overlays

Doors draw on `Layers.OVERLAY` so they appear on top of borders:

```python
# After region rendering and borders:
for element in self._elements:
    element.draw(canvas, Layers.OVERLAY)
```

Door elements check the layer and only draw their overlay (threshold bar, door rectangle) during this pass.

## Transform System

Maps are rendered with a transform that scales and centers:

```python
def calculate_fit_transform(self, canvas_width, canvas_height):
    bounds = self.bounds
    
    # Padding in grid units
    padding_x, padding_y = grid_to_map(options.map_border_cells, options.map_border_cells)
    
    # Scale to fit
    padded_width = bounds.width + (2 * padding_x)
    padded_height = bounds.height + (2 * padding_y)
    scale = min(canvas_width / padded_width, canvas_height / padded_height)
    
    # Center
    translate_x = ((canvas_width - (bounds.width * scale)) / 2) - (bounds.x * scale)
    translate_y = ((canvas_height - (bounds.height * scale)) / 2) - (bounds.y * scale)
    
    matrix = skia.Matrix()
    matrix.setScale(scale, scale)
    matrix.postTranslate(translate_x, translate_y)
    return matrix
```

The transform is applied once at the start of rendering:

```python
def render(self, canvas, transform=None):
    matrix = transform or self.calculate_fit_transform(canvas_width, canvas_height)
    
    canvas.save()
    canvas.concat(matrix)
    
    # ... all drawing happens in map coordinates ...
    
    canvas.restore()
```

## Prop Rendering

Props (columns, altars, etc.) are drawn during `Layers.PROPS` and `Layers.SHADOW`:

```python
# In MapElement.draw():
def draw(self, canvas, layer):
    if layer == Layers.PROPS:
        # Draw decoration props first
        for prop in self._props:
            if prop.prop_type.is_decoration:
                prop.draw(canvas, layer)
        
        # Then non-decoration props
        for prop in self._props:
            if not prop.prop_type.is_decoration:
                prop.draw(canvas, layer)
    
    elif layer == Layers.SHADOW:
        # Only shadow for non-decoration props
        for prop in self._props:
            if not prop.prop_type.is_decoration:
                prop.draw(canvas, layer)
```

Props handle their own layer-specific drawing:

```python
# In Prop._draw_content():
def _draw_content(self, canvas, bounds, layer):
    if layer == Layers.SHADOW:
        # Draw offset shadow shape
        canvas.save()
        canvas.translate(shadow_offset_x, shadow_offset_y)
        shadow_shape.draw(canvas, shadow_paint)
        canvas.restore()
    
    elif layer == Layers.PROPS:
        # Draw fill and outline
        shape.draw(canvas, fill_paint)
        shape.draw(canvas, outline_paint)
```

## Full Render Flow

```python
def render(self, canvas, transform=None):
    # Setup
    matrix = transform or self.calculate_fit_transform(...)
    canvas.save()
    canvas.concat(matrix)
    
    # 1. Background
    canvas.drawRect(full_canvas, background_paint)
    
    # 2. Build regions and crosshatch shape
    regions = self._make_regions()
    crosshatch_shape = combine_inflated(regions)
    
    # 3. Crosshatch background fill
    crosshatch_shape.draw(canvas, shading_paint)
    
    # 4. Crosshatch pattern
    draw_crosshatches_tiled(canvas, crosshatch_shape, self.hatch_tile, options)
    
    # 5. Render each region
    for region in regions:
        canvas.save()
        canvas.clipPath(region.shape.to_path())
        
        # Shadow
        region.shape.draw(canvas, shadow_paint)
        
        # Fill (offset)
        canvas.translate(shadow_offset)
        region.shape.draw(canvas, room_paint)
        canvas.restore()  # Remove offset
        
        # Element shadows
        for element in region.elements:
            element.draw(canvas, Layers.SHADOW)
        
        # Grid
        draw_region_grid(canvas, region, options)
        
        # Water
        if water_layer:
            water_layer.draw(canvas, style)
        
        # Props
        for element in region.elements:
            element.draw(canvas, Layers.PROPS)
        
        canvas.restore()  # Remove clip
    
    # 6. Borders (unified)
    canvas.drawPath(unified_border, border_paint)
    
    # 7. Overlays (doors)
    for element in self._elements:
        element.draw(canvas, Layers.OVERLAY)
    
    # 8. Text (room numbers)
    for element in self._elements:
        element.draw(canvas, Layers.TEXT)
    
    canvas.restore()  # Remove transform
```

## Output Formats

### PNG

```python
def render_to_png(self, filename, width=1200, height=1200):
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    self.render(canvas)
    image = surface.makeImageSnapshot()
    image.save(filename, skia.kPNG)
```

### SVG

```python
def render_to_svg(self, filename, width=1200, height=1200):
    stream = skia.FILEWStream(filename)
    canvas = skia.SVGCanvas.Make((width, height), stream)
    self.render(canvas)
    del canvas  # Flush SVG
    stream.flush()
```

Both formats use the same `render()` method - Skia handles the format-specific encoding.

