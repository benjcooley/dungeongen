"""Helper functions for debug visualization in tests."""

from typing import List, Tuple
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import skia

def draw_passage_debug(
    points: List[Tuple[int, int]], 
    manhattan_distances: List[int],
    bend_positions: List[int],
    canvas: 'skia.Canvas'
) -> None:
    print("\nDEBUG TestDraw: Drawing passage debug")
    print(f"DEBUG TestDraw: Points: {points}")
    print(f"DEBUG TestDraw: Manhattan distances: {manhattan_distances}")
    print(f"DEBUG TestDraw: Bend positions: {bend_positions}")
    """Draw debug visualization for passage points.
    
    Args:
        points: List of passage points
        manhattan_distances: List of cumulative Manhattan distances at each point
        bend_positions: List of positions where bends occur
        canvas: Canvas to draw on
    """
    from graphics.conversions import grid_to_map
    import skia
    
    # Draw Manhattan distances
    paint = skia.Paint(Color=skia.ColorGREEN)
    paint.setTextSize(16)
    
    for i, dist in enumerate(manhattan_distances):
        if i < len(points) - 1:  # Skip last point
            px, py = grid_to_map(points[i+1][0], points[i+1][1])
            canvas.drawString(f"d={dist}", px + 10, py - 10, paint)
    
    # Draw bend positions text
    paint = skia.Paint(Color=skia.ColorBLUE)
    paint.setTextSize(16)
    if bend_positions:
        px, py = grid_to_map(points[0][0], points[0][1])
        bend_text = f"bends at: {', '.join(map(str, bend_positions))}"
        canvas.drawString(bend_text, px - 20, py - 30, paint)
