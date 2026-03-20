"""3D Viewport sidebar panels for Bake Turbo."""

from __future__ import annotations

import bpy

from ..modes import BAKE_MODES
from ..core.bake_sets import get_bake_sets


# --- UIList for trim regions ---

class BT_UL_TrimRegions(bpy.types.UIList):
    bl_idname = "BT_UL_TrimRegions"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        layout.prop(item, "name", text="", emboss=False, icon='UV_DATA')


# --- Main panel ---

class BT_PT_BakeMain(bpy.types.Panel):
    bl_label = "Bake Turbo"
    bl_idname = "BT_PT_BakeMain"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo

        # Mode switcher
        layout.prop(settings, "panel_mode", expand=True)
        layout.separator()

        if settings.panel_mode == 'BAKE':
            self._draw_bake(context, layout, settings)
        else:
            self._draw_trimsheet(context, layout)

    def _draw_bake(self, context, layout, settings):
        # Mode selector
        layout.prop(settings, "bake_mode", text="Mode")

        # Image settings
        row = layout.row(align=True)
        row.prop(settings, "image_size", text="Size")
        row.prop(settings, "padding", text="Pad")

        # Mode-specific: samples
        mode_id = settings.bake_mode
        if mode_id == 'BATCH' or (mode_id in BAKE_MODES and BAKE_MODES[mode_id].use_samples):
            layout.prop(settings, "samples")

        # AA and color
        row = layout.row(align=True)
        row.prop(settings, "aa_override", text="AA")
        row.prop(settings, "color_space", text="")

        layout.prop(settings, "background_color", text="BG")
        layout.prop(settings, "save_to_disk")

        # Batch map selection when in Batch mode
        if settings.bake_mode == 'BATCH':
            box = layout.box()
            row = box.row(align=True)
            row.prop(settings, "batch_normal", toggle=True)
            row.prop(settings, "batch_ao", toggle=True)
            row.prop(settings, "batch_combined", toggle=True)
            row = box.row(align=True)
            row.prop(settings, "batch_base_color", toggle=True)
            row.prop(settings, "batch_roughness", toggle=True)
            row.prop(settings, "batch_metallic", toggle=True)
            row = box.row(align=True)
            row.prop(settings, "batch_emit", toggle=True)

        layout.separator()

        # Device and grouping
        prefs = context.preferences.addons[__package__.rsplit('.', 1)[0]].preferences
        # Only show device selector if a GPU compute device is available
        cycles_prefs = context.preferences.addons.get('cycles')
        if cycles_prefs and cycles_prefs.preferences.compute_device_type != 'NONE':
            layout.prop(prefs, "bake_device", text="Device")
        layout.prop(settings, "force_mode", text="Grouping")
        layout.prop(settings, "tile_repeat", text="Tiling")

        # Bake button
        if settings.bake_mode == 'BATCH':
            batch_props = ['batch_normal', 'batch_ao', 'batch_combined',
                           'batch_base_color', 'batch_roughness', 'batch_metallic',
                           'batch_emit']
            count = sum(1 for p in batch_props if getattr(settings, p))
            label = f"Batch Bake ({count} map{'s' if count != 1 else ''})"
        elif settings.force_mode == 'MULTIRES':
            obj = context.view_layer.objects.active
            has_multires = obj and obj.type == 'MESH' and any(
                m.type == 'MULTIRES' for m in obj.modifiers
            )
            label = "Bake Multires" if has_multires else "Bake (no Multires)"
        else:
            sets = get_bake_sets(context, settings.force_mode)
            active_sets = [s for s in sets if s.objects_low]
            set_count = len(active_sets)
            label = f"Bake ({set_count} set{'s' if set_count != 1 else ''})"

        row = layout.row()
        row.scale_y = 1.5
        row.operator(
            "bake_turbo.bake",
            text=label,
            icon='RENDER_STILL',
        )

    def _draw_trimsheet(self, context, layout):
        trim = context.scene.bake_turbo_trim

        # Trimsheet selector
        if len(trim.trimsheets) > 0:
            ts = trim.get_active_trimsheet()
            row = layout.row(align=True)
            row.prop(ts, "name", text="")
            row.operator("bake_turbo.add_trimsheet", text="", icon='ADD')
            row.operator("bake_turbo.remove_trimsheet", text="", icon='REMOVE')
        else:
            layout.operator("bake_turbo.add_trimsheet", text="New Trimsheet", icon='ADD')
            return

        ts = trim.get_active_trimsheet()
        if ts is None:
            return

        # Navigate between trimsheets if multiple
        if len(trim.trimsheets) > 1:
            layout.prop(trim, "active_trimsheet_index", text="Sheet")

        layout.separator()

        # Region list
        row = layout.row()
        row.template_list(
            "BT_UL_TrimRegions", "",
            ts, "regions",
            ts, "active_region_index",
            rows=3,
        )

        col = row.column(align=True)
        col.operator("bake_turbo.capture_trim_region", text="", icon='ADD')
        col.operator("bake_turbo.remove_trim_region", text="", icon='REMOVE')
        col.separator()
        op = col.operator("bake_turbo.move_trim_region", text="", icon='TRIA_UP')
        op.direction = -1
        op = col.operator("bake_turbo.move_trim_region", text="", icon='TRIA_DOWN')
        op.direction = 1

        layout.separator()

        # Fit mode
        layout.prop(trim, "fit_mode", text="Fit")

        # Assign buttons
        region = trim.get_active_region()
        region_label = f" '{region.name}'" if region else ""

        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("bake_turbo.assign_trim",
                     text="Assign on Faces", icon='UV_DATA')
        col.operator("bake_turbo.convert_to_trim_path",
                     text="Assign on Path", icon='CURVE_PATH')

        # Post-assignment tools
        row = layout.row(align=True)
        op = row.operator("bake_turbo.trim_action", text="Mirror", icon='MOD_MIRROR')
        op.action = 'MIRROR'
        op = row.operator("bake_turbo.trim_action", text="Rotate", icon='FILE_REFRESH')
        op.action = 'ROTATE'
        op = row.operator("bake_turbo.trim_action", text="90°", icon='FILE_REFRESH')
        op.action = 'ROTATE_90'

        # UV Snapshot section
        layout.separator()
        box = layout.box()
        box.label(text="UV Snapshot", icon='SCREEN_BACK')

        obj = context.active_object
        if obj and obj.type == 'MESH':
            snap = obj.bake_turbo_uv_snapshot
            if snap.source_object is not None:
                box.label(text=f"Snapshot: {snap.source_object.name}", icon='OBJECT_DATA')
                box.operator("bake_turbo.restore_uvs", text="Restore UVs", icon='LOOP_BACK')
            else:
                box.operator("bake_turbo.save_uvs", text="Save UVs", icon='FILE_TICK')
        else:
            col = box.column()
            col.enabled = False
            col.label(text="Select a mesh object")


# --- Sub-panels (only visible in Bake mode) ---

class BT_PT_BakeSets(bpy.types.Panel):
    bl_label = "Bake Sets"
    bl_idname = "BT_PT_BakeSets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"
    bl_parent_id = "BT_PT_BakeMain"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene.bake_turbo.panel_mode == 'BAKE'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo
        sets = get_bake_sets(context, settings.force_mode)

        if not sets:
            layout.label(text="No objects found", icon='INFO')
            return

        for bset in sets:
            box = layout.box()
            row = box.row()
            row.label(text=bset.name, icon='OBJECT_DATA')

            if bset.objects_low:
                row = box.row()
                row.label(text=f"  Low: {len(bset.objects_low)}", icon='MESH_DATA')
            if bset.objects_high:
                row = box.row()
                row.label(text=f"  High: {len(bset.objects_high)}", icon='MESH_DATA')
            if bset.objects_cage:
                row = box.row()
                row.label(text=f"  Cage: {len(bset.objects_cage)}", icon='MESH_CUBE')
            if bset.objects_float:
                row = box.row()
                row.label(text=f"  Float: {len(bset.objects_float)}", icon='MESH_CIRCLE')


class BT_PT_HighPoly(bpy.types.Panel):
    bl_label = "High Poly Settings"
    bl_idname = "BT_PT_HighPoly"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"
    bl_parent_id = "BT_PT_BakeMain"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.bake_turbo
        if settings.panel_mode != 'BAKE':
            return False
        if settings.force_mode == 'MULTIRES':
            return False
        if settings.force_mode == 'SELECTION':
            return True
        sets = get_bake_sets(context, settings.force_mode)
        return any(bs.objects_high for bs in sets)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo
        layout.prop(settings, "cage_extrusion")
        layout.prop(settings, "ray_distance")


# --- UV Editor panel ---

class BT_PT_TrimsheetUV(bpy.types.Panel):
    bl_label = "Trim Sheet Regions"
    bl_idname = "BT_PT_TrimsheetUV"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Bake"

    def draw(self, context):
        layout = self.layout
        trim = context.scene.bake_turbo_trim

        # Trimsheet selector
        if len(trim.trimsheets) == 0:
            layout.operator("bake_turbo.add_trimsheet", text="New Trimsheet", icon='ADD')
            return

        ts = trim.get_active_trimsheet()
        row = layout.row(align=True)
        row.prop(ts, "name", text="")
        row.operator("bake_turbo.add_trimsheet", text="", icon='ADD')
        row.operator("bake_turbo.remove_trimsheet", text="", icon='REMOVE')

        # Navigate between trimsheets
        if len(trim.trimsheets) > 1:
            row = layout.row(align=True)
            row.prop(trim, "active_trimsheet_index", text="Sheet")

        layout.separator()

        # Draw and select tools
        row = layout.row(align=True)
        row.operator("bake_turbo.draw_trim_region", text="Draw Region", icon='GREASEPENCIL')
        row.operator("bake_turbo.select_trim_region", text="Select", icon='RESTRICT_SELECT_OFF')

        layout.separator()

        # Region list
        if ts and len(ts.regions) > 0:
            row = layout.row()
            row.template_list(
                "BT_UL_TrimRegions", "uv",
                ts, "regions",
                ts, "active_region_index",
                rows=3,
            )
            col = row.column(align=True)
            col.operator("bake_turbo.remove_trim_region", text="", icon='REMOVE')
            col.separator()
            op = col.operator("bake_turbo.move_trim_region", text="", icon='TRIA_UP')
            op.direction = -1
            op = col.operator("bake_turbo.move_trim_region", text="", icon='TRIA_DOWN')
            op.direction = 1


classes = (
    BT_UL_TrimRegions,
    BT_PT_BakeMain,
    BT_PT_BakeSets,
    BT_PT_HighPoly,
    BT_PT_TrimsheetUV,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
