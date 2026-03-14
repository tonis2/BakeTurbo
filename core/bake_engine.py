"""Main bake pipeline orchestrator."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field

import bpy

from ..modes import BakeMode, BAKE_MODES
from .bake_sets import BakeSet, get_bake_sets
from .image_manager import (
    get_or_create_image, create_aa_image, downsample_image,
    invert_image, resolve_color_space,
    handle_circular_dependency, cleanup_temp_image,
)
from .material_manager import (
    ensure_materials, copy_materials, restore_materials,
    setup_bake_node, remove_bake_nodes, connect_bake_result,
)
from .node_relinker import (
    relink_for_bake, zero_emission, zero_alpha, zero_transmission,
    setup_emission_for_relink,
)


@dataclass
class _SavedRenderSettings:
    engine: str = ""
    device: str = ""
    samples: int = 0
    margin_type: str = ""
    margin: int = 0
    use_clear: bool = False
    use_selected_to_active: bool = False
    cage_extrusion: float = 0.0
    max_ray_distance: float = 0.0
    normal_space: str = ""
    normal_r: str = ""
    normal_g: str = ""
    normal_b: str = ""


@contextmanager
def bake_context(context: bpy.types.Context):
    """Context manager that saves and restores render/bake settings."""
    scene = context.scene
    render = scene.render
    cycles = scene.cycles
    bake = render.bake

    saved = _SavedRenderSettings(
        engine=render.engine,
        device=cycles.device if hasattr(cycles, 'device') else 'CPU',
        samples=cycles.samples,
        margin_type=bake.margin_type,
        margin=bake.margin,
        use_clear=bake.use_clear,
        use_selected_to_active=bake.use_selected_to_active,
        cage_extrusion=bake.cage_extrusion,
        max_ray_distance=bake.max_ray_distance,
        normal_space=bake.normal_space,
        normal_r=bake.normal_r,
        normal_g=bake.normal_g,
        normal_b=bake.normal_b,
    )

    try:
        yield saved
    finally:
        render.engine = saved.engine
        if hasattr(cycles, 'device'):
            cycles.device = saved.device
        cycles.samples = saved.samples
        bake.margin_type = saved.margin_type
        bake.margin = saved.margin
        bake.use_clear = saved.use_clear
        bake.use_selected_to_active = saved.use_selected_to_active
        bake.cage_extrusion = saved.cage_extrusion
        bake.max_ray_distance = saved.max_ray_distance
        bake.normal_space = saved.normal_space
        bake.normal_r = saved.normal_r
        bake.normal_g = saved.normal_g
        bake.normal_b = saved.normal_b


def run_bake(context: bpy.types.Context, operator: bpy.types.Operator) -> bool:
    """Execute the full bake pipeline. Returns True on success."""
    scene = context.scene
    settings = scene.bake_turbo
    prefs = context.preferences.addons[__package__.rsplit('.', 1)[0]].preferences

    mode_id = settings.bake_mode
    if mode_id == 'BATCH':
        # Batch is handled by the operator, not here
        operator.report({'ERROR'}, "Batch mode should be handled by the operator")
        return False
    if mode_id not in BAKE_MODES:
        operator.report({'ERROR'}, f"Unknown bake mode: {mode_id}")
        return False

    mode = BAKE_MODES[mode_id]

    # Multires bake path
    if settings.force_mode == 'MULTIRES':
        return _run_multires_bake(context, operator, mode, settings, prefs)

    bake_sets = get_bake_sets(context, settings.force_mode)

    if not bake_sets:
        operator.report({'ERROR'}, "No objects found to bake")
        return False

    # Filter out sets with no low-poly objects
    bake_sets = [bs for bs in bake_sets if bs.objects_low]
    if not bake_sets:
        operator.report({'ERROR'}, "No low-poly objects found in bake sets")
        return False

    aa_factor = int(settings.aa_override)
    base_size = int(settings.image_size)
    color_space = resolve_color_space(mode, settings.color_space)
    use_float = prefs.use_float32

    with bake_context(context) as saved:
        _configure_render(context, settings, prefs, mode)

        for bset in bake_sets:
            success = _bake_set(
                context, operator, mode, bset,
                base_size, aa_factor, color_space, use_float,
                settings, prefs,
            )
            if not success:
                return False

    img_names = [f"{bs.name}_{mode.id}" for bs in bake_sets]
    if settings.save_to_disk:
        operator.report({'INFO'}, f"Bake complete: image '{img_names[0]}' saved to textures/")
    else:
        operator.report({'INFO'}, f"Bake complete: image '{img_names[0]}'")
    return True


def _run_multires_bake(
    context: bpy.types.Context,
    operator: bpy.types.Operator,
    mode: BakeMode,
    settings,
    prefs,
) -> bool:
    """Bake sculpted detail from a Multiresolution modifier."""
    obj = context.view_layer.objects.active
    if not obj or obj.type != 'MESH':
        operator.report({'ERROR'}, "No active mesh object")
        return False

    # Find Multiresolution modifier
    multires = None
    for mod in obj.modifiers:
        if mod.type == 'MULTIRES':
            multires = mod
            break

    if not multires:
        operator.report({'ERROR'}, f"'{obj.name}' has no Multiresolution modifier")
        return False

    if multires.total_levels < 1:
        operator.report({'ERROR'}, "Multiresolution modifier needs at least 1 subdivision level")
        return False

    base_size = int(settings.image_size)
    color_space = resolve_color_space(mode, settings.color_space)
    use_float = prefs.use_float32
    bg = tuple(settings.background_color)

    img_name = f"{obj.name}_{mode.id}"
    bake_image = get_or_create_image(
        img_name, base_size, base_size,
        color_space=color_space, use_float=use_float, background=bg,
    )

    # Ensure material and UV
    ensure_materials([obj])
    mat_originals = copy_materials([obj])

    try:
        for slot in obj.material_slots:
            if slot.material:
                setup_bake_node(slot.material, bake_image)

        # Select only the multires object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        with bake_context(context) as saved:
            _configure_render(context, settings, prefs, mode)

            bake = context.scene.render.bake
            bake.use_multires = True
            bake.use_selected_to_active = False

            try:
                bpy.ops.object.bake(type=mode.blender_mode)
            except RuntimeError as e:
                operator.report({'ERROR'}, f"Multires bake failed: {e}")
                return False

        # Save to disk if enabled
        if settings.save_to_disk:
            import os
            blend_path = bpy.data.filepath
            if blend_path:
                tex_dir = os.path.join(os.path.dirname(blend_path), "textures")
            else:
                tex_dir = os.path.join(os.path.expanduser("~"), "BakeTurbo_textures")
            os.makedirs(tex_dir, exist_ok=True)

            save_path = os.path.join(tex_dir, f"{bake_image.name}.png")
            bake_image.filepath_raw = save_path
            bake_image.file_format = 'PNG'
            bake_image.save()
            bake_image.source = 'FILE'
            bake_image.reload()

    finally:
        restore_materials(mat_originals)

    # Connect result
    tile_repeat = settings.tile_repeat
    for slot in obj.material_slots:
        if slot.material:
            connect_bake_result(slot.material, bake_image, mode, tile_repeat)

    if settings.save_to_disk:
        operator.report({'INFO'}, f"Bake complete: image '{bake_image.name}' saved to textures/")
    else:
        operator.report({'INFO'}, f"Bake complete: image '{bake_image.name}'")
    return True


def _configure_render(
    context: bpy.types.Context,
    settings,
    prefs,
    mode: BakeMode,
):
    """Set up Cycles render settings for baking."""
    scene = context.scene
    scene.render.engine = 'CYCLES'

    if hasattr(scene.cycles, 'device'):
        scene.cycles.device = prefs.bake_device

    if mode.use_samples:
        scene.cycles.samples = settings.samples
    else:
        scene.cycles.samples = 1

    bake = scene.render.bake
    bake.margin_type = 'EXTEND'
    bake.margin = settings.padding
    bake.use_clear = True

    # Normal map settings
    if mode.blender_mode == 'NORMAL':
        bake.normal_space = 'TANGENT'
        y_swizzle = prefs.normal_y_swizzle
        bake.normal_r = 'POS_X'
        bake.normal_g = 'POS_Y' if y_swizzle == 'POSITIVE_Y' else 'NEG_Y'
        bake.normal_b = 'POS_Z'


def _bake_set(
    context: bpy.types.Context,
    operator: bpy.types.Operator,
    mode: BakeMode,
    bset: BakeSet,
    base_size: int,
    aa_factor: int,
    color_space: str,
    use_float: bool,
    settings,
    prefs,
) -> bool:
    """Bake a single bake set. Returns True on success."""
    has_high = bool(bset.objects_high)
    all_low = bset.objects_low + bset.objects_float

    # Ensure all target objects have materials
    ensure_materials(all_low)

    # Image setup
    img_name = f"{bset.name}_{mode.id}"
    bg = tuple(settings.background_color)

    if aa_factor > 1:
        bake_image = create_aa_image(
            img_name, base_size, base_size, aa_factor,
            color_space=color_space, use_float=use_float, background=bg,
        )
    else:
        bake_image = get_or_create_image(
            img_name, base_size, base_size,
            color_space=color_space, use_float=use_float, background=bg,
        )

    # Copy materials for non-destructive editing
    mat_originals = copy_materials(all_low)

    try:
        # Set up bake target node on all low-poly materials
        for obj in all_low:
            for slot in obj.material_slots:
                if slot.material:
                    setup_bake_node(slot.material, bake_image)

        # Handle circular dependency
        temp_image = handle_circular_dependency(all_low, bake_image)

        # PBR relinking
        if mode.relink:
            for obj in all_low:
                for slot in obj.material_slots:
                    if slot.material:
                        relink_for_bake(slot.material, mode.relink)
                        if mode.relink.target_socket == "Emission Color":
                            setup_emission_for_relink(slot.material)

        # Clean up unwanted shader contributions
        if mode.category == "pbr" or mode.blender_mode in ('EMIT', 'ROUGHNESS'):
            for obj in all_low:
                for slot in obj.material_slots:
                    if slot.material:
                        if prefs.ignore_emission and mode.id != "emission_strength":
                            if not mode.relink or mode.relink.target_socket != "Emission Color":
                                zero_emission(slot.material)
                        if prefs.ignore_alpha and mode.id != "alpha":
                            zero_alpha(slot.material)
                        if prefs.clean_transmission and mode.id != "transmission":
                            zero_transmission(slot.material)

        # Selection
        bpy.ops.object.select_all(action='DESELECT')

        bake = context.scene.render.bake

        if has_high:
            bake.use_selected_to_active = True
            bake.cage_extrusion = settings.cage_extrusion
            bake.max_ray_distance = settings.ray_distance

            # Use cage object if available
            cage_obj = bset.objects_cage[0] if bset.objects_cage else None
            if cage_obj:
                bake.use_cage = True
                bake.cage_object = cage_obj
            else:
                bake.use_cage = False

            # Select high-poly objects
            for obj in bset.objects_high:
                obj.select_set(True)
            # Active = low-poly (bake target)
            for obj in all_low:
                obj.select_set(True)
            context.view_layer.objects.active = bset.objects_low[0]
        else:
            bake.use_selected_to_active = False
            for obj in all_low:
                obj.select_set(True)
            context.view_layer.objects.active = all_low[0]

        # Bake
        try:
            bpy.ops.object.bake(type=mode.blender_mode)
        except RuntimeError as e:
            operator.report({'ERROR'}, f"Bake failed for '{bset.name}': {e}")
            return False

        # Post-process
        if mode.invert:
            invert_image(bake_image)

        # AA downsample
        if aa_factor > 1:
            final_image = get_or_create_image(
                img_name, base_size, base_size,
                color_space=color_space, use_float=use_float, background=bg,
            )
            downsample_image(bake_image, final_image, aa_factor)
            # Remove oversized image
            bpy.data.images.remove(bake_image)
            bake_image = final_image

        # Save the image to disk if enabled
        if settings.save_to_disk:
            import os
            blend_path = bpy.data.filepath
            if blend_path:
                tex_dir = os.path.join(os.path.dirname(blend_path), "textures")
            else:
                tex_dir = os.path.join(os.path.expanduser("~"), "BakeTurbo_textures")
            os.makedirs(tex_dir, exist_ok=True)

            save_path = os.path.join(tex_dir, f"{bake_image.name}.png")
            bake_image.filepath_raw = save_path
            bake_image.file_format = 'PNG'
            bake_image.save()
            bake_image.source = 'FILE'
            bake_image.reload()

        cleanup_temp_image(temp_image)

    finally:
        restore_materials(mat_originals)

    # Connect the baked image to the target material
    tile_repeat = settings.tile_repeat
    for obj in bset.objects_low:
        for slot in obj.material_slots:
            if slot.material:
                connect_bake_result(slot.material, bake_image, mode, tile_repeat)

    return True
