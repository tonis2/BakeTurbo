"""Icon loading for Bake Turbo. Uses built-in Blender icons for now."""

from __future__ import annotations

import os
import bpy.utils.previews

_preview_collections: dict[str, bpy.utils.previews.ImagePreviewCollection] = {}


def register():
    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
    if os.path.isdir(icons_dir):
        for filename in os.listdir(icons_dir):
            if filename.endswith(".png"):
                name = os.path.splitext(filename)[0]
                pcoll.load(name, os.path.join(icons_dir, filename), 'IMAGE')
    _preview_collections["main"] = pcoll


def unregister():
    for pcoll in _preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    _preview_collections.clear()


def get_icon_id(name: str) -> int:
    pcoll = _preview_collections.get("main")
    if pcoll and name in pcoll:
        return pcoll[name].icon_id
    return 0
