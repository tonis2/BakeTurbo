"""Non-destructive material copy/restore and bake node setup."""

from __future__ import annotations

import bpy


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
