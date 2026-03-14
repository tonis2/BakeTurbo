"""Bake Turbo operators."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty

from ..core.bake_engine import run_bake
from ..core.bake_sets import get_bake_sets


class BT_OT_Bake(bpy.types.Operator):
    bl_idname = "bake_turbo.bake"
    bl_label = "Bake"
    bl_description = "Bake textures using current settings"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            cls.poll_message_set("Must be in Object mode")
            return False
        settings = context.scene.bake_turbo
        sets = get_bake_sets(context, settings.force_mode)
        if not any(bs.objects_low for bs in sets):
            cls.poll_message_set("No bakeable objects found")
            return False
        return True

    def execute(self, context):
        settings = context.scene.bake_turbo

        if settings.bake_mode == 'BATCH':
            return self._batch_bake(context, settings)

        success = run_bake(context, self)
        return {'FINISHED'} if success else {'CANCELLED'}

    def _batch_bake(self, context, settings):
        batch_map = [
            ('batch_normal', 'normal'),
            ('batch_ao', 'ao'),
            ('batch_combined', 'combined'),
            ('batch_base_color', 'base_color'),
            ('batch_roughness', 'roughness'),
            ('batch_metallic', 'metallic'),
            ('batch_emit', 'emit'),
        ]

        modes_to_bake = [
            mode_id for prop, mode_id in batch_map
            if getattr(settings, prop, False)
        ]

        if not modes_to_bake:
            self.report({'ERROR'}, "No map types selected for batch bake")
            return {'CANCELLED'}

        original_mode = settings.bake_mode
        baked = []
        failed = []

        for mode_id in modes_to_bake:
            settings.bake_mode = mode_id
            success = run_bake(context, self)
            if success:
                baked.append(mode_id)
            else:
                failed.append(mode_id)

        settings.bake_mode = original_mode

        if failed:
            self.report({'WARNING'},
                f"Batch bake: {len(baked)} done, {len(failed)} failed ({', '.join(failed)})")
        else:
            self.report({'INFO'}, f"Batch bake complete: {', '.join(baked)}")

        return {'FINISHED'} if baked else {'CANCELLED'}


class BT_OT_SelectObjectsByType(bpy.types.Operator):
    bl_idname = "bake_turbo.select_by_type"
    bl_label = "Select Objects by Type"
    bl_description = "Select all objects of a specific role in bake sets"
    bl_options = {'REGISTER', 'UNDO'}

    object_type: StringProperty(
        name="Type",
        description="Object role to select: low, high, cage, float",
        default="low",
    )

    def execute(self, context):
        settings = context.scene.bake_turbo
        sets = get_bake_sets(context, settings.force_mode)

        bpy.ops.object.select_all(action='DESELECT')

        count = 0
        for bset in sets:
            objs = {
                "low": bset.objects_low,
                "high": bset.objects_high,
                "cage": bset.objects_cage,
                "float": bset.objects_float,
            }.get(self.object_type, [])
            for obj in objs:
                obj.select_set(True)
                count += 1

        self.report({'INFO'}, f"Selected {count} {self.object_type} object(s)")
        return {'FINISHED'}


classes = (BT_OT_Bake, BT_OT_SelectObjectsByType)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
