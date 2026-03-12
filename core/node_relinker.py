"""Relink Principled BSDF sockets for PBR extraction bakes."""

from __future__ import annotations

import bpy

from ..modes import RelinkSpec


def find_principled_bsdf(node_tree: bpy.types.NodeTree) -> bpy.types.ShaderNodeBsdfPrincipled | None:
    """Find the first Principled BSDF node, searching group nodes one level deep."""
    for node in node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    # Search inside group nodes
    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            for inner in node.node_tree.nodes:
                if inner.type == 'BSDF_PRINCIPLED':
                    return inner
    return None


def relink_for_bake(material: bpy.types.Material, spec: RelinkSpec) -> bool:
    """Relink Principled BSDF: pipe source_socket value/link into target_socket.

    Returns True if relinking was performed, False if no Principled BSDF found.
    """
    if not material.use_nodes or not material.node_tree:
        return False

    bsdf = find_principled_bsdf(material.node_tree)
    if bsdf is None:
        return False

    tree = material.node_tree
    src_input = bsdf.inputs.get(spec.source_socket)
    tgt_input = bsdf.inputs.get(spec.target_socket)

    if src_input is None or tgt_input is None:
        return False

    # Remove existing links to target
    for link in list(tree.links):
        if link.to_socket == tgt_input:
            tree.links.remove(link)

    # If source has an incoming link, reconnect it to target
    src_link = None
    for link in tree.links:
        if link.to_socket == src_input:
            src_link = link
            break

    if src_link:
        tree.links.new(src_link.from_socket, tgt_input)
    else:
        # Copy default value
        _copy_socket_value(src_input, tgt_input)

    return True


def zero_emission(material: bpy.types.Material):
    """Zero out emission so it doesn't bleed into non-emission bakes."""
    if not material.use_nodes or not material.node_tree:
        return
    bsdf = find_principled_bsdf(material.node_tree)
    if bsdf is None:
        return
    tree = material.node_tree
    em_str = bsdf.inputs.get("Emission Strength")
    if em_str:
        for link in list(tree.links):
            if link.to_socket == em_str:
                tree.links.remove(link)
        em_str.default_value = 0.0
    em_col = bsdf.inputs.get("Emission Color")
    if em_col:
        for link in list(tree.links):
            if link.to_socket == em_col:
                tree.links.remove(link)
        em_col.default_value = (0.0, 0.0, 0.0, 1.0)


def zero_alpha(material: bpy.types.Material):
    """Set alpha to 1.0 so it doesn't affect bake."""
    if not material.use_nodes or not material.node_tree:
        return
    bsdf = find_principled_bsdf(material.node_tree)
    if bsdf is None:
        return
    tree = material.node_tree
    alpha = bsdf.inputs.get("Alpha")
    if alpha:
        for link in list(tree.links):
            if link.to_socket == alpha:
                tree.links.remove(link)
        alpha.default_value = 1.0


def zero_transmission(material: bpy.types.Material):
    """Zero out transmission weight."""
    if not material.use_nodes or not material.node_tree:
        return
    bsdf = find_principled_bsdf(material.node_tree)
    if bsdf is None:
        return
    tree = material.node_tree
    tw = bsdf.inputs.get("Transmission Weight")
    if tw:
        for link in list(tree.links):
            if link.to_socket == tw:
                tree.links.remove(link)
        tw.default_value = 0.0


def setup_emission_for_relink(material: bpy.types.Material):
    """Set emission strength to 1.0 so relinked emission color is visible."""
    if not material.use_nodes or not material.node_tree:
        return
    bsdf = find_principled_bsdf(material.node_tree)
    if bsdf is None:
        return
    tree = material.node_tree
    em_str = bsdf.inputs.get("Emission Strength")
    if em_str:
        for link in list(tree.links):
            if link.to_socket == em_str:
                tree.links.remove(link)
        em_str.default_value = 1.0


def _copy_socket_value(src, dst):
    """Copy the default_value from one socket to another, handling type differences."""
    try:
        if hasattr(src, 'default_value') and hasattr(dst, 'default_value'):
            src_val = src.default_value
            # Float -> Color: broadcast
            if isinstance(src_val, float) and len(getattr(dst, 'default_value', ())) >= 3:
                dst.default_value = (src_val, src_val, src_val, 1.0)
            # Color -> Float: luminance
            elif hasattr(src_val, '__len__') and len(src_val) >= 3 and isinstance(dst.default_value, float):
                dst.default_value = 0.2126 * src_val[0] + 0.7152 * src_val[1] + 0.0722 * src_val[2]
            else:
                dst.default_value = src_val
    except (TypeError, AttributeError):
        pass
