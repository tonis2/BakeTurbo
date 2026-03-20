"""Trim sheet subpackage — region definition, UV mapping, and overlays."""

from . import properties, operators, uv_operators, uv_draw, trim_path


def register():
    properties.register()
    operators.register()
    uv_operators.register()
    uv_draw.register()
    trim_path.register()


def unregister():
    trim_path.unregister()
    uv_draw.unregister()
    uv_operators.unregister()
    operators.unregister()
    properties.unregister()
