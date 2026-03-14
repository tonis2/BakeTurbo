"""Standard Blender bake modes — passed directly to bpy.ops.object.bake(type=...)."""

from __future__ import annotations

from .types import BakeMode

STANDARD_MODES: dict[str, BakeMode] = {
    "ao": BakeMode("AO", "ao", "AO", "standard", use_samples=True),
    "normal": BakeMode("Normal", "normal", "NORMAL", "standard"),
    "shadow": BakeMode("Shadow", "shadow", "SHADOW", "standard", use_samples=True),
    "combined": BakeMode("Lighting", "combined", "COMBINED", "standard", use_samples=True),
    "diffuse": BakeMode("Diffuse", "diffuse", "DIFFUSE", "standard", color_space="sRGB"),
    "roughness": BakeMode("Roughness", "roughness", "ROUGHNESS", "standard"),
    "glossy": BakeMode("Glossy", "glossy", "GLOSSY", "standard"),
    "emit": BakeMode("Emit", "emit", "EMIT", "standard", color_space="sRGB"),
    "environment": BakeMode("Environment", "environment", "ENVIRONMENT", "standard", color_space="sRGB"),
    "transmission_std": BakeMode("Transmission", "transmission_std", "TRANSMISSION", "standard"),
}
