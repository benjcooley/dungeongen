"""SVG rendering for dungeon layouts."""
from typing import Optional, List, Tuple
from .models import Dungeon, Room, Passage, RoomShape, Door, DoorType, Stair, StairDirection, Exit, ExitType, WaterRegion
from .validator import Violation
from .occupancy import OccupancyGrid, CellType


class SVGRenderer:
    """Renders dungeon layouts as SVG."""
    
    def __init__(self, 
                 grid_size: int = 20,  # Pixels per grid unit
                 padding: int = 40,
                 show_grid: bool = True,
                 show_labels: bool = False):
        self.grid_size = grid_size
        self.padding = padding
        self.show_grid = show_grid
        self.show_labels = show_labels
        
        # Colors
        self.bg_color = "#1a1a2e"
        self.grid_color = "#252542"
        self.room_fill = "#4a4a6a"
        self.room_stroke = "#6a6a9a"
        self.passage_color = "#3a3a5a"
        self.special_colors = {
            'hub': '#6a8a6a',
            'dead_end': '#8a6a6a',
            'lair': '#8a6a8a',
        }
        
        # Door colors - bright and visible
        self.door_colors = {
            'open': '#c4b454',      # Bright gold for open doors
            'closed': '#8b4513',    # Saddle brown for closed doors
            'locked': '#4169e1',    # Royal blue for locked
            'secret': '#696969',    # Dim gray for secret doors
        }
        
        # Stair colors
        self.stair_colors = {
            'up': '#5f9ea0',        # Cadet blue for up stairs
            'down': '#cd853f',      # Peru/tan for down stairs
        }
        
        # Exit colors
        self.exit_colors = {
            'entrance': '#228b22',  # Forest green for main entrance
            'exit': '#dc143c',      # Crimson for exits
            'stairs_up': '#5f9ea0',
            'stairs_down': '#cd853f',
        }
        
        # Water colors
        self.water_fill = "#2a5a7a"
        self.water_stroke = "#1a3a4a"
        self.water_opacity = 0.5
    
    def render(self, dungeon: Dungeon, violations: Optional[List[Violation]] = None,
                occupancy: Optional[OccupancyGrid] = None) -> str:
        """Render dungeon to SVG string."""
        bounds = dungeon.bounds
        
        # Calculate dimensions
        width = (bounds[2] - bounds[0]) * self.grid_size + self.padding * 2
        height = (bounds[3] - bounds[1]) * self.grid_size + self.padding * 2
        
        # Offset to handle negative coordinates
        offset_x = -bounds[0] * self.grid_size + self.padding
        offset_y = -bounds[1] * self.grid_size + self.padding
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">'
        ]
        
        # Background
        svg_parts.append(
            f'<rect x="0" y="0" width="{width}" height="{height}" '
            f'fill="{self.bg_color}"/>'
        )
        
        # Occupancy grid (debug mode) - render UNDER everything else
        if occupancy:
            svg_parts.append(self._render_occupancy(occupancy, bounds, offset_x, offset_y))
        
        # Grid
        if self.show_grid and not occupancy:  # Don't show grid lines over occupancy
            svg_parts.append(self._render_grid(bounds, offset_x, offset_y))
        
        # Passages (render first, under rooms) - skip if showing occupancy
        if not occupancy:
            for passage in dungeon.passages.values():
                svg_parts.append(self._render_passage(passage, offset_x, offset_y))
            
            # Rooms
            for room in dungeon.rooms.values():
                svg_parts.append(self._render_room(room, offset_x, offset_y))
            
            # Water (render after rooms, before doors/props)
            for water in dungeon.water_regions:
                svg_parts.append(self._render_water(water, offset_x, offset_y))
            
            # Doors (render on top of passages/rooms)
            for door in dungeon.doors.values():
                svg_parts.append(self._render_door(door, offset_x, offset_y))
            
            # Stairs (render on top of passages)
            for stair in dungeon.stairs.values():
                svg_parts.append(self._render_stair(stair, offset_x, offset_y))
            
            # Exits (render last, most prominent)
            for exit in dungeon.exits.values():
                svg_parts.append(self._render_exit(exit, offset_x, offset_y))
            
            # Room numbers (render on top)
            for room in dungeon.rooms.values():
                if room.number > 0:
                    svg_parts.append(self._render_room_number(room, offset_x, offset_y))
        
        # Violations (render as red X markers)
        if violations:
            svg_parts.append(self._render_violations(violations, offset_x, offset_y))
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
    
    def _render_occupancy(self, occupancy: OccupancyGrid, bounds, offset_x: int, offset_y: int) -> str:
        """Render occupancy grid as colored cells."""
        parts = ['<g class="occupancy">']
        
        # Generate a color for each unique room/passage element
        element_colors = {}
        color_index = 0
        hues = [0, 120, 240, 60, 180, 300, 30, 150, 270, 90, 210, 330]  # Different hues
        
        for y in range(bounds[1] - 1, bounds[3] + 2):
            for x in range(bounds[0] - 1, bounds[2] + 2):
                info = occupancy.get(x, y)
                
                # Skip only EMPTY and WALL cells
                if info.cell_type in (CellType.EMPTY, CellType.WALL):
                    continue
                
                px = x * self.grid_size + offset_x
                py = y * self.grid_size + offset_y
                
                # Determine fill color based on cell type
                if info.cell_type == CellType.RESERVED:
                    # Halo/reserved: neutral faint marker - doesn't belong to any room
                    # Just indicates "spacing buffer - don't place here"
                    fill = 'rgba(80, 80, 100, 0.25)'
                    label = ''
                elif info.cell_type == CellType.ROOM:
                    # Rooms get bright colors
                    if info.element_id and info.element_id not in element_colors:
                        hue = hues[color_index % len(hues)]
                        color_index += 1
                        element_colors[info.element_id] = hue
                    hue = element_colors.get(info.element_id, 0)
                    fill = f'hsl({hue}, 50%, 40%)'
                    label = 'R'
                elif info.cell_type == CellType.PASSAGE:
                    # Passages get their own color (blue-ish)
                    fill = '#3a4a6a'
                    label = 'P'
                elif info.cell_type == CellType.DOOR:
                    fill = '#6a6a3a'  # Yellow-ish
                    label = 'D'
                elif info.cell_type == CellType.BLOCKED:
                    fill = '#333333'  # Same as reserved - unoccupied but unavailable
                    label = 'B'
                else:
                    fill = '#333333'
                    label = 'B'  # Unknown types treated as blocked
                
                # Draw cell
                parts.append(
                    f'<rect x="{px}" y="{py}" '
                    f'width="{self.grid_size}" height="{self.grid_size}" '
                    f'fill="{fill}" stroke="#222" stroke-width="0.5"/>'
                )
                
                # Add cell type label (if any)
                if label:
                    parts.append(
                        f'<text x="{px + self.grid_size/2}" y="{py + self.grid_size/2 + 3}" '
                        f'fill="#888" font-size="8" text-anchor="middle" '
                        f'font-family="monospace">{label}</text>'
                    )
        
        parts.append('</g>')
        return '\n'.join(parts)
    
    def _render_grid(self, bounds, offset_x: int, offset_y: int) -> str:
        """Render background grid."""
        lines = ['<g class="grid" opacity="0.3">']
        
        # Vertical lines
        for x in range(bounds[0], bounds[2] + 1):
            px = x * self.grid_size + offset_x
            py1 = bounds[1] * self.grid_size + offset_y
            py2 = bounds[3] * self.grid_size + offset_y
            lines.append(
                f'<line x1="{px}" y1="{py1}" x2="{px}" y2="{py2}" '
                f'stroke="{self.grid_color}" stroke-width="1"/>'
            )
        
        # Horizontal lines
        for y in range(bounds[1], bounds[3] + 1):
            py = y * self.grid_size + offset_y
            px1 = bounds[0] * self.grid_size + offset_x
            px2 = bounds[2] * self.grid_size + offset_x
            lines.append(
                f'<line x1="{px1}" y1="{py}" x2="{px2}" y2="{py}" '
                f'stroke="{self.grid_color}" stroke-width="1"/>'
            )
        
        lines.append('</g>')
        return '\n'.join(lines)
    
    def _render_room(self, room: Room, offset_x: int, offset_y: int) -> str:
        """Render a single room."""
        # Determine fill color based on tags
        fill = self.room_fill
        for tag in room.tags:
            if tag in self.special_colors:
                fill = self.special_colors[tag]
                break
        
        # Junction meta-rooms get special rendering
        if room.is_junction:
            return self._render_junction(room, offset_x, offset_y, fill)
        
        if room.shape == RoomShape.CIRCLE:
            # Circle room - x,y is now top-left of bounding box (consistent with rectangles)
            # Use center_world which gives the geometric center in world coordinates
            wcx, wcy = room.center_world
            cx = wcx * self.grid_size + offset_x
            cy = wcy * self.grid_size + offset_y
            r = (room.width / 2) * self.grid_size
            
            svg = (
                f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                f'fill="{fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
            )
        else:
            # Rectangle room
            px = room.x * self.grid_size + offset_x
            py = room.y * self.grid_size + offset_y
            pw = room.width * self.grid_size
            ph = room.height * self.grid_size
            
            svg = (
                f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" '
                f'fill="{fill}" stroke="{self.room_stroke}" stroke-width="2" rx="3"/>'
            )
        
        # Add label if enabled
        if self.show_labels:
            cx, cy = room.center
            px = cx * self.grid_size + offset_x
            py = cy * self.grid_size + offset_y
            svg += (
                f'<text x="{px}" y="{py}" fill="white" '
                f'font-size="10" text-anchor="middle" dominant-baseline="middle">'
                f'{room.id[:4]}</text>'
            )
        
        return svg
    
    def _render_junction(self, room: Room, offset_x: int, offset_y: int, fill: str) -> str:
        """Render a junction meta-room (T, cross, or L)."""
        px = room.x * self.grid_size + offset_x
        py = room.y * self.grid_size + offset_y
        pw = room.width * self.grid_size
        ph = room.height * self.grid_size
        cx = px + pw / 2
        cy = py + ph / 2
        
        # Junction color slightly different
        junction_fill = "#3a3a5a"
        
        if room.shape == RoomShape.CROSS:
            # 4-way cross shape
            arm_w = pw * 0.4
            arm_h = ph * 0.4
            path = (
                f'M {cx - arm_w/2} {py} '
                f'L {cx + arm_w/2} {py} '
                f'L {cx + arm_w/2} {cy - arm_h/2} '
                f'L {px + pw} {cy - arm_h/2} '
                f'L {px + pw} {cy + arm_h/2} '
                f'L {cx + arm_w/2} {cy + arm_h/2} '
                f'L {cx + arm_w/2} {py + ph} '
                f'L {cx - arm_w/2} {py + ph} '
                f'L {cx - arm_w/2} {cy + arm_h/2} '
                f'L {px} {cy + arm_h/2} '
                f'L {px} {cy - arm_h/2} '
                f'L {cx - arm_w/2} {cy - arm_h/2} Z'
            )
            return f'<path d="{path}" fill="{junction_fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
        
        elif room.shape == RoomShape.T_JUNCTION:
            # T shape (pointing down by default)
            arm_w = pw * 0.4
            return (
                f'<rect x="{px}" y="{py}" width="{pw}" height="{ph * 0.5}" '
                f'fill="{junction_fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
                f'<rect x="{cx - arm_w/2}" y="{py}" width="{arm_w}" height="{ph}" '
                f'fill="{junction_fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
            )
        
        elif room.shape == RoomShape.L_CORNER:
            # L shape
            path = (
                f'M {px} {py} '
                f'L {px + pw} {py} '
                f'L {px + pw} {cy} '
                f'L {cx} {cy} '
                f'L {cx} {py + ph} '
                f'L {px} {py + ph} Z'
            )
            return f'<path d="{path}" fill="{junction_fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
        
        # Fallback to rectangle
        return (
            f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" '
            f'fill="{junction_fill}" stroke="{self.room_stroke}" stroke-width="2"/>'
        )
    
    def _render_passage(self, passage: Passage, offset_x: int, offset_y: int) -> str:
        """Render a passage."""
        if len(passage.waypoints) < 2:
            return ''
        
        # Build path - waypoints are grid cells, draw through cell centers
        points = []
        for wx, wy in passage.waypoints:
            px = (wx + 0.5) * self.grid_size + offset_x
            py = (wy + 0.5) * self.grid_size + offset_y
            points.append(f'{px},{py}')
        
        path_d = 'M ' + ' L '.join(points)
        
        # Passage width in pixels
        stroke_width = passage.width * self.grid_size * 0.8
        
        return (
            f'<path d="{path_d}" fill="none" '
            f'stroke="{self.passage_color}" stroke-width="{stroke_width}" '
            f'stroke-linecap="square" stroke-linejoin="miter"/>'
        )
    
    def _render_door(self, door: Door, offset_x: int, offset_y: int) -> str:
        """Render a door at a room entrance."""
        # Position at cell center
        px = (door.x + 0.5) * self.grid_size + offset_x
        py = (door.y + 0.5) * self.grid_size + offset_y
        
        # Door dimensions - make them prominent
        door_length = self.grid_size * 0.8
        door_thickness = self.grid_size * 0.25
        
        # Get color based on door type
        if door.door_type == DoorType.OPEN:
            color = self.door_colors['open']
            stroke_dash = '4,2'  # Dashed for open
        elif door.door_type == DoorType.LOCKED:
            color = self.door_colors['locked']
            stroke_dash = ''
        elif door.door_type == DoorType.SECRET:
            color = self.door_colors['secret']
            stroke_dash = '2,2'
        else:  # CLOSED
            color = self.door_colors['closed']
            stroke_dash = ''
        
        # Rotate based on direction
        if door.direction in ('north', 'south'):
            # Horizontal door
            x1 = px - door_length / 2
            y1 = py - door_thickness / 2
            width = door_length
            height = door_thickness
        else:
            # Vertical door
            x1 = px - door_thickness / 2
            y1 = py - door_length / 2
            width = door_thickness
            height = door_length
        
        # Draw door
        parts = [f'<g class="door">']
        
        # Door rectangle
        dash_attr = f'stroke-dasharray="{stroke_dash}"' if stroke_dash else ''
        parts.append(
            f'<rect x="{x1}" y="{y1}" width="{width}" height="{height}" '
            f'fill="{color}" stroke="#222" stroke-width="1" {dash_attr}/>'
        )
        
        # Add visual indicator for open doors (two parallel lines)
        if door.door_type == DoorType.OPEN:
            if door.direction in ('north', 'south'):
                # Horizontal gaps
                parts.append(
                    f'<line x1="{x1 + door_length * 0.2}" y1="{py}" '
                    f'x2="{x1 + door_length * 0.4}" y2="{py}" '
                    f'stroke="#111" stroke-width="2"/>'
                )
                parts.append(
                    f'<line x1="{x1 + door_length * 0.6}" y1="{py}" '
                    f'x2="{x1 + door_length * 0.8}" y2="{py}" '
                    f'stroke="#111" stroke-width="2"/>'
                )
            else:
                # Vertical gaps
                parts.append(
                    f'<line x1="{px}" y1="{y1 + door_length * 0.2}" '
                    f'x2="{px}" y2="{y1 + door_length * 0.4}" '
                    f'stroke="#111" stroke-width="2"/>'
                )
                parts.append(
                    f'<line x1="{px}" y1="{y1 + door_length * 0.6}" '
                    f'x2="{px}" y2="{y1 + door_length * 0.8}" '
                    f'stroke="#111" stroke-width="2"/>'
                )
        
        # Add lock indicator for locked doors
        if door.door_type == DoorType.LOCKED:
            parts.append(
                f'<circle cx="{px}" cy="{py}" r="{door_thickness * 0.8}" '
                f'fill="#333" stroke="#888" stroke-width="1"/>'
            )
        
        parts.append('</g>')
        return '\n'.join(parts)
    
    def _render_stair(self, stair: Stair, offset_x: int, offset_y: int) -> str:
        """Render stairs in a passage."""
        # Position at cell center
        px = (stair.x + 0.5) * self.grid_size + offset_x
        py = (stair.y + 0.5) * self.grid_size + offset_y
        
        # Stair dimensions
        stair_size = self.grid_size * 0.8
        step_count = 4
        
        # Get color based on direction
        if stair.stair_dir == StairDirection.UP:
            color = self.stair_colors['up']
            arrow = '↑'
        else:
            color = self.stair_colors['down']
            arrow = '↓'
        
        parts = [f'<g class="stair">']
        
        # Draw stair steps based on orientation
        if stair.direction in ('north', 'south'):
            # Vertical stairs
            step_width = stair_size
            step_height = stair_size / step_count
            
            for i in range(step_count):
                # Steps get progressively smaller/lighter going "up"
                if stair.stair_dir == StairDirection.UP:
                    y_pos = py + stair_size/2 - (i + 1) * step_height
                    shade = 1.0 - i * 0.15
                else:
                    y_pos = py - stair_size/2 + i * step_height
                    shade = 0.55 + i * 0.15
                
                step_color = self._shade_color(color, shade)
                parts.append(
                    f'<rect x="{px - step_width/2}" y="{y_pos}" '
                    f'width="{step_width}" height="{step_height * 0.9}" '
                    f'fill="{step_color}" stroke="#333" stroke-width="0.5"/>'
                )
        else:
            # Horizontal stairs
            step_width = stair_size / step_count
            step_height = stair_size
            
            for i in range(step_count):
                if stair.stair_dir == StairDirection.UP:
                    if stair.direction == 'east':
                        x_pos = px - stair_size/2 + i * step_width
                    else:
                        x_pos = px + stair_size/2 - (i + 1) * step_width
                    shade = 0.55 + i * 0.15
                else:
                    if stair.direction == 'east':
                        x_pos = px + stair_size/2 - (i + 1) * step_width
                    else:
                        x_pos = px - stair_size/2 + i * step_width
                    shade = 1.0 - i * 0.15
                
                step_color = self._shade_color(color, shade)
                parts.append(
                    f'<rect x="{x_pos}" y="{py - step_height/2}" '
                    f'width="{step_width * 0.9}" height="{step_height}" '
                    f'fill="{step_color}" stroke="#333" stroke-width="0.5"/>'
                )
        
        # Add direction indicator (small arrow)
        arrow_size = self.grid_size * 0.3
        parts.append(
            f'<text x="{px}" y="{py + arrow_size/3}" '
            f'font-size="{arrow_size}" fill="white" text-anchor="middle" '
            f'font-weight="bold">{arrow}</text>'
        )
        
        parts.append('</g>')
        return '\n'.join(parts)
    
    def _render_exit(self, exit: Exit, offset_x: int, offset_y: int) -> str:
        """Render dungeon entrance/exit as an archway or opening."""
        px = exit.x * self.grid_size + offset_x
        py = exit.y * self.grid_size + offset_y
        
        # Get color based on exit type
        if exit.exit_type == ExitType.ENTRANCE:
            color = self.exit_colors['entrance']
            symbol = '⌂'  # House symbol for entrance
        elif exit.exit_type == ExitType.EXIT:
            color = self.exit_colors['exit']
            symbol = '⮞'  # Arrow out
        elif exit.exit_type == ExitType.STAIRS_UP:
            color = self.exit_colors['stairs_up']
            symbol = '⇑'
        else:
            color = self.exit_colors['stairs_down']
            symbol = '⇓'
        
        parts = [f'<g class="exit">']
        
        # Draw archway based on direction
        arch_width = self.grid_size * 0.9
        arch_height = self.grid_size * 0.9
        
        # Draw arch shape (like a door frame)
        if exit.direction == 'north':
            # Arch facing north
            cx = px + self.grid_size / 2
            cy = py + self.grid_size / 2
            parts.append(
                f'<path d="M {cx - arch_width/2} {cy + arch_height/2} '
                f'L {cx - arch_width/2} {cy - arch_height/4} '
                f'Q {cx - arch_width/2} {cy - arch_height/2} {cx} {cy - arch_height/2} '
                f'Q {cx + arch_width/2} {cy - arch_height/2} {cx + arch_width/2} {cy - arch_height/4} '
                f'L {cx + arch_width/2} {cy + arch_height/2}" '
                f'fill="none" stroke="{color}" stroke-width="3"/>'
            )
        elif exit.direction == 'south':
            cx = px + self.grid_size / 2
            cy = py + self.grid_size / 2
            parts.append(
                f'<path d="M {cx - arch_width/2} {cy - arch_height/2} '
                f'L {cx - arch_width/2} {cy + arch_height/4} '
                f'Q {cx - arch_width/2} {cy + arch_height/2} {cx} {cy + arch_height/2} '
                f'Q {cx + arch_width/2} {cy + arch_height/2} {cx + arch_width/2} {cy + arch_height/4} '
                f'L {cx + arch_width/2} {cy - arch_height/2}" '
                f'fill="none" stroke="{color}" stroke-width="3"/>'
            )
        elif exit.direction == 'west':
            cx = px + self.grid_size / 2
            cy = py + self.grid_size / 2
            parts.append(
                f'<path d="M {cx + arch_width/2} {cy - arch_height/2} '
                f'L {cx - arch_width/4} {cy - arch_height/2} '
                f'Q {cx - arch_width/2} {cy - arch_height/2} {cx - arch_width/2} {cy} '
                f'Q {cx - arch_width/2} {cy + arch_height/2} {cx - arch_width/4} {cy + arch_height/2} '
                f'L {cx + arch_width/2} {cy + arch_height/2}" '
                f'fill="none" stroke="{color}" stroke-width="3"/>'
            )
        else:  # east
            cx = px + self.grid_size / 2
            cy = py + self.grid_size / 2
            parts.append(
                f'<path d="M {cx - arch_width/2} {cy - arch_height/2} '
                f'L {cx + arch_width/4} {cy - arch_height/2} '
                f'Q {cx + arch_width/2} {cy - arch_height/2} {cx + arch_width/2} {cy} '
                f'Q {cx + arch_width/2} {cy + arch_height/2} {cx + arch_width/4} {cy + arch_height/2} '
                f'L {cx - arch_width/2} {cy + arch_height/2}" '
                f'fill="none" stroke="{color}" stroke-width="3"/>'
            )
        
        # Add symbol in center (smaller for cleaner look)
        if exit.is_main:
            # Main entrance gets a filled background circle
            parts.append(
                f'<circle cx="{px + self.grid_size/2}" cy="{py + self.grid_size/2}" '
                f'r="{self.grid_size * 0.25}" fill="{color}" opacity="0.3"/>'
            )
        
        # Add label
        parts.append(
            f'<text x="{px + self.grid_size/2}" y="{py + self.grid_size/2 + 4}" '
            f'font-size="{self.grid_size * 0.5}" fill="{color}" text-anchor="middle" '
            f'font-weight="bold">{symbol}</text>'
        )
        
        parts.append('</g>')
        return '\n'.join(parts)
    
    def _render_water(self, water: WaterRegion, offset_x: int, offset_y: int) -> str:
        """Render water as smooth filled polygon."""
        if not water.boundary or len(water.boundary) < 3:
            return ''
        
        # Convert grid coordinates to pixel coordinates
        points = [
            (x * self.grid_size + offset_x, y * self.grid_size + offset_y)
            for x, y in water.boundary
        ]
        
        # Build SVG path
        path_d = f'M {points[0][0]:.1f},{points[0][1]:.1f} '
        path_d += ' '.join(f'L {p[0]:.1f},{p[1]:.1f}' for p in points[1:])
        path_d += ' Z'
        
        return (
            f'<path d="{path_d}" '
            f'fill="{self.water_fill}" fill-opacity="{self.water_opacity}" '
            f'stroke="{self.water_stroke}" stroke-width="1.5"/>'
        )
    
    def _render_room_number(self, room: Room, offset_x: int, offset_y: int) -> str:
        """Render room number at center of room."""
        cx, cy = room.center_grid
        px = (cx + 0.5) * self.grid_size + offset_x
        py = (cy + 0.5) * self.grid_size + offset_y
        
        # Larger font for room numbers
        font_size = min(self.grid_size * 0.8, room.width * self.grid_size * 0.4)
        
        return (
            f'<text x="{px}" y="{py + font_size * 0.35}" '
            f'font-size="{font_size}" fill="#ffffff" text-anchor="middle" '
            f'font-family="sans-serif" font-weight="bold" opacity="0.7">'
            f'{room.number}</text>'
        )
    
    def _shade_color(self, hex_color: str, factor: float) -> str:
        """Lighten or darken a hex color by a factor (1.0 = original)."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Parse RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Apply factor
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _render_violations(self, violations: List[Violation], offset_x: int, offset_y: int) -> str:
        """Render violation markers as red X symbols."""
        if not violations:
            return ''
        
        parts = ['<g class="violations">']
        
        for v in violations:
            x, y = v.location
            # Place marker at cell center
            px = (x + 0.5) * self.grid_size + offset_x
            py = (y + 0.5) * self.grid_size + offset_y
            
            # Size of the X marker
            size = self.grid_size * 0.8
            
            # Color based on severity
            color = "#ff4444" if v.severity == "error" else "#ffaa44"
            
            # Draw X
            parts.append(
                f'<g transform="translate({px},{py})">'
                f'<line x1="{-size/2}" y1="{-size/2}" x2="{size/2}" y2="{size/2}" '
                f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
                f'<line x1="{size/2}" y1="{-size/2}" x2="{-size/2}" y2="{size/2}" '
                f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
                f'<circle cx="0" cy="0" r="{size/2 + 2}" fill="none" stroke="{color}" stroke-width="2" opacity="0.5"/>'
                f'</g>'
            )
        
        parts.append('</g>')
        return '\n'.join(parts)

