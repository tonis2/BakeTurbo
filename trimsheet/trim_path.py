"""Trim Path — generate quad-strip geometry along a curve with trim UVs."""

import bpy
from bpy.types import Operator


_DATA_TYPE_TO_SOCKET = {
    'FLOAT': 'NodeSocketFloat',
    'INT': 'NodeSocketInt',
    'FLOAT_VECTOR': 'NodeSocketVector',
    'FLOAT_COLOR': 'NodeSocketColor',
    'BOOLEAN': 'NodeSocketBool',
    'QUATERNION': 'NodeSocketRotation',
}


def _value_socket(node, is_output=False):
    """Get the Value/Attribute socket matching the node's data_type."""
    target = _DATA_TYPE_TO_SOCKET.get(node.data_type, 'NodeSocketFloat')
    sockets = node.outputs if is_output else node.inputs
    for s in sockets:
        if s.name in ('Value', 'Attribute') and s.bl_idname == target:
            return s
    # Fallback: first Value/Attribute socket
    for s in sockets:
        if s.name in ('Value', 'Attribute'):
            return s
    return None


def _add_node(tree, bl_idname, location=(0, 0)):
    node = tree.nodes.new(bl_idname)
    node.location = location
    return node


def _setup_interface(tree):
    """Add modifier input/output sockets to the node group interface."""
    # Geometry I/O (required for geometry nodes modifier)
    tree.interface.new_socket('Geometry', in_out='INPUT',
                              socket_type='NodeSocketGeometry')
    tree.interface.new_socket('Geometry', in_out='OUTPUT',
                              socket_type='NodeSocketGeometry')

    res = tree.interface.new_socket('Resolution', in_out='INPUT',
                                    socket_type='NodeSocketInt')
    res.default_value = 64
    res.min_value = 2

    width = tree.interface.new_socket('Width', in_out='INPUT',
                                      socket_type='NodeSocketFloat')
    width.default_value = 0.05
    width.min_value = 0.001

    offset = tree.interface.new_socket('Surface Offset', in_out='INPUT',
                                       socket_type='NodeSocketFloat')
    offset.default_value = 0.002

    u_min = tree.interface.new_socket('U Min', in_out='INPUT',
                                      socket_type='NodeSocketFloat')
    u_min.default_value = 0.0
    u_max = tree.interface.new_socket('U Max', in_out='INPUT',
                                      socket_type='NodeSocketFloat')
    u_max.default_value = 1.0
    v_min = tree.interface.new_socket('V Min', in_out='INPUT',
                                      socket_type='NodeSocketFloat')
    v_min.default_value = 0.0
    v_max = tree.interface.new_socket('V Max', in_out='INPUT',
                                      socket_type='NodeSocketFloat')
    v_max.default_value = 1.0

    tree.interface.new_socket('Surface Target', in_out='INPUT',
                              socket_type='NodeSocketObject')

    snap = tree.interface.new_socket('Snap to Surface', in_out='INPUT',
                                     socket_type='NodeSocketBool')
    snap.default_value = True

    tree.interface.new_socket('Material', in_out='INPUT',
                              socket_type='NodeSocketMaterial')


def _set_modifier_input(mod, name, value):
    """Set a geometry nodes modifier input by socket name."""
    for item in mod.node_group.interface.items_tree:
        if (hasattr(item, 'in_out') and item.in_out == 'INPUT'
                and item.name == name):
            mod[item.identifier] = value
            return


def _build_core(tree, curves_socket, group_in, group_out, x_off=0):
    """Build the shared pipeline: curves → snap to surface → mesh with UVs."""
    link = tree.links.new
    x = x_off

    # --- Resample curve ---
    resample = _add_node(tree, 'GeometryNodeResampleCurve', (x, 0))
    if hasattr(resample, 'mode'):
        resample.mode = 'COUNT'
    else:
        resample.inputs['Mode'].default_value = 'Count'
    link(curves_socket, resample.inputs['Curve'])
    link(group_in.outputs['Resolution'], resample.inputs['Count'])

    # --- Snap curve points to surface (before curve-to-mesh) ---
    obj_info = _add_node(tree, 'GeometryNodeObjectInfo', (x + 200, -500))
    obj_info.transform_space = 'RELATIVE'
    link(group_in.outputs['Surface Target'], obj_info.inputs['Object'])

    pos_curve = _add_node(tree, 'GeometryNodeInputPosition', (x + 200, -200))

    # Sample nearest position on target surface
    sample_pos = _add_node(tree, 'GeometryNodeSampleNearestSurface', (x + 400, -200))
    sample_pos.data_type = 'FLOAT_VECTOR'
    link(obj_info.outputs['Geometry'], sample_pos.inputs['Mesh'])
    link(pos_curve.outputs['Position'], sample_pos.inputs['Sample Position'])
    pos_tgt = _add_node(tree, 'GeometryNodeInputPosition', (x + 400, -350))
    link(pos_tgt.outputs['Position'], _value_socket(sample_pos))

    # Sample surface normal for offset
    sample_nrm = _add_node(tree, 'GeometryNodeSampleNearestSurface', (x + 400, -500))
    sample_nrm.data_type = 'FLOAT_VECTOR'
    link(obj_info.outputs['Geometry'], sample_nrm.inputs['Mesh'])
    link(pos_curve.outputs['Position'], sample_nrm.inputs['Sample Position'])
    nrm_tgt = _add_node(tree, 'GeometryNodeInputNormal', (x + 400, -650))
    link(nrm_tgt.outputs['Normal'], _value_socket(sample_nrm))

    # Switch: snap or keep original curve positions
    switch_pos = _add_node(tree, 'GeometryNodeSwitch', (x + 600, -200))
    switch_pos.input_type = 'VECTOR'
    link(group_in.outputs['Snap to Surface'], switch_pos.inputs['Switch'])
    link(pos_curve.outputs['Position'], switch_pos.inputs['False'])
    link(_value_socket(sample_pos, is_output=True), switch_pos.inputs['True'])

    # Offset snapped position along surface normal
    nrm_scale = _add_node(tree, 'ShaderNodeVectorMath', (x + 600, -400))
    nrm_scale.operation = 'SCALE'
    link(_value_socket(sample_nrm, is_output=True), nrm_scale.inputs[0])
    link(group_in.outputs['Surface Offset'], nrm_scale.inputs['Scale'])

    # Apply snap + offset to curve points
    set_curve_pos = _add_node(tree, 'GeometryNodeSetPosition', (x + 800, 0))
    link(resample.outputs['Curve'], set_curve_pos.inputs['Geometry'])
    link(switch_pos.outputs['Output'], set_curve_pos.inputs['Position'])
    link(nrm_scale.outputs['Vector'], set_curve_pos.inputs['Offset'])

    # Set curve normal to surface normal so profile lies flat on surface
    set_curve_nrm = _add_node(tree, 'GeometryNodeSetCurveNormal', (x + 1000, 0))
    set_curve_nrm.inputs['Mode'].default_value = 'Minimum Twist'
    link(set_curve_pos.outputs['Geometry'], set_curve_nrm.inputs['Curve'])

    # --- Store path factor ---
    sp_path = _add_node(tree, 'GeometryNodeSplineParameter', (x + 1000, -200))

    store_path = _add_node(tree, 'GeometryNodeStoreNamedAttribute', (x + 1200, 0))
    store_path.data_type = 'FLOAT'
    store_path.domain = 'POINT'
    store_path.inputs['Name'].default_value = "_bt_path_factor"
    link(set_curve_nrm.outputs['Curve'], store_path.inputs['Geometry'])
    link(sp_path.outputs['Factor'], _value_socket(store_path))

    # --- Profile line scaled by Width ---
    line = _add_node(tree, 'GeometryNodeCurvePrimitiveLine', (x + 1000, -500))
    line.mode = 'POINTS'
    line.inputs['Start'].default_value = (-0.5, 0.0, 0.0)
    line.inputs['End'].default_value = (0.5, 0.0, 0.0)

    pos_in = _add_node(tree, 'GeometryNodeInputPosition', (x + 1000, -700))
    vec_scale_w = _add_node(tree, 'ShaderNodeVectorMath', (x + 1200, -700))
    vec_scale_w.operation = 'SCALE'
    link(pos_in.outputs['Position'], vec_scale_w.inputs[0])
    link(group_in.outputs['Width'], vec_scale_w.inputs['Scale'])

    set_pos_prof = _add_node(tree, 'GeometryNodeSetPosition', (x + 1200, -500))
    link(line.outputs['Curve'], set_pos_prof.inputs['Geometry'])
    link(vec_scale_w.outputs['Vector'], set_pos_prof.inputs['Position'])

    # --- Store profile factor ---
    sp_prof = _add_node(tree, 'GeometryNodeSplineParameter', (x + 1400, -700))

    store_prof = _add_node(tree, 'GeometryNodeStoreNamedAttribute', (x + 1400, -500))
    store_prof.data_type = 'FLOAT'
    store_prof.domain = 'POINT'
    store_prof.inputs['Name'].default_value = "_bt_profile_factor"
    link(set_pos_prof.outputs['Geometry'], store_prof.inputs['Geometry'])
    link(sp_prof.outputs['Factor'], _value_socket(store_prof))

    # --- Curve to Mesh ---
    c2m = _add_node(tree, 'GeometryNodeCurveToMesh', (x + 1600, 0))
    c2m.inputs['Fill Caps'].default_value = False
    link(store_path.outputs['Geometry'], c2m.inputs['Curve'])
    link(store_prof.outputs['Geometry'], c2m.inputs['Profile Curve'])

    # --- UV mapping: read factors, map to trim bounds ---
    read_path = _add_node(tree, 'GeometryNodeInputNamedAttribute', (x + 1600, -200))
    read_path.data_type = 'FLOAT'
    read_path.inputs['Name'].default_value = "_bt_path_factor"

    map_u = _add_node(tree, 'ShaderNodeMapRange', (x + 1800, -200))
    link(_value_socket(read_path, is_output=True), map_u.inputs['Value'])
    map_u.inputs['From Min'].default_value = 0.0
    map_u.inputs['From Max'].default_value = 1.0
    link(group_in.outputs['U Min'], map_u.inputs['To Min'])
    link(group_in.outputs['U Max'], map_u.inputs['To Max'])

    read_prof = _add_node(tree, 'GeometryNodeInputNamedAttribute', (x + 1600, -400))
    read_prof.data_type = 'FLOAT'
    read_prof.inputs['Name'].default_value = "_bt_profile_factor"

    map_v = _add_node(tree, 'ShaderNodeMapRange', (x + 1800, -400))
    link(_value_socket(read_prof, is_output=True), map_v.inputs['Value'])
    map_v.inputs['From Min'].default_value = 0.0
    map_v.inputs['From Max'].default_value = 1.0
    link(group_in.outputs['V Min'], map_v.inputs['To Min'])
    link(group_in.outputs['V Max'], map_v.inputs['To Max'])

    combine = _add_node(tree, 'ShaderNodeCombineXYZ', (x + 2000, -300))
    link(map_u.outputs['Result'], combine.inputs['X'])
    link(map_v.outputs['Result'], combine.inputs['Y'])

    # Store as UVMap corner attribute
    store_uv = _add_node(tree, 'GeometryNodeStoreNamedAttribute', (x + 2200, 0))
    store_uv.data_type = 'FLOAT2'
    store_uv.domain = 'CORNER'
    store_uv.inputs['Name'].default_value = "UVMap"
    link(c2m.outputs['Mesh'], store_uv.inputs['Geometry'])
    link(combine.outputs['Vector'], _value_socket(store_uv))

    # --- Remove temporary attributes ---
    rm_path = _add_node(tree, 'GeometryNodeRemoveAttribute', (x + 2400, 0))
    rm_path.inputs['Name'].default_value = "_bt_path_factor"
    link(store_uv.outputs['Geometry'], rm_path.inputs['Geometry'])

    rm_prof = _add_node(tree, 'GeometryNodeRemoveAttribute', (x + 2600, 0))
    rm_prof.inputs['Name'].default_value = "_bt_profile_factor"
    link(rm_path.outputs['Geometry'], rm_prof.inputs['Geometry'])

    # --- Set material ---
    set_mat = _add_node(tree, 'GeometryNodeSetMaterial', (x + 2800, 0))
    link(rm_prof.outputs['Geometry'], set_mat.inputs['Geometry'])
    link(group_in.outputs['Material'], set_mat.inputs['Material'])

    # --- Output ---
    group_out.location = (x + 3000, 0)
    link(set_mat.outputs['Geometry'], group_out.inputs['Geometry'])


def _build_gp_group(tree):
    """Build the Grease Pencil → trim path node group."""
    tree.nodes.clear()
    group_in = _add_node(tree, 'NodeGroupInput', (-400, 0))
    group_out = _add_node(tree, 'NodeGroupOutput', (2800, 0))
    _setup_interface(tree)

    gp2curves = _add_node(tree, 'GeometryNodeGreasePencilToCurves', (0, 0))
    tree.links.new(group_in.outputs['Geometry'], gp2curves.inputs['Grease Pencil'])

    _build_core(tree, gp2curves.outputs['Curves'], group_in, group_out,
                x_off=200)


def _build_curve_group(tree):
    """Build the Curve → trim path node group."""
    tree.nodes.clear()
    group_in = _add_node(tree, 'NodeGroupInput', (-200, 0))
    group_out = _add_node(tree, 'NodeGroupOutput', (2600, 0))
    _setup_interface(tree)

    _build_core(tree, group_in.outputs['Geometry'], group_in, group_out,
                x_off=0)


def _get_or_create_group(name, builder):
    """Return an existing node group or create a new one."""
    ng = bpy.data.node_groups.get(name)
    if ng is not None:
        # Validate that the group has required sockets
        socket_names = {
            item.name for item in ng.interface.items_tree
            if hasattr(item, 'in_out')
        }
        if {'Geometry', 'Surface Target', 'Material'}.issubset(socket_names):
            return ng
        # Rebuild outdated group
        ng.interface.clear()
        builder(ng)
        return ng
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    builder(ng)
    return ng


def _get_or_create_trim_material(trim_settings):
    """Find or create a material using the active trimsheet's image."""
    ts = trim_settings.get_active_trimsheet()
    if ts is None:
        return None

    ts_name = ts.name
    mat_name = f"Trim_{ts_name}"

    # Return existing material if already created
    mat = bpy.data.materials.get(mat_name)
    if mat is not None:
        return mat

    # Search for an image matching the trimsheet name
    trim_img = None
    ts_lower = ts_name.lower().replace(' ', '_')
    for img in bpy.data.images:
        img_base = img.name.rsplit('.', 1)[0] if '.' in img.name else img.name
        if img_base.lower().replace(' ', '_') == ts_lower:
            trim_img = img
            break

    if trim_img is None:
        return None

    # Create material with the trim sheet image
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    principled = tree.nodes.get('Principled BSDF')

    tex_node = tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = trim_img
    tex_node.location = (-300, 300)
    tree.links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

    return mat


def _get_region_uv_bounds(region):
    """Compute AABB of a trim region's UV coordinates."""
    coords = region.get_uv_coords()
    if not coords:
        return 0.0, 1.0, 0.0, 1.0
    us = [c[0] for c in coords]
    vs = [c[1] for c in coords]
    return min(us), max(us), min(vs), max(vs)


class BT_OT_ConvertToTrimPath(Operator):
    bl_idname = "bake_turbo.convert_to_trim_path"
    bl_label = "Convert to Trim Path"
    bl_description = ("Add a Geometry Nodes modifier that generates a quad strip "
                      "along the path with trim region UVs")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            cls.poll_message_set("No active object")
            return False
        if obj.type not in ('GREASEPENCIL', 'CURVE'):
            cls.poll_message_set("Active object must be a Grease Pencil or Curve")
            return False
        region = context.scene.bake_turbo_trim.get_active_region()
        if region is None:
            cls.poll_message_set("No active trim region")
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        trim = context.scene.bake_turbo_trim
        region = trim.get_active_region()

        # Pick node group variant
        if obj.type == 'GREASEPENCIL':
            ng = _get_or_create_group("BakeTurbo_TrimPath_GP",
                                      _build_gp_group)
        else:
            ng = _get_or_create_group("BakeTurbo_TrimPath_Curve",
                                      _build_curve_group)

        # Add modifier
        mod = obj.modifiers.new(name="Trim Path", type='NODES')
        mod.node_group = ng

        # Set UV bounds from active region
        u_min, u_max, v_min, v_max = _get_region_uv_bounds(region)
        _set_modifier_input(mod, 'U Min', u_min)
        _set_modifier_input(mod, 'U Max', u_max)
        _set_modifier_input(mod, 'V Min', v_min)
        _set_modifier_input(mod, 'V Max', v_max)

        # Auto-assign surface target from a selected mesh
        target_mesh = None
        for sel_obj in context.selected_objects:
            if sel_obj.type == 'MESH' and sel_obj != obj:
                target_mesh = sel_obj
                break

        if target_mesh is not None:
            _set_modifier_input(mod, 'Surface Target', target_mesh)

        # Create/find a material with the trim sheet texture
        trim_mat = _get_or_create_trim_material(trim)
        if trim_mat is not None:
            _set_modifier_input(mod, 'Material', trim_mat)

        # Switch Properties editor to modifier tab
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.spaces.active.context = 'MODIFIER'
                break

        self.report({'INFO'}, f"Trim path created with region '{region.name}'")
        return {'FINISHED'}


classes = (BT_OT_ConvertToTrimPath,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
