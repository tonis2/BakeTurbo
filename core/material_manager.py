"""Non-destructive material copy/restore and bake node setup."""

from __future__ import annotations

import bpy


def ensure_materials(objects: list[bpy.types.Object]):
    """Ensure every object has at least one material with a node tree and a UV map."""
    for obj in objects:
        # Ensure UV map exists for baking
        if obj.type == 'MESH' and obj.data.uv_layers.active is None:
            obj.data.uv_layers.new(name="UVMap")

        if not obj.material_slots:
            mat = bpy.data.materials.new(name=f"{obj.name}_BakeMat")
            mat.use_nodes = True
            obj.data.materials.append(mat)
        else:
            for slot in obj.material_slots:
                if not slot.material:
                    mat = bpy.data.materials.new(name=f"{obj.name}_BakeMat")
                    mat.use_nodes = True
                    slot.material = mat


def copy_materials(objects: list[bpy.types.Object]) -> dict[bpy.types.Object, list[bpy.types.Material | None]]:
    """Replace each material slot with a copy. Returns mapping to originals for restore."""
    originals: dict[bpy.types.Object, list[bpy.types.Material | None]] = {}

    for obj in objects:
        orig_list = []
        for i, slot in enumerate(obj.material_slots):
            mat = slot.material
            orig_list.append(mat)
            if mat:
                copy = mat.copy()
                slot.material = copy
        originals[obj] = orig_list

    return originals


def restore_materials(originals: dict[bpy.types.Object, list[bpy.types.Material | None]]):
    """Restore original materials and clean up copies."""
    for obj, mats in originals.items():
        for i, orig_mat in enumerate(mats):
            if i < len(obj.material_slots):
                copy = obj.material_slots[i].material
                obj.material_slots[i].material = orig_mat
                # Remove the copy
                if copy and copy.users == 0:
                    bpy.data.materials.remove(copy)


def setup_bake_node(material: bpy.types.Material, image: bpy.types.Image) -> bpy.types.ShaderNodeTexImage | None:
    """Create an Image Texture node set as the active bake target.

    Returns the created node, or None if the material has no node tree.
    """
    if not material.use_nodes or not material.node_tree:
        return None

    tree = material.node_tree
    node = tree.nodes.new('ShaderNodeTexImage')
    node.name = "BakeTurbo_Target"
    node.label = "Bake Target"
    node.image = image
    node.location = (400, 0)

    # Make it the active (selected) node — Blender bakes to the active image node
    tree.nodes.active = node
    node.select = True

    return node


def remove_bake_nodes(material: bpy.types.Material):
    """Remove all bake target nodes from a material."""
    if not material.use_nodes or not material.node_tree:
        return
    tree = material.node_tree
    to_remove = [n for n in tree.nodes if n.name == "BakeTurbo_Target"]
    for n in to_remove:
        tree.nodes.remove(n)


def connect_bake_result(material, image, mode):
    """Connect a baked image to the material's Principled BSDF."""
    if not material.use_nodes or not material.node_tree:
        return

    tree = material.node_tree
    principled = None
    for node in tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled = node
            break
    if not principled:
        return

    # Find or create the image texture node for this bake result
    tex_node = None
    for node in tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image == image:
            tex_node = node
            break
    if not tex_node:
        tex_node = tree.nodes.new('ShaderNodeTexImage')
        tex_node.image = image

    if mode.blender_mode == 'NORMAL':
        image.colorspace_settings.name = 'Non-Color'
        # Find or create Normal Map node
        normal_node = None
        for node in tree.nodes:
            if node.type == 'NORMAL_MAP':
                normal_node = node
                break
        if not normal_node:
            normal_node = tree.nodes.new('ShaderNodeNormalMap')
            normal_node.location = (principled.location[0] - 200, principled.location[1] - 300)

        tex_node.location = (normal_node.location[0] - 300, normal_node.location[1])
        tree.links.new(tex_node.outputs['Color'], normal_node.inputs['Color'])
        tree.links.new(normal_node.outputs['Normal'], principled.inputs['Normal'])
    else:
        # For other modes, connect directly to a matching input
        input_map = {
            'ROUGHNESS': 'Roughness',
            'EMIT': 'Emission Color',
            'DIFFUSE': 'Base Color',
            'AO': 'Base Color',
        }
        input_name = input_map.get(mode.blender_mode)
        if input_name and input_name in principled.inputs:
            tex_node.location = (principled.location[0] - 300, principled.location[1] - 200)
            tree.links.new(tex_node.outputs['Color'], principled.inputs[input_name])
