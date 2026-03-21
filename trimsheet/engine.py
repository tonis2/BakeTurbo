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


def assign_trim(obj, bm, uv_layer, region_coords, fit_mode):
    """Map selected faces' UVs to fit within the given trim region.

    Returns list of face indices that were assigned.
    """
    selected = [f for f in bm.faces if f.select]
    if not selected:
        raise TrimsheetError("No faces selected!")

    mesh_coords = _parse_mesh_coordinates(selected)
    seams = _get_seam_edge_neighbors(selected)

    try:
        flat_mesh_coords = unwrap(mesh_coords, seams)
    except UnwrapException as e:
        raise TrimsheetError(str(e))

    uv_coords = _compute_uv_coords(region_coords, flat_mesh_coords, fit_mode)

    # Apply UV coordinates to faces
    for i, face in enumerate(selected):
        for j, loop in enumerate(face.loops):
            loop[uv_layer].uv = uv_coords[i][j]

    # Store assignment state for mirror/rotate
    face_indices = [f.index for f in selected]
    _last_assignment['face_indices'] = face_indices
    _last_assignment['flat_mesh_coords'] = flat_mesh_coords
    _last_assignment['region_coords'] = region_coords
    _last_assignment['fit_mode'] = fit_mode
    _last_assignment['reference_uvs'] = uv_coords

    bmesh.update_edit_mesh(obj.data)
    return face_indices


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
