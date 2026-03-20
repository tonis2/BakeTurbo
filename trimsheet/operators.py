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
    """Capture UV coordinates from selected face as a trim region"""
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

    action: bpy.props.StringProperty()  # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj and obj.type == 'MESH' and obj.mode == 'EDIT'
            and has_assignment()
        )

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
            elif self.action == 'ROTATE':
                rotate_uvs(obj, bm, uv_layer)
            elif self.action == 'ROTATE_90':
                rotate_uvs(obj, bm, uv_layer, degrees=90)
            else:
                self.report({'ERROR'}, f"Unknown action: {self.action}")
                return {'CANCELLED'}
        except TrimsheetError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}


class BT_OT_SaveUVs(bpy.types.Operator):
    """Save a UV snapshot by duplicating the active object as a hidden copy"""
    bl_idname = "bake_turbo.save_uvs"
    bl_label = "Save UVs"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not (obj and obj.type == 'MESH' and obj.mode == 'OBJECT'):
            return False
        if not obj.data.uv_layers:
            return False
        snap = obj.bake_turbo_uv_snapshot
        return snap.source_object is None

    def execute(self, context):
        obj = context.active_object

        # Duplicate mesh data and create a new object
        new_mesh = obj.data.copy()
        snapshot = bpy.data.objects.new(f"{obj.name}_uv_snapshot", new_mesh)

        # Link to active collection so it persists in the file
        context.collection.objects.link(snapshot)

        # Copy the world transform so shrinkwrap works correctly
        snapshot.matrix_world = obj.matrix_world.copy()

        # Hide the snapshot
        snapshot.hide_set(True)
        snapshot.hide_render = True
        snapshot.hide_viewport = True

        # Store reference
        obj.bake_turbo_uv_snapshot.source_object = snapshot
        obj.bake_turbo_uv_snapshot.original_name = obj.name

        self.report({'INFO'}, f"UV snapshot saved as '{snapshot.name}'")
        return {'FINISHED'}


class BT_OT_RestoreUVs(bpy.types.Operator):
    """Restore UVs from snapshot using Shrinkwrap + Data Transfer"""
    bl_idname = "bake_turbo.restore_uvs"
    bl_label = "Restore UVs"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not (obj and obj.type == 'MESH' and obj.mode == 'OBJECT'):
            return False
        snap = obj.bake_turbo_uv_snapshot
        return snap.source_object is not None

    def execute(self, context):
        obj = context.active_object
        snapshot = obj.bake_turbo_uv_snapshot.source_object

        if snapshot is None:
            self.report({'ERROR'}, "Snapshot object no longer exists")
            obj.bake_turbo_uv_snapshot.source_object = None
            return {'CANCELLED'}

        # Unhide temporarily so modifiers can access it
        snapshot.hide_set(False)
        snapshot.hide_viewport = False

        # Ensure only the active object is selected
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Add and apply Shrinkwrap modifier
        shrink = obj.modifiers.new(name="_bt_shrinkwrap", type='SHRINKWRAP')
        shrink.target = snapshot
        shrink.wrap_method = 'NEAREST_SURFACEPOINT'
        bpy.ops.object.modifier_apply(modifier=shrink.name)

        # Add and apply Data Transfer modifier
        dt = obj.modifiers.new(name="_bt_data_transfer", type='DATA_TRANSFER')
        dt.object = snapshot
        dt.use_loop_data = True
        dt.data_types_loops = {'UV'}
        dt.loop_mapping = 'NEAREST_POLYNOR'
        bpy.ops.object.modifier_apply(modifier=dt.name)

        # Clean up snapshot
        snapshot_mesh = snapshot.data
        bpy.data.objects.remove(snapshot, do_unlink=True)
        if snapshot_mesh and snapshot_mesh.users == 0:
            bpy.data.meshes.remove(snapshot_mesh)

        # Clear reference
        obj.bake_turbo_uv_snapshot.source_object = None
        obj.bake_turbo_uv_snapshot.original_name = ""

        self.report({'INFO'}, "UVs restored from snapshot")
        return {'FINISHED'}


classes = (
    BT_OT_AddTrimsheet,
    BT_OT_RemoveTrimsheet,
    BT_OT_CaptureRegion,
    BT_OT_RemoveRegion,
    BT_OT_MoveRegion,
    BT_OT_AssignTrim,
    BT_OT_TrimAction,
    BT_OT_SaveUVs,
    BT_OT_RestoreUVs,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
