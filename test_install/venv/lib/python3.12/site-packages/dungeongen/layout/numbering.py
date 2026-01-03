"""Room numbering algorithm using branch-cluster approach.

Numbers rooms starting from entrance, assigning contiguous blocks per branch
at each junction. Uses clockwise ordering from incoming direction.
"""

import math
from typing import Dict, Set, List, Tuple, Optional
from .models import Dungeon, Room


def number_dungeon(dungeon: Dungeon, entrance_room_id: Optional[str] = None, 
                   spine_direction: Optional[Tuple[float, float]] = None) -> Dict[str, int]:
    """
    Number all rooms in the dungeon using branch-cluster algorithm.
    
    Args:
        dungeon: The dungeon to number
        entrance_room_id: The room connected to the entrance passage.
                         If None, finds the room connected to entrance passage.
        spine_direction: Direction vector for the main spine (e.g., (0, 1) for south).
                        If None, inferred from entrance passage direction.
    
    Returns:
        Dict mapping room_id -> room number (1-based)
    """
    # Build adjacency graph from passages
    graph = _build_adjacency_graph(dungeon)
    
    # Get room positions
    positions = {rid: room.center for rid, room in dungeon.rooms.items()}
    
    # Find entrance room and spine direction if not provided
    if entrance_room_id is None:
        entrance_room_id, spine_direction = _find_entrance_and_spine(dungeon)
    
    if entrance_room_id is None or entrance_room_id not in dungeon.rooms:
        # No entrance found, just number rooms in order
        return {rid: i+1 for i, rid in enumerate(dungeon.rooms.keys())}
    
    # Default spine direction is south (positive Y)
    if spine_direction is None:
        spine_direction = (0, 1)
    
    # Run the numbering algorithm
    numberer = _DungeonNumberer(graph, positions, spine_direction)
    return numberer.number(entrance_room_id)


def _build_adjacency_graph(dungeon: Dungeon) -> Dict[str, Set[str]]:
    """Build adjacency graph from passages."""
    graph: Dict[str, Set[str]] = {rid: set() for rid in dungeon.rooms.keys()}
    
    for passage in dungeon.passages.values():
        start = passage.start_room
        end = passage.end_room
        
        # Skip entrance passages (start_room is None)
        if start is None:
            continue
        
        # Skip T-junctions for direct adjacency (end_room == "passage")
        if end == "passage":
            continue
        
        # Add bidirectional edge
        if start in graph and end in graph:
            graph[start].add(end)
            graph[end].add(start)
    
    # Handle T-junctions: find rooms connected through passage cells
    # For now, we rely on direct room-to-room passages
    # T-junctions create implicit connections that should be resolved
    
    return graph


def _find_entrance_room(dungeon: Dungeon) -> Optional[str]:
    """Find the room connected to the entrance passage."""
    for passage in dungeon.passages.values():
        if not passage.start_room:  # Entrance passage (None or empty string)
            if passage.end_room and passage.end_room != "passage":
                return passage.end_room
    return None


def _find_entrance_and_spine(dungeon: Dungeon) -> Tuple[Optional[str], Optional[Tuple[float, float]]]:
    """Find the entrance room and infer spine direction from entrance passage."""
    for passage in dungeon.passages.values():
        if not passage.start_room:  # Entrance passage (None or empty string)
            if passage.end_room and passage.end_room != "passage":
                entrance_room_id = passage.end_room
                
                # Infer spine direction from passage waypoints
                if len(passage.waypoints) >= 2:
                    start = passage.waypoints[0]
                    end = passage.waypoints[-1]
                    dx = end[0] - start[0]
                    dy = end[1] - start[1]
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        # Spine continues in the direction the entrance comes from
                        spine_dir = (dx / length, dy / length)
                        return entrance_room_id, spine_dir
                
                return entrance_room_id, None
    return None, None


class _DungeonNumberer:
    """Internal class to run the numbering algorithm."""
    
    def __init__(self, graph: Dict[str, Set[str]], positions: Dict[str, Tuple[float, float]],
                 spine_direction: Tuple[float, float] = (0, 1)):
        self.graph = graph
        self.positions = positions
        self.spine_direction = spine_direction  # Direction of main spine from entrance
        self.visited: Set[str] = set()
        self.numbers: Dict[str, int] = {}
        self.next_num = 1
    
    def number(self, entrance: str) -> Dict[str, int]:
        """Run the numbering algorithm starting from entrance."""
        self._assign_number(entrance)
        self._process_junction_room(entrance, parent=None)
        
        # Number any disconnected rooms (shouldn't happen with valid dungeons)
        for room_id in self.graph.keys():
            if room_id not in self.visited:
                self._assign_number(room_id)
                self._process_junction_room(room_id, parent=None)
        
        return self.numbers
    
    def _assign_number(self, room: str) -> None:
        """Assign the next number to a room."""
        self.visited.add(room)
        self.numbers[room] = self.next_num
        self.next_num += 1
    
    def _process_junction_room(self, u: str, parent: Optional[str]) -> None:
        """Process a junction room, numbering all outgoing branches."""
        # Order exits by clockwise angle from incoming direction
        exits = self._ordered_exits(u, parent)
        
        # For each exit, number the entire branch component
        for v in exits:
            if v in self.visited:
                continue
            
            # Compute branch region (connected component from v, blocking u)
            component = self._component_without_node(v, blocked=u)
            
            # Number that region as a contiguous cluster
            self._number_component_clustered(root=u, entry=v, component=component)
    
    def _number_component_clustered(self, root: str, entry: str, component: Set[str]) -> None:
        """Number all rooms in a component as a contiguous cluster."""
        if entry not in self.visited:
            self._assign_number(entry)
        
        # Work stack: (current_room, parent_room)
        work: List[Tuple[str, Optional[str]]] = [(entry, root)]
        
        while work:
            u, parent = work.pop()
            
            if u not in component:
                continue
            
            # Process exits within this component
            exits = self._ordered_exits_restricted(u, parent, component)
            
            for v in exits:
                if v in self.visited:
                    continue
                
                # Sub-branch component
                sub_component = self._component_without_node_restricted(v, blocked=u, allowed=component)
                
                if v not in self.visited:
                    self._assign_number(v)
                
                work.append((v, u))
                
                # Fill any remaining rooms in sub-component
                self._fill_sub_component(entry_node=v, sub_component=sub_component, work=work)
    
    def _fill_sub_component(self, entry_node: str, sub_component: Set[str], 
                           work: List[Tuple[str, Optional[str]]]) -> None:
        """Ensure all rooms in sub-component get numbered."""
        while True:
            # Find unvisited rooms in sub-component
            unvisited = [r for r in sub_component if r not in self.visited]
            if not unvisited:
                break
            
            # Select next room by encounter heuristic (closest to entry, then clockwise)
            r = self._select_next_room(entry_node, sub_component, unvisited)
            
            self._assign_number(r)
            
            # Find a parent for ordering
            parent = self._choose_parent(r, sub_component)
            work.append((r, parent))
    
    def _select_next_room(self, entry: str, allowed: Set[str], candidates: List[str]) -> str:
        """Select next room by distance from entry, tie-break by clockwise angle."""
        # Compute distances within allowed set
        distances = self._bfs_distances(entry, allowed)
        
        best = candidates[0]
        best_dist = distances.get(best, float('inf'))
        
        entry_pos = self.positions.get(entry, (0, 0))
        
        for r in candidates:
            d = distances.get(r, float('inf'))
            if d < best_dist:
                best = r
                best_dist = d
            elif d == best_dist:
                # Tie-break by clockwise angle from north
                r_pos = self.positions.get(r, (0, 0))
                best_pos = self.positions.get(best, (0, 0))
                
                r_angle = self._clockwise_angle((0, 1), self._normalize(
                    (r_pos[0] - entry_pos[0], r_pos[1] - entry_pos[1])))
                best_angle = self._clockwise_angle((0, 1), self._normalize(
                    (best_pos[0] - entry_pos[0], best_pos[1] - entry_pos[1])))
                
                if r_angle < best_angle:
                    best = r
                    best_dist = d
        
        return best
    
    def _choose_parent(self, room: str, allowed: Set[str]) -> Optional[str]:
        """Choose a visited neighbor as parent for ordering."""
        for neighbor in self.graph.get(room, []):
            if neighbor in allowed and neighbor in self.visited:
                return neighbor
        return None
    
    def _ordered_exits(self, u: str, parent: Optional[str]) -> List[str]:
        """Get neighbors of u, excluding parent, sorted by clockwise angle."""
        neighbors = set(self.graph.get(u, []))
        if parent is not None:
            neighbors.discard(parent)
        return self._sort_by_clockwise(u, parent, list(neighbors))
    
    def _ordered_exits_restricted(self, u: str, parent: Optional[str], 
                                  allowed: Set[str]) -> List[str]:
        """Get neighbors of u within allowed set, excluding parent, sorted clockwise."""
        neighbors = [v for v in self.graph.get(u, []) if v in allowed and v != parent]
        return self._sort_by_clockwise(u, parent, neighbors)
    
    def _sort_by_clockwise(self, u: str, parent: Optional[str], 
                          neighbors: List[str]) -> List[str]:
        """Sort neighbors prioritizing spine direction, then clockwise from incoming direction."""
        u_pos = self.positions.get(u, (0, 0))
        
        # Reference direction: from parent to u, or spine direction if no parent (entrance room)
        if parent is not None:
            parent_pos = self.positions.get(parent, (0, 0))
            ref_dir = self._normalize((u_pos[0] - parent_pos[0], u_pos[1] - parent_pos[1]))
        else:
            # For entrance room, use spine direction as reference
            # This makes the spine neighbor (straight ahead) come first
            ref_dir = self.spine_direction
        
        def angle_key(v: str) -> float:
            v_pos = self.positions.get(v, (0, 0))
            direction = self._normalize((v_pos[0] - u_pos[0], v_pos[1] - u_pos[1]))
            return self._clockwise_angle(ref_dir, direction)
        
        return sorted(neighbors, key=angle_key)
    
    def _component_without_node(self, start: str, blocked: str) -> Set[str]:
        """Find connected component from start, not passing through blocked."""
        component: Set[str] = set()
        stack = [start]
        
        while stack:
            x = stack.pop()
            if x == blocked or x in component:
                continue
            component.add(x)
            for y in self.graph.get(x, []):
                if y != blocked and y not in component:
                    stack.append(y)
        
        return component
    
    def _component_without_node_restricted(self, start: str, blocked: str, 
                                           allowed: Set[str]) -> Set[str]:
        """Find connected component from start within allowed set, not through blocked."""
        component: Set[str] = set()
        stack = [start]
        
        while stack:
            x = stack.pop()
            if x == blocked or x not in allowed or x in component:
                continue
            component.add(x)
            for y in self.graph.get(x, []):
                if y != blocked and y in allowed and y not in component:
                    stack.append(y)
        
        return component
    
    def _bfs_distances(self, start: str, allowed: Set[str]) -> Dict[str, int]:
        """Compute BFS distances from start within allowed set."""
        distances: Dict[str, int] = {start: 0}
        queue = [start]
        
        while queue:
            current = queue.pop(0)
            current_dist = distances[current]
            
            for neighbor in self.graph.get(current, []):
                if neighbor in allowed and neighbor not in distances:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)
        
        return distances
    
    @staticmethod
    def _normalize(v: Tuple[float, float]) -> Tuple[float, float]:
        """Normalize a 2D vector."""
        length = math.sqrt(v[0] * v[0] + v[1] * v[1])
        if length < 0.0001:
            return (0, 1)
        return (v[0] / length, v[1] / length)
    
    @staticmethod
    def _clockwise_angle(ref: Tuple[float, float], v: Tuple[float, float]) -> float:
        """Compute clockwise angle from ref to v (0 to 2π)."""
        # Using atan2 for angle calculation
        # Clockwise from ref means we compute the angle difference
        ref_angle = math.atan2(ref[0], ref[1])  # Note: (x, y) for clockwise from north
        v_angle = math.atan2(v[0], v[1])
        
        diff = v_angle - ref_angle
        
        # Normalize to [0, 2π)
        while diff < 0:
            diff += 2 * math.pi
        while diff >= 2 * math.pi:
            diff -= 2 * math.pi
        
        return diff

