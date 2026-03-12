"""PBR extraction modes — relink Principled BSDF sockets, then bake EMIT or ROUGHNESS."""

from __future__ import annotations

from .types import BakeMode, RelinkSpec


def _pbr(name, id, source, target, *, color_space="Non-Color", invert=False):
    blender_mode = "EMIT" if target == "Emission Color" else "ROUGHNESS"
    return id, BakeMode(
        name=name,
        id=id,
        blender_mode=blender_mode,
        category="pbr",
        relink=RelinkSpec(source_socket=source, target_socket=target),
        color_space=color_space,
        invert=invert,
    )


PBR_MODES: dict[str, BakeMode] = dict([
    _pbr("Base Color", "base_color",
         "Base Color", "Emission Color", color_space="sRGB"),
    _pbr("Metallic", "metallic",
         "Metallic", "Roughness"),
    _pbr("Specular", "specular",
         "Specular IOR Level", "Roughness"),
    _pbr("SSS Color", "sss_color",
         "Base Color", "Emission Color", color_space="sRGB"),
    _pbr("SSS Strength", "sss_strength",
         "Subsurface Weight", "Roughness"),
    _pbr("Coat Weight", "coat_weight",
         "Coat Weight", "Roughness"),
    _pbr("Coat Roughness", "coat_roughness",
         "Coat Roughness", "Roughness"),
    _pbr("Alpha", "alpha",
         "Alpha", "Roughness"),
    _pbr("Emission Strength", "emission_strength",
         "Emission Strength", "Roughness"),
    _pbr("Sheen Weight", "sheen",
         "Sheen Weight", "Roughness"),
    _pbr("Sheen Tint", "sheen_tint",
         "Sheen Tint", "Emission Color", color_space="sRGB"),
    _pbr("Specular Tint", "specular_tint",
         "Specular Tint", "Emission Color", color_space="sRGB"),
    _pbr("Anisotropic", "anisotropic",
         "Anisotropic", "Roughness"),
    _pbr("Anisotropic Rotation", "anisotropic_rotation",
         "Anisotropic Rotation", "Roughness"),
    _pbr("Transmission", "transmission",
         "Transmission Weight", "Roughness"),
])
