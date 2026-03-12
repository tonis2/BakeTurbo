from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RelinkSpec:
    """Specifies how to relink Principled BSDF sockets for PBR extraction.

    source_socket: Input name to read from (e.g. "Base Color")
    target_socket: Input name to pipe the value into (e.g. "Emission Color")
    """
    source_socket: str
    target_socket: str


@dataclass(frozen=True)
class BakeMode:
    name: str               # Display name
    id: str                 # Internal identifier
    blender_mode: str       # bpy.ops.object.bake(type=...)
    category: str           # "standard" or "pbr"
    relink: Optional[RelinkSpec] = None
    use_samples: bool = False       # Whether mode uses custom sample count
    color_space: str = "Non-Color"  # Default color space for baked image
    invert: bool = False            # Post-process: invert result
