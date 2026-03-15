"""GPU overlay drawing for trim sheet regions in the UV Editor."""

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader

_draw_handler = None

# Predefined colors for regions (cycling)
REGION_COLORS = [
    (0.9, 0.3, 0.3, 0.15),  # red
    (0.3, 0.7, 0.9, 0.15),  # blue
    (0.3, 0.9, 0.4, 0.15),  # green
    (0.9, 0.7, 0.2, 0.15),  # yellow
    (0.7, 0.3, 0.9, 0.15),  # purple
    (0.9, 0.5, 0.2, 0.15),  # orange
    (0.2, 0.9, 0.8, 0.15),  # cyan
    (0.9, 0.3, 0.7, 0.15),  # pink
]

ACTIVE_BORDER_COLOR = (1.0, 1.0, 1.0, 0.9)
INACTIVE_BORDER_COLOR = (0.7, 0.7, 0.7, 0.5)


def _get_region_color(index):
    color = REGION_COLORS[index % len(REGION_COLORS)]
    return color


def _draw_regions():
    """Draw all trim regions as overlays in the UV Editor."""
    context = bpy.context
    scene = context.scene
    if not hasattr(scene, 'bake_turbo_trim'):
        return

    trim_settings = scene.bake_turbo_trim
    ts = trim_settings.get_active_trimsheet()
    if ts is None or len(ts.regions) == 0:
        return

    region = context.region
    view2d = region.view2d

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')

    for i, trim_region in enumerate(ts.regions):
        coords = trim_region.get_uv_coords()
        if len(coords) < 3:
            continue

        is_active = (i == ts.active_region_index)

        # Convert UV coords to screen coords
        screen_coords = []
        for uv in coords:
            sx, sy = view2d.view_to_region(uv[0], uv[1], clip=False)
            screen_coords.append((sx, sy))

        # Draw filled rectangle (for quads, use triangle fan)
        if len(screen_coords) >= 3:
            fill_color = _get_region_color(i)
            if is_active:
                fill_color = (fill_color[0], fill_color[1], fill_color[2], 0.25)

            # Triangulate as fan from first vertex
            tris = []
            for j in range(1, len(screen_coords) - 1):
                tris.extend([screen_coords[0], screen_coords[j], screen_coords[j + 1]])

            batch = batch_for_shader(shader, 'TRIS', {"pos": tris})
            shader.bind()
            shader.uniform_float("color", fill_color)
            batch.draw(shader)

        # Draw border
        border_coords = screen_coords + [screen_coords[0]]
        border_color = ACTIVE_BORDER_COLOR if is_active else INACTIVE_BORDER_COLOR

        gpu.state.line_width_set(2.0 if is_active else 1.0)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": border_coords})
        shader.bind()
        shader.uniform_float("color", border_color)
        batch.draw(shader)

        # Draw label at center
        if len(screen_coords) >= 2:
            cx = sum(p[0] for p in screen_coords) / len(screen_coords)
            cy = sum(p[1] for p in screen_coords) / len(screen_coords)

            font_id = 0
            blf.size(font_id, 12)
            blf.position(font_id, cx - len(trim_region.name) * 3, cy - 6, 0)
            blf.color(font_id, 1.0, 1.0, 1.0, 0.8 if is_active else 0.5)
            blf.draw(font_id, trim_region.name)

    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def register():
    global _draw_handler
    if _draw_handler is None:
        _draw_handler = bpy.types.SpaceImageEditor.draw_handler_add(
            _draw_regions, (), 'WINDOW', 'POST_PIXEL'
        )


def unregister():
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
