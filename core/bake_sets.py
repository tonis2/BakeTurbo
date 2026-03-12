"""Object grouping by naming convention for bake sets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import bpy

LOW_KEYWORDS = {"low", "lo", "lowpoly"}
HIGH_KEYWORDS = {"high", "hi", "hipoly", "highpoly"}
CAGE_KEYWORDS = {"cage"}
FLOAT_KEYWORDS = {"float", "floater"}

SEPARATORS = re.compile(r"[\s_.\-]")


@dataclass
class BakeSet:
    name: str
    objects_low: list[bpy.types.Object] = field(default_factory=list)
    objects_high: list[bpy.types.Object] = field(default_factory=list)
    objects_cage: list[bpy.types.Object] = field(default_factory=list)
    objects_float: list[bpy.types.Object] = field(default_factory=list)


def _parse_object_name(obj_name: str) -> tuple[str, str | None]:
    """Split object name into (base_name, role).

    Returns the base name (without the role suffix) and the detected role
    ('low', 'high', 'cage', 'float') or None if no role keyword found.
    """
    parts = SEPARATORS.split(obj_name)
    if len(parts) < 2:
        return obj_name, None

    last = parts[-1].lower()
    for keywords, role in [
        (LOW_KEYWORDS, "low"),
        (HIGH_KEYWORDS, "high"),
        (CAGE_KEYWORDS, "cage"),
        (FLOAT_KEYWORDS, "float"),
    ]:
        if last in keywords:
            # Reconstruct base name from all parts except the last
            # Use the original string up to the last separator
            base = obj_name[:obj_name.rfind(parts[-1])].rstrip(" _.-")
            return base, role

    return obj_name, None


def get_bake_sets(context: bpy.types.Context, force_mode: str = 'NONE') -> list[BakeSet]:
    """Build bake sets from visible mesh objects in the scene.

    force_mode:
        'NONE' — group by naming convention
        'SINGLE' — each object becomes its own bake set (low only)
    """
    objects = [
        obj for obj in context.view_layer.objects
        if obj.type == 'MESH' and obj.visible_get()
    ]

    if force_mode == 'SINGLE':
        return [BakeSet(name=obj.name, objects_low=[obj]) for obj in objects]

    if force_mode == 'SELECTION':
        active = context.view_layer.objects.active
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            return []
        if active and active.type == 'MESH' and active in selected:
            high = [obj for obj in selected if obj is not active]
            return [BakeSet(
                name=active.name,
                objects_low=[active],
                objects_high=high,
            )]
        else:
            # No valid active mesh — treat all selected as individual low sets
            return [BakeSet(name=obj.name, objects_low=[obj]) for obj in selected]

    sets_dict: dict[str, BakeSet] = {}

    for obj in objects:
        base, role = _parse_object_name(obj.name)

        if base not in sets_dict:
            sets_dict[base] = BakeSet(name=base)

        bset = sets_dict[base]
        if role == "high":
            bset.objects_high.append(obj)
        elif role == "cage":
            bset.objects_cage.append(obj)
        elif role == "float":
            bset.objects_float.append(obj)
        else:
            # 'low' or no role keyword — treat as low
            bset.objects_low.append(obj)

    return list(sets_dict.values())
