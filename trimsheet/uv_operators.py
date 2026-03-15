"""UV Editor operators for drawing and selecting trim regions."""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from .engine import capture_region_from_rect


class BT_OT_DrawTrimRegion(bpy.types.Operator):
    """Draw a rectangle in the UV Editor to define a trim region"""
    bl_idname = "bake_turbo.draw_trim_region"
    bl_label = "Draw Region"
    bl_options = {'REGISTER', 'UNDO'}

    # Internal state
    _drawing = False
    _start_uv = None
    _end_uv = None
    _draw_handler = None

    @classmethod
    def poll(cls, context):
        trim = context.scene.bake_turbo_trim
        return (
            context.area and context.area.type == 'IMAGE_EDITOR'
            and trim.get_active_trimsheet() is not None
        )

    def invoke(self, context, event):
        self._drawing = False
        self._start_uv = None
        self._end_uv = None

        self._draw_handler = bpy.types.SpaceImageEditor.draw_handler_add(
            self._draw_callback, (context,), 'WINDOW', 'POST_PIXEL'
        )

        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Click and drag to draw a trim region. ESC to cancel.")
        return {'RUNNING_MODAL'}

    def _draw_callback(self, context):
        if self._start_uv is None or self._end_uv is None:
            return

        region = context.region
        view2d = region.view2d

        p1 = view2d.view_to_region(self._start_uv[0], self._start_uv[1], clip=False)
        p2 = view2d.view_to_region(self._end_uv[0], self._start_uv[1], clip=False)
        p3 = view2d.view_to_region(self._end_uv[0], self._end_uv[1], clip=False)
        p4 = view2d.view_to_region(self._start_uv[0], self._end_uv[1], clip=False)

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')

        # Fill
        batch = batch_for_shader(shader, 'TRIS', {
            "pos": [p1, p2, p3, p1, p3, p4]
        })
        shader.bind()
        shader.uniform_float("color", (0.2, 0.6, 1.0, 0.2))
        batch.draw(shader)

        # Border
        gpu.state.line_width_set(2.0)
        batch = batch_for_shader(shader, 'LINE_STRIP', {
            "pos": [p1, p2, p3, p4, p1]
        })
        shader.bind()
        shader.uniform_float("color", (0.3, 0.7, 1.0, 0.9))
        batch.draw(shader)

        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            uv = context.region.view2d.region_to_view(
                event.mouse_region_x, event.mouse_region_y
            )
            self._end_uv = uv

        elif event.type == 'LEFTMOUSE':
            uv = context.region.view2d.region_to_view(
                event.mouse_region_x, event.mouse_region_y
            )

            if event.value == 'PRESS' and not self._drawing:
                self._drawing = True
                self._start_uv = uv
                self._end_uv = uv
                return {'RUNNING_MODAL'}

            elif event.value == 'RELEASE' and self._drawing:
                self._end_uv = uv
                self._finish(context)
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cleanup(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _finish(self, context):
        s = self._start_uv
        e = self._end_uv

        uv_min = (min(s[0], e[0]), min(s[1], e[1]))
        uv_max = (max(s[0], e[0]), max(s[1], e[1]))

        # Discard tiny rectangles
        if abs(uv_max[0] - uv_min[0]) < 0.001 or abs(uv_max[1] - uv_min[1]) < 0.001:
            self.report({'WARNING'}, "Region too small, cancelled")
            self._cleanup(context)
            return

        coords = capture_region_from_rect(uv_min, uv_max)
        trim = context.scene.bake_turbo_trim
        ts = trim.get_active_trimsheet()
        name = f"Region {len(ts.regions) + 1}"
        ts.add_region(name, coords)

        self._cleanup(context)
        self.report({'INFO'}, f"Added trim region '{name}'")

    def _cleanup(self, context):
        if self._draw_handler is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._draw_handler = None
        context.area.header_text_set(None)
        context.area.tag_redraw()


class BT_OT_SelectTrimRegion(bpy.types.Operator):
    """Click on a trim region overlay to select it"""
    bl_idname = "bake_turbo.select_trim_region"
    bl_label = "Select Region"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        trim = context.scene.bake_turbo_trim
        ts = trim.get_active_trimsheet()
        return (
            context.area and context.area.type == 'IMAGE_EDITOR'
            and ts is not None and len(ts.regions) > 0
        )

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Click on a region to select it. ESC to cancel.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            uv = context.region.view2d.region_to_view(
                event.mouse_region_x, event.mouse_region_y
            )
            hit = self._hit_test(context, uv)
            if hit is not None:
                ts = context.scene.bake_turbo_trim.get_active_trimsheet()
                ts.active_region_index = hit
                context.area.header_text_set(None)
                context.area.tag_redraw()
                self.report({'INFO'}, f"Selected '{ts.regions[hit].name}'")
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.area.header_text_set(None)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _hit_test(self, context, uv_point):
        """Check which region contains the click point. Returns index or None."""
        trim = context.scene.bake_turbo_trim
        ts = trim.get_active_trimsheet()
        if ts is None:
            return None

        x, y = uv_point

        for i, region in enumerate(ts.regions):
            coords = region.get_uv_coords()
            if len(coords) < 3:
                continue

            # Point-in-polygon (ray casting)
            inside = False
            n = len(coords)
            j = n - 1
            for k in range(n):
                xi, yi = coords[k]
                xj, yj = coords[j]
                if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                    inside = not inside
                j = k
            if inside:
                return i

        return None


classes = (BT_OT_DrawTrimRegion, BT_OT_SelectTrimRegion)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
