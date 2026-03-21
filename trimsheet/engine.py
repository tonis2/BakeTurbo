"""Core UV mapping logic for trim sheet operations."""

import bmesh

from .math_utils import compactPoints, normal, compare
from .geometry_2d import (
    boundaryVertices, mvcWeights, applyMvcWeights,
    containedPolygons, mirrorPoints, rotatePointsFill, rotatePointsFit,
)
from .unwrap import unwrap, UnwrapException


class TrimsheetError(Exception):
    pass


# Module-level state for the last assignment (needed for mirror/rotate)
_last_assignment = {
    'face_indices': None,
    'flat_mesh_coords': None,
    'region_coords': None,
    'fit_mode': None,
    'reference_uvs': None,
}


def clear_assignment():
    for key in _last_assignment:
        _last_assignment[key] = None


def has_assignment():
    return _last_assignment['face_indices'] is not None


def capture_region_from_face(bm, uv_layer):
    """Capture UV coordinates from the first selected face as a trim region polygon."""
    selected = [f for f in bm.faces if f.select]
    if not selected:
        raise TrimsheetError("No face selected!")

    face = selected[0]
    uv_coords = [tuple(loop[uv_layer].uv) for loop in face.loops]
    uv_coords = compactPoints(uv_coords)
    return uv_coords


def capture_region_from_rect(uv_min, uv_max):
    """Create a rectangular trim region from min/max UV coordinates."""
    return [
        (uv_min[0], uv_min[1]),
        (uv_max[0], uv_min[1]),
        (uv_max[0], uv_max[1]),
        (uv_min[0], uv_max[1]),
    ]


def _parse_mesh_coordinates(faces):
    """Extract 3D vertex coordinates from faces."""
    return [[loop.vert.co[:] for loop in face.loops] for face in faces]


def _get_seam_edge_neighbors(faces):
    """Find face pairs separated by seam edges."""
    faceIndexMap = {face.index: i for i, face in enumerate(faces)}
    seamEdges = set()
    for face in faces:
        for edge in face.edges:
            if edge.seam:
                seamEdges.add(edge)

    neighborFaceLists = []
    for edge in seamEdges:
        face_list = [faceIndexMap[f.index] for f in edge.link_faces if f.index in faceIndexMap]
        if len(face_list) > 1:
            neighborFaceLists.append(face_list)
    return neighborFaceLists


def _compute_uv_coords(region_coords, flat_mesh_coords, fit_mode):
    """Compute UV coordinates using the specified fit mode."""
    if fit_mode == 'FILL':
        boundary = boundaryVertices(flat_mesh_coords)
        if len(region_coords) != len(boundary):
            raise TrimsheetError(
                f"Fill mode requires {len(boundary)} region vertices "
                f"(boundary has {len(boundary)}), but region has {len(region_coords)}. "
                f"Try using Fit mode instead."
            )
        boundaryN = normal(*boundary[0:3])
        regionN = normal(*region_coords[0:3])
        if compare(boundaryN, regionN) != 0:
            boundary.reverse()
        weights = mvcWeights(boundary, flat_mesh_coords)
        return applyMvcWeights(region_coords, weights)
    elif fit_mode == 'FIT':
        return containedPolygons(flat_mesh_coords, region_coords, True, True)
    elif fit_mode == 'FIT_X':
        return containedPolygons(flat_mesh_coords, region_coords, True, False)
    elif fit_mode == 'FIT_Y':
        return containedPolygons(flat_mesh_coords, region_coords, False, True)
    else:
        raise TrimsheetError(f"Unknown fit mode: {fit_mode}")


def _find_connected_groups(faces):
    """Split faces into connected groups based on shared vertices."""
    face_to_group = {}
    groups = []

    for i, face in enumerate(faces):
        # Find all groups this face connects to via shared vertices
        connected = set()
        face_verts = {v.index for v in face.verts}
        for j, other in enumerate(faces[:i]):
            if j in face_to_group:
                other_verts = {v.index for v in other.verts}
                if face_verts & other_verts:
                    connected.add(face_to_group[j])

        if not connected:
            # New group
            group_id = len(groups)
            groups.append([i])
            face_to_group[i] = group_id
        else:
            # Merge into first connected group
            target = min(connected)
            groups[target].append(i)
            face_to_group[i] = target
            # Merge other connected groups into target
            for gid in connected:
                if gid != target:
                    for fi in groups[gid]:
                        face_to_group[fi] = target
                    groups[target].extend(groups[gid])
                    groups[gid] = []

    return [g for g in groups if g]


def assign_trim(obj, bm, uv_layer, region_coords, fit_mode):
    """Map selected faces' UVs to fit within the given trim region.

    Handles disconnected faces by processing each connected group separately.
    Returns list of face indices that were assigned.
    """
    selected = [f for f in bm.faces if f.select]
    if not selected:
        raise TrimsheetError("No faces selected!")

    groups = _find_connected_groups(selected)

    all_face_indices = []
    all_flat_coords = []
    all_uv_coords = []

    for group_indices in groups:
        group_faces = [selected[i] for i in group_indices]
        mesh_coords = _parse_mesh_coordinates(group_faces)
        seams = _get_seam_edge_neighbors(group_faces)

        try:
            flat_mesh_coords = unwrap(mesh_coords, seams)
        except UnwrapException as e:
            raise TrimsheetError(str(e))

        uv_coords = _compute_uv_coords(region_coords, flat_mesh_coords, fit_mode)

        # Apply UV coordinates to faces
        for i, face in enumerate(group_faces):
            for j, loop in enumerate(face.loops):
                loop[uv_layer].uv = uv_coords[i][j]

        all_face_indices.extend(f.index for f in group_faces)
        all_flat_coords.extend(flat_mesh_coords)
        all_uv_coords.extend(uv_coords)

    # Store assignment state for mirror/rotate
    _last_assignment['face_indices'] = all_face_indices
    _last_assignment['flat_mesh_coords'] = all_flat_coords
    _last_assignment['region_coords'] = region_coords
    _last_assignment['fit_mode'] = fit_mode
    _last_assignment['reference_uvs'] = all_uv_coords

    bmesh.update_edit_mesh(obj.data)
    return all_face_indices


def mirror_uvs(obj, bm, uv_layer):
    """Mirror the last UV assignment."""
    if not has_assignment():
        raise TrimsheetError("No active assignment to mirror!")

    faces = [bm.faces[i] for i in _last_assignment['face_indices']]
    current_uvs = [[tuple(loop[uv_layer].uv) for loop in face.loops] for face in faces]
    mirrored = mirrorPoints(current_uvs)

    region_coords = _last_assignment['region_coords']
    fit_mode = _last_assignment['fit_mode']
    uv_coords = _compute_uv_coords(region_coords, mirrored, fit_mode)

    for i, face in enumerate(faces):
        for j, loop in enumerate(face.loops):
            loop[uv_layer].uv = uv_coords[i][j]

    _last_assignment['reference_uvs'] = uv_coords
    bmesh.update_edit_mesh(obj.data)


def rotate_uvs(obj, bm, uv_layer, degrees=None):
    """Rotate the last UV assignment."""
    if not has_assignment():
        raise TrimsheetError("No active assignment to rotate!")

    faces = [bm.faces[i] for i in _last_assignment['face_indices']]
    fit_mode = _last_assignment['fit_mode']
    region_coords = _last_assignment['region_coords']

    if fit_mode == 'FILL':
        current_uvs = [[tuple(loop[uv_layer].uv) for loop in face.loops] for face in faces]
        rotated = rotatePointsFill(current_uvs)
    else:
        if degrees is None:
            degrees = 90
        reference = _last_assignment['reference_uvs']
        rotated_unfit = rotatePointsFit(reference, degrees)
        rotated = _compute_uv_coords(region_coords, rotated_unfit, fit_mode)

    for i, face in enumerate(faces):
        for j, loop in enumerate(face.loops):
            loop[uv_layer].uv = rotated[i][j]

    # Update reference so next rotation accumulates
    _last_assignment['reference_uvs'] = rotated

    bmesh.update_edit_mesh(obj.data)
