"""Bake Turbo — Professional texture baking toolkit for Blender 5.0+"""

bl_info = {
    "name": "Bake Turbo",
    "description": "Professional texture baking toolkit",
    "author": "Tonis",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "category": "Render",
}

_needs_reload = "bpy" in locals()

import bpy

from . import core, modes, preferences, properties, trimsheet, ui

if _needs_reload:
    import importlib
    from .core import bake_sets, image_manager, material_manager, node_relinker, bake_engine
    from .modes import types, standard, pbr
    from .trimsheet import (
        math_utils, geometry_2d, unwrap as ts_unwrap,
        properties as ts_properties, engine as ts_engine,
        operators as ts_operators, uv_operators, uv_draw,
        trim_path,
    )
    from .ui import icons, operators, panels

    # Reload bottom-up: leaf modules first
    importlib.reload(bake_sets)
    importlib.reload(image_manager)
    importlib.reload(material_manager)
    importlib.reload(node_relinker)
    importlib.reload(bake_engine)
    importlib.reload(core)

    importlib.reload(types)
    importlib.reload(standard)
    importlib.reload(pbr)
    importlib.reload(modes)

    importlib.reload(preferences)
    importlib.reload(properties)

    importlib.reload(math_utils)
    importlib.reload(geometry_2d)
    importlib.reload(ts_unwrap)
    importlib.reload(ts_engine)
    importlib.reload(ts_properties)
    importlib.reload(ts_operators)
    importlib.reload(uv_operators)
    importlib.reload(uv_draw)
    importlib.reload(trim_path)
    importlib.reload(trimsheet)

    importlib.reload(icons)
    importlib.reload(operators)
    importlib.reload(panels)
    importlib.reload(ui)


def register():
    preferences.register()
    properties.register()
    trimsheet.register()
    ui.register()


def unregister():
    ui.unregister()
    trimsheet.unregister()
    properties.unregister()
    preferences.unregister()
