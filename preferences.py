import bpy
from bpy.props import (
    EnumProperty, BoolProperty, FloatVectorProperty, StringProperty,
)


class BakeTurboPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    bake_device: EnumProperty(
        name="Bake Device",
        items=[
            ('GPU', "GPU Compute", ""),
            ('CPU', "CPU", ""),
        ],
        default='GPU',
    )

    use_float32: BoolProperty(
        name="32-bit Float Images",
        default=False,
    )

    default_background: FloatVectorProperty(
        name="Default Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 0.0),
    )

    default_color_space: EnumProperty(
        name="Default Color Space",
        items=[
            ('sRGB', "sRGB", ""),
            ('Non-Color', "Non-Color", ""),
        ],
        default='sRGB',
    )

    normal_y_swizzle: EnumProperty(
        name="Normal Y",
        items=[
            ('POSITIVE_Y', "+Y (OpenGL)", ""),
            ('NEGATIVE_Y', "-Y (DirectX)", ""),
        ],
        default='POSITIVE_Y',
    )

    auto_detect_high_poly: BoolProperty(
        name="Auto-detect High Poly by Modifiers",
        default=False,
    )

    ignore_alpha: BoolProperty(
        name="Ignore Alpha Channel",
        description="Treat alpha as 1.0 during bake",
        default=False,
    )

    ignore_emission: BoolProperty(
        name="Ignore Emission for Non-Emission Bakes",
        default=True,
    )

    clean_transmission: BoolProperty(
        name="Clean Transmission",
        description="Zero out transmission during non-transmission bakes",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bake_device")
        layout.prop(self, "use_float32")
        layout.prop(self, "default_background")
        layout.prop(self, "default_color_space")
        layout.prop(self, "normal_y_swizzle")
        layout.separator()
        layout.prop(self, "auto_detect_high_poly")
        layout.prop(self, "ignore_alpha")
        layout.prop(self, "ignore_emission")
        layout.prop(self, "clean_transmission")


classes = (BakeTurboPreferences,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
