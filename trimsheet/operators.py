"""3D viewport operators for trim sheet management and UV assignment."""

import bpy
import bmesh

from .engine import (
    TrimsheetError, assign_trim, mirror_uvs, rotate_uvs,
    clear_assignment, has_assignment, capture_region_from_face,
)


class BT_OT_AddTrimsheet(bpy.types.Operator):
    """Add a new trim sheet"""
    bl_idname = "bake_turbo.add_trimsheet"
    bl_label = "Add Trimsheet"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        trim = context.scene.bake_turbo_trim
        ts = trim.trimsheets.add()
        ts.name = f"Trimsheet {len(trim.trimsheets)}"
        trim.active_trimsheet_index = len(trim.trimsheets) - 1
        return {'FINISHED'}


class BT_OT_RemoveTrimsheet(bpy.types.Operator):
    """Remove the active trim sheet"""
    bl_idname = "bake_turbo.remove_trimsheet"
    bl_label = "Remove Trimsheet"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.bake_turbo_trim.trimsheets) > 0

    def execute(self, context):
        trim = context.scene.bake_turbo_trim
        trim.trimsheets.remove(trim.active_trimsheet_index)
        if trim.active_trimsheet_index >= len(trim.trimsheets):
            trim.active_trimsheet_index = max(0, len(trim.trimsheets) - 1)
        return {'FINISHED'}


class BT_OT_CaptureRegion(bpy.types.Operator):
    """Capture UV coordinates from selected face as a new trim region"""
    bl_idname = "bake_turbo.capture_trim_region"
    bl_label = "Capture Region"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        trim = context.scene.bake_turbo_trim
        return (
            obj and obj.type == 'MESH' and obj.mode == 'EDIT'
            and trim.get_active_trimsheet() is not None
        )

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            self.report({'ERROR'}, "No active UV map!")
            return {'CANCELLED'}

        try:
            coords = capture_region_from_face(bm, uv_layer)
        except TrimsheetError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        ts = context.scene.bake_turbo_trim.get_active_trimsheet()
        name = f"Region {len(ts.regions) + 1}"
        ts.add_region(name, coords)
        self.report({'INFO'}, f"Captured trim region '{name}'")
        return {'FINISHED'}


class BT_OT_RecaptureRegion(bpy.types.Operator):
    """Update the active trim region's UV coordinates from selected face"""
    bl_idname = "bake_turbo.recapture_trim_region"
    bl_label = "Recapture Region"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        trim = context.scene.bake_turbo_trim
        return (
            obj and obj.type == 'MESH' and obj.mode == 'EDIT'
            and trim.get_active_region() is not None
        )

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            self.report({'ERROR'}, "No active UV map!")
            return {'CANCELLED'}

        try:
            coords = capture_region_from_face(bm, uv_layer)
        except TrimsheetError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        region = context.scene.bake_turbo_trim.get_active_region()
        region.set_uv_coords(coords)
        self.report({'INFO'}, f"Updated trim region '{region.name}'")
        return {'FINISHED'}


class BT_OT_RemoveRegion(bpy.types.Operator):
    """Remove the active trim region"""
    bl_idname = "bake_turbo.remove_trim_region"
    bl_label = "Remove Region"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ts = context.scene.bake_turbo_trim.get_active_trimsheet()
        return ts is not None and len(ts.regions) > 0

    def execute(self, context):
        ts = context.scene.bake_turbo_trim.get_active_trimsheet()
        ts.remove_region(ts.active_region_index)
        return {'FINISHED'}


class BT_OT_MoveRegion(bpy.types.Operator):
    """Move the active region up or down in the list"""
    bl_idname = "bake_turbo.move_trim_region"
    bl_label = "Move Region"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.IntProperty(default=1)  # type: ignore

    @classmethod
    def poll(cls, context):
        ts = context.scene.bake_turbo_trim.get_active_trimsheet()
        return ts is not None and len(ts.regions) > 1

    def execute(self, context):
        ts = context.scene.bake_turbo_trim.get_active_trimsheet()
        idx = ts.active_region_index
        new_idx = idx + self.direction

        if 0 <= new_idx < len(ts.regions):
            ts.regions.move(idx, new_idx)
            ts.active_region_index = new_idx

        return {'FINISHED'}


class BT_OT_AssignTrim(bpy.types.Operator):
    """Map selected faces' UVs to the active trim region"""
    bl_idname = "bake_turbo.assign_trim"
    bl_label = "Assign"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        trim = context.scene.bake_turbo_trim
        return (
            obj and obj.type == 'MESH' and obj.mode == 'EDIT'
            and trim.get_active_region() is not None
        )

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            self.report({'ERROR'}, "No active UV map!")
            return {'CANCELLED'}

        trim = context.scene.bake_turbo_trim
        region = trim.get_active_region()
        region_coords = region.get_uv_coords()

        try:
            indices = assign_trim(obj, bm, uv_layer, region_coords, trim.fit_mode)
        except TrimsheetError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        self.report({'INFO'}, f"Assigned '{region.name}' to {len(indices)} faces")
        return {'FINISHED'}


class BT_OT_TrimAction(bpy.types.Operator):
    """Mirror, rotate, or rotate 90 degrees"""
    bl_idname = "bake_turbo.trim_action"
    bl_label = "Trim Action"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})  # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj and obj.type == 'MESH' and obj.mode == 'EDIT'
            and has_assignment()
        )

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            self.report({'ERROR'}, "No active UV map!")
            return {'CANCELLED'}

        try:
            if self.action == 'MIRROR':
                mirror_uvs(obj, bm, uv_layer)
            elif self.action == 'ROTATE_90':
                rotate_uvs(obj, bm, uv_layer, degrees=90)
            else:
                self.report({'ERROR'}, f"Unknown action: {self.action}")
                return {'CANCELLED'}
        except TrimsheetError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    BT_OT_AddTrimsheet,
    BT_OT_RemoveTrimsheet,
    BT_OT_CaptureRegion,
    BT_OT_RecaptureRegion,
    BT_OT_RemoveRegion,
    BT_OT_MoveRegion,
    BT_OT_AssignTrim,
    BT_OT_TrimAction,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
