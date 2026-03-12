"""3D Viewport sidebar panels for Bake Turbo."""

from __future__ import annotations

import bpy

from ..modes import BAKE_MODES
from ..core.bake_sets import get_bake_sets


class BT_PT_BakeMain(bpy.types.Panel):
    bl_label = "Bake Turbo"
    bl_idname = "BT_PT_BakeMain"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo

        # Mode selector
        layout.prop(settings, "bake_mode", text="Mode")

        # Image settings
        row = layout.row(align=True)
        row.prop(settings, "image_size", text="Size")
        row.prop(settings, "padding", text="Pad")

        # Mode-specific: samples
        mode_id = settings.bake_mode
        if mode_id in BAKE_MODES and BAKE_MODES[mode_id].use_samples:
            layout.prop(settings, "samples")

        # AA and color
        row = layout.row(align=True)
        row.prop(settings, "aa_override", text="AA")
        row.prop(settings, "color_space", text="")

        layout.prop(settings, "background_color", text="BG")

        layout.separator()

        # Force mode
        layout.prop(settings, "force_mode", text="Grouping")

        # Bake button
        sets = get_bake_sets(context, settings.force_mode)
        active_sets = [s for s in sets if s.objects_low]
        set_count = len(active_sets)

        row = layout.row()
        row.scale_y = 1.5
        row.operator(
            "bake_turbo.bake",
            text=f"Bake ({set_count} set{'s' if set_count != 1 else ''})",
            icon='RENDER_STILL',
        )


class BT_PT_BakeSets(bpy.types.Panel):
    bl_label = "Bake Sets"
    bl_idname = "BT_PT_BakeSets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"
    bl_parent_id = "BT_PT_BakeMain"
    bl_options = {'DEFAULT_CLOSED'}

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
        sets = get_bake_sets(context, settings.force_mode)
        return any(bs.objects_high for bs in sets)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo
        layout.prop(settings, "cage_extrusion")
        layout.prop(settings, "ray_distance")


class BT_PT_Selection(bpy.types.Panel):
    bl_label = "Selection"
    bl_idname = "BT_PT_Selection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bake"
    bl_parent_id = "BT_PT_BakeMain"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bake_turbo

        layout.prop(settings, "freeze_selection")

        row = layout.row(align=True)
        op = row.operator("bake_turbo.select_by_type", text="Low")
        op.object_type = "low"
        op = row.operator("bake_turbo.select_by_type", text="High")
        op.object_type = "high"
        op = row.operator("bake_turbo.select_by_type", text="Cage")
        op.object_type = "cage"
        op = row.operator("bake_turbo.select_by_type", text="Float")
        op.object_type = "float"


classes = (BT_PT_BakeMain, BT_PT_BakeSets, BT_PT_HighPoly, BT_PT_Selection)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
