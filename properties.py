import bpy
from bpy.props import (
    EnumProperty, IntProperty, FloatProperty, FloatVectorProperty,
    BoolProperty, StringProperty,
)

from .modes import BAKE_MODES


def _bake_mode_items(self, context):
    items = []
    for cat_label, cat_key in [("Standard", "standard"), ("PBR", "pbr")]:
        items.append(("", cat_label, ""))  # separator / header
        for mode_id, mode in BAKE_MODES.items():
            if mode.category == cat_key:
                items.append((mode_id, mode.name, "", len(items)))
    return items


class BakeTurboSettings(bpy.types.PropertyGroup):
    bake_mode: EnumProperty(
        name="Bake Mode",
        items=_bake_mode_items,
    )

    image_size: EnumProperty(
        name="Size",
        items=[
            ('128', "128", ""),
            ('256', "256", ""),
            ('512', "512", ""),
            ('1024', "1024", ""),
            ('2048', "2048", ""),
            ('4096', "4096", ""),
            ('8192', "8192", ""),
        ],
        default='1024',
    )

    padding: IntProperty(
        name="Padding",
        min=0, max=128,
        default=16,
    )

    samples: IntProperty(
        name="Samples",
        min=1, max=4096,
        default=64,
    )

    ray_distance: FloatProperty(
        name="Ray Distance",
        min=0.0,
        default=0.0,
        precision=4,
    )

    cage_extrusion: FloatProperty(
        name="Cage Extrusion",
        min=0.0,
        default=0.0,
        precision=4,
    )

    aa_override: EnumProperty(
        name="Anti-Aliasing",
        items=[
            ('1', "None", ""),
            ('2', "2x", ""),
            ('4', "4x", ""),
        ],
        default='1',
    )

    color_space: EnumProperty(
        name="Color Space",
        items=[
            ('AUTO', "Auto (from mode)", ""),
            ('sRGB', "sRGB", ""),
            ('Non-Color', "Non-Color", ""),
        ],
        default='AUTO',
    )

    background_color: FloatVectorProperty(
        name="Background",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.0, 0.0, 0.0, 0.0),
    )

    tile_repeat: FloatProperty(
        name="Tile Repeat",
        description="Repeat the baked texture this many times (1 = no tiling)",
        min=1.0,
        default=1.0,
        precision=1,
    )

    target_image: StringProperty(
        name="Target Image",
        description="Image name to bake into. Pick existing or type a new name to create. Leave empty to auto-create",
    )

    save_to_disk: BoolProperty(
        name="Save",
        description="Save baked image to textures/ folder on disk",
        default=True,
    )

    panel_mode: EnumProperty(
        name="Panel Mode",
        items=[
            ('BAKE', "Bake", "Texture baking tools"),
            ('TRIMSHEET', "Trim Sheet", "Trim sheet region mapping"),
        ],
        default='BAKE',
    )

    force_mode: EnumProperty(
        name="Force Mode",
        items=[
            ('NONE', "Auto", "Group by naming convention"),
            ('SELECTION', "Selection", "Active object = target, other selected = source"),
            ('MULTIRES', "Multires", "Bake sculpted detail from Multiresolution modifier"),
            ('SINGLE', "Single Object", "Bake each object independently"),
        ],
        default='SELECTION',
    )


classes = (BakeTurboSettings,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bake_turbo = bpy.props.PointerProperty(type=BakeTurboSettings)


def unregister():
    del bpy.types.Scene.bake_turbo
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
