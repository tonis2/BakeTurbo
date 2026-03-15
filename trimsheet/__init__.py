"""Trim sheet subpackage — region definition, UV mapping, and overlays."""

from . import properties, operators, uv_operators, uv_draw


def register():
    properties.register()
    operators.register()
    uv_operators.register()
    uv_draw.register()


def unregister():
    uv_draw.unregister()
    uv_operators.unregister()
    operators.unregister()
    properties.unregister()
