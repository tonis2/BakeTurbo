"""Bake Turbo operators."""

from __future__ import annotations

import bpy

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
        if settings.force_mode == 'MULTIRES':
            obj = context.view_layer.objects.active
            if not obj or obj.type != 'MESH':
                cls.poll_message_set("No active mesh object")
                return False
            if not any(m.type == 'MULTIRES' for m in obj.modifiers):
                cls.poll_message_set("Active object has no Multiresolution modifier")
                return False
            return True
        sets = get_bake_sets(context, settings.force_mode)
        if not any(bs.objects_low for bs in sets):
            cls.poll_message_set("No bakeable objects found")
            return False
        return True

    def execute(self, context):
        success = run_bake(context, self)
        return {'FINISHED'} if success else {'CANCELLED'}


classes = (BT_OT_Bake,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
