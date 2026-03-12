"""Bake Turbo — Professional texture baking toolkit for Blender 5.0+"""

bl_info = {
    "name": "Bake Turbo",
    "author": "Tonis",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Bake",
    "description": "Professional texture baking toolkit",
    "category": "Baking",
}

from . import preferences, properties, ui


def register():
    preferences.register()
    properties.register()
    ui.register()


def unregister():
    ui.unregister()
    properties.unregister()
    preferences.unregister()
