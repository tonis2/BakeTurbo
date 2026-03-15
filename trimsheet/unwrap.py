"""Multi-face UV unwrapping algorithm for flattening 3D mesh faces to 2D."""

import numpy as np
import copy

from .math_utils import (
    normal, normalise, crossProduct, distance, subtract,
    compactPoints, deepToList, roundList, padPoints, applyMatrix, compare,
)


class UnwrapException(Exception):
    pass


def sortEdges(edges):
    edgesCopy = list(edges)
    newEdges = [edgesCopy.pop(0)]
    while edgesCopy:
        v = newEdges[-1][1]
        i = 0
        while edgesCopy[i][0] != v:
            i += 1
        newEdges.append(edgesCopy.pop(i))
    if newEdges[0][0] != newEdges[-1][1]:
        raise ValueError(
            f"Last edge {newEdges[-1]} should connect to first edge {newEdges[0]}"
        )
    return newEdges


def rotationMatrixToFlattenFace(face, indexIncreasing):
    normal1 = faceNormal(compactPoints(face), indexIncreasing)
    normal2 = np.array((0, 0, 1))
    return rotationMatrixFromNormals(normal1, normal2)


def getPerpendicularVector(v):
    if v[0] != 0:
        return (-v[1], v[0], 0)
    elif v[1] != 0:
        return (v[2], 0, -v[0])
    return (1, 0, 0)


def antiParallelRotationMatrix(v1):
    axis = getPerpendicularVector(v1)
    R = 2 * np.outer(np.array(axis), np.array(axis)) - np.eye(3)
    return R


def rotationMatrixFromNormals(v1, v2):
    v1, v2 = normalise(v1), normalise(v2)
    v = crossProduct(v1, v2)
    if distance(v) == 0:
        if np.dot(np.array(v1), np.array(v2)) > 0:
            return np.eye(3)
        return antiParallelRotationMatrix(v1)

    K = np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0],
    ])
    cosTheta = np.dot(v1, v2)
    R = np.eye(3) + K + np.dot(K, K) / (1 + cosTheta)
    return R


def faceNormal(face, indexIncreasing):
    P1, P2, P3 = face[0], face[1], face[2]
    if not indexIncreasing:
        P1, P3 = face[2], face[0]
    return normal(P1, P2, P3)


def flatFaceCoordinates(face, indexIncreasing):
    R = rotationMatrixToFlattenFace(face, indexIncreasing)
    return np.dot(np.array(face), R.T)


def sharedEdges(f1, f2):
    result = []
    for i in range(len(f1)):
        for j in range(len(f2)):
            if f1[i] == f2[j]:
                prevI = (i - 1) % len(f1)
                nextI = (i + 1) % len(f1)
                prevJ = (j - 1) % len(f2)
                nextJ = (j + 1) % len(f2)
                if f1[prevI] == f2[prevJ] or f1[prevI] == f2[nextJ]:
                    result.append((prevI, i))
    return result


def emptyMatrix(n, m):
    return [[[] for _ in range(m)] for _ in range(n)]


def graphOfFaces(mesh, seams=None):
    if seams is None:
        seams = []
    graph = emptyMatrix(len(mesh), len(mesh))
    for i in range(len(mesh) - 1):
        for j in range(i + 1, len(mesh)):
            if (i, j) in seams:
                continue
            graph[i][j] = sharedEdges(mesh[i], mesh[j])
            graph[j][i] = sharedEdges(mesh[j], mesh[i])
    return graph


def dfs(matrix, visited, node):
    visited[node] = True
    for neighbor in range(len(matrix)):
        if len(matrix[node][neighbor]) > 0 and not visited[neighbor]:
            dfs(matrix, visited, neighbor)


def countIslands(matrix):
    visited = [False] * len(matrix)
    count = 0
    for node in range(len(matrix)):
        if not visited[node]:
            dfs(matrix, visited, node)
            count += 1
    return count


def vertexIndexIncreasing(mesh, f1Index, f2Index, face1Increasing, graph):
    f1 = mesh[f1Index]
    f2 = mesh[f2Index]
    f1Edge = graph[f1Index][f2Index][0]
    f2Edge = graph[f2Index][f1Index][0]
    f1EdgeValues = (f1[f1Edge[0]], f1[f1Edge[1]])
    f2EdgeValues = (f2[f2Edge[0]], f2[f2Edge[1]])
    return (f1EdgeValues[0] == f2EdgeValues[0]) ^ face1Increasing


def translationRotationMatrix(o1, o2, t1, t2):
    vectorO = np.array(subtract(o1, o2))
    vectorT = np.array(subtract(t1, t2))
    vOnorm = np.linalg.norm(vectorO)
    vTnorm = np.linalg.norm(vectorT)
    product = vOnorm * vTnorm

    cosTheta = np.dot(vectorO, vectorT) / product
    sinTheta = np.cross(vectorO, vectorT) / product

    R = np.array([[cosTheta, -sinTheta], [sinTheta, cosTheta]])
    T = np.eye(3)
    T[:2, :2] = R
    T[:2, 2] = t1 - (R @ o1)
    return T


def validateSeams(seams, numberOfFaces):
    validated = []
    for seam in seams:
        if max(seam) >= numberOfFaces:
            raise ValueError(
                f"Invalid seam: {seam} references index >= number of faces ({numberOfFaces})"
            )
        validated.append(tuple(sorted(seam)))
    return validated


def unwrap(mesh, seams=None):
    if seams is None:
        seams = []
    seams = validateSeams(seams, len(mesh))

    mappedFaces = [None] * len(mesh)
    mappedBy = [[] for _ in range(len(mesh))]

    graph = graphOfFaces(mesh, seams)
    islandCount = countIslands(graph)
    if islandCount == 0:
        raise UnwrapException("Mesh is empty!")
    if islandCount > 1:
        raise UnwrapException(
            f"Can't unwrap mesh with more than 1 island (currently {islandCount})!"
        )

    stack = [(0, True, None, None)]

    while stack:
        index, indexIncreasing, neighbourIndex, neighbourEdgeIndex = stack.pop()

        if (neighbourIndex, neighbourEdgeIndex) in mappedBy[index]:
            continue

        for i in range(len(graph[index])):
            for edgeIndex in range(len(graph[index][i])):
                if i == neighbourIndex and edgeIndex == neighbourEdgeIndex:
                    continue
                nIndexIncreasing = vertexIndexIncreasing(
                    mesh, index, i, indexIncreasing, graph
                )
                stack.append((i, nIndexIncreasing, index, edgeIndex))

        F = copy.deepcopy(mesh[index])
        rotatedFace = deepToList(flatFaceCoordinates(F, indexIncreasing))
        rotatedFace = padPoints(rotatedFace, 2)

        origin1 = rotatedFace[0]
        origin2 = rotatedFace[1]
        target1 = rotatedFace[0]
        target2 = rotatedFace[1]

        if neighbourIndex is not None:
            origin1 = rotatedFace[graph[index][neighbourIndex][0][0]]
            origin2 = rotatedFace[graph[index][neighbourIndex][0][1]]
            target1 = mappedFaces[neighbourIndex][graph[neighbourIndex][index][0][0]]
            target2 = mappedFaces[neighbourIndex][graph[neighbourIndex][index][0][1]]
            if indexIncreasing:
                target1, target2 = target2, target1

        matrix = translationRotationMatrix(origin1, origin2, target1, target2)
        transformedFace = applyMatrix(rotatedFace, matrix, True)

        if mappedFaces[index] is not None:
            if compare(mappedFaces[index], transformedFace) != 0:
                raise UnwrapException(
                    "Shape is not unwrappable without distortion!\n"
                    "(hint: consider marking some edges as seams)"
                )
        else:
            mappedFaces[index] = transformedFace
            mappedBy[index].append((neighbourIndex, neighbourEdgeIndex))
            if neighbourIndex is not None:
                mappedBy[neighbourIndex].append((index, edgeIndex))

    return roundList(deepToList(mappedFaces))
