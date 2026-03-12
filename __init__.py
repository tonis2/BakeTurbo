"""Bake Turbo — Professional texture baking toolkit for Blender 5.0+"""

_needs_reload = "bpy" in locals()

import bpy

from . import core, modes, preferences, properties, ui

if _needs_reload:
    import importlib
    from .core import bake_sets, image_manager, material_manager, node_relinker, bake_engine
    from .modes import types, standard, pbr
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

    importlib.reload(icons)
    importlib.reload(operators)
    importlib.reload(panels)
    importlib.reload(ui)


def register():
    preferences.register()
    properties.register()
    ui.register()


def unregister():
    ui.unregister()
    properties.unregister()
    preferences.unregister()
