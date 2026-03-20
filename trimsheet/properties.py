"""Trim sheet data model: PropertyGroups for trim sheets, regions, and settings."""

import bpy


class BT_UVCoord(bpy.types.PropertyGroup):
    uv: bpy.props.FloatVectorProperty(size=2)  # type: ignore


class BT_TrimRegion(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Region")  # type: ignore
    uv_coords: bpy.props.CollectionProperty(type=BT_UVCoord)  # type: ignore
    color: bpy.props.FloatVectorProperty(  # type: ignore
        name="Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.8, 0.8, 0.8),
    )

    def set_uv_coords(self, coords):
        self.uv_coords.clear()
        for coord in coords:
            item = self.uv_coords.add()
            item.uv = coord[:2]

    def get_uv_coords(self):
        return [tuple(c.uv) for c in self.uv_coords]


class BT_Trimsheet(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Trimsheet")  # type: ignore
    regions: bpy.props.CollectionProperty(type=BT_TrimRegion)  # type: ignore
    active_region_index: bpy.props.IntProperty(name="Active Region", default=0)  # type: ignore

    def add_region(self, name, uv_coords):
        region = self.regions.add()
        region.name = name
        region.set_uv_coords(uv_coords)
        self.active_region_index = len(self.regions) - 1
        return region

    def remove_region(self, index):
        self.regions.remove(index)
        if self.active_region_index >= len(self.regions):
            self.active_region_index = max(0, len(self.regions) - 1)


class BT_TrimsheetSettings(bpy.types.PropertyGroup):
    trimsheets: bpy.props.CollectionProperty(type=BT_Trimsheet)  # type: ignore
    active_trimsheet_index: bpy.props.IntProperty(  # type: ignore
        name="Active Trimsheet", default=0, min=0,
        get=lambda self: min(self.get("active_trimsheet_index", 0),
                             max(0, len(self.trimsheets) - 1)),
        set=lambda self, v: self.__setitem__(
            "active_trimsheet_index",
            max(0, min(v, len(self.trimsheets) - 1))),
    )
    fit_mode: bpy.props.EnumProperty(  # type: ignore
        name="Fit",
        items=[
            ('FILL', "Fill", "Stretch UVs using MVC to fill the trim region shape"),
            ('FIT', "Fit", "Scale uniformly to fit inside the trim region"),
            ('FIT_X', "Fit X", "Scale to match trim width"),
            ('FIT_Y', "Fit Y", "Scale to match trim height"),
        ],
        default='FIT',
    )

    def get_active_trimsheet(self):
        idx = self.active_trimsheet_index
        if 0 <= idx < len(self.trimsheets):
            return self.trimsheets[idx]
        return None

    def get_active_region(self):
        ts = self.get_active_trimsheet()
        if ts is None:
            return None
        idx = ts.active_region_index
        if 0 <= idx < len(ts.regions):
            return ts.regions[idx]
        return None


class BT_UVSnapshot(bpy.types.PropertyGroup):
    source_object: bpy.props.PointerProperty(  # type: ignore
        type=bpy.types.Object,
        name="Snapshot Object",
        description="Hidden duplicate storing original UVs",
    )
    original_name: bpy.props.StringProperty(  # type: ignore
        name="Original Name",
        description="Name of the mesh when the snapshot was taken",
    )


classes = (BT_UVCoord, BT_TrimRegion, BT_Trimsheet, BT_TrimsheetSettings, BT_UVSnapshot)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bake_turbo_trim = bpy.props.PointerProperty(type=BT_TrimsheetSettings)
    bpy.types.Object.bake_turbo_uv_snapshot = bpy.props.PointerProperty(type=BT_UVSnapshot)


def unregister():
    del bpy.types.Object.bake_turbo_uv_snapshot
    del bpy.types.Scene.bake_turbo_trim
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
