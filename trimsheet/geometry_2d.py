"""2D geometry algorithms: MVC weights, containment, boundary, mirror, rotate."""

import numpy as np
import copy

from .math_utils import (
    compare, compactPoints, normal, deepToList, roundList,
    padPoints, applyMatrix, subtract, distance,
)


# --- Boundary vertices ---

def polygonsToEdges(polygons):
    edges = {}
    for poly in polygons:
        for i in range(len(poly)):
            edge = tuple(sorted((tuple(poly[i]), tuple(poly[(i + 1) % len(poly)]))))
            edges[edge] = edges.get(edge, 0) + 1
    return edges


def boundaryEdgeMap(boundaryEdges):
    edgeMap = {}
    for a, b in boundaryEdges:
        edgeMap.setdefault(a, []).append(b)
        edgeMap.setdefault(b, []).append(a)
    for key in edgeMap:
        if len(edgeMap[key]) != 2:
            raise ValueError(
                f"Vertex {key} has {len(edgeMap[key])} unique sides, must be 2!"
            )
    return edgeMap


def nextBoundaryPoint(prev, current, edgeMap):
    for point in edgeMap[tuple(current)]:
        if compare(point, prev) != 0:
            return point
    raise ValueError(f"No next point for {current}")


def firstBoundaryPoint(polygons, edgeMap):
    for i in range(len(polygons)):
        for j in range(len(polygons[i])):
            if tuple(polygons[i][j]) in edgeMap:
                return [i, j]


def nextPolygonPoint(polygons, polygonIndex, polygonPointIndex, positiveStep=True):
    step = 1 if positiveStep else -1
    polygon = polygons[polygonIndex]
    return polygon[(polygonPointIndex + step) % len(polygon)]


def boundaryVertices(polygons, edges=None):
    if edges is None:
        edges = polygonsToEdges(polygons)
    boundaryEdges = [edge for edge in edges if edges[edge] == 1]
    edgeMap = boundaryEdgeMap(boundaryEdges)

    firstPolygonIndex, firstPolygonPointIndex = firstBoundaryPoint(polygons, edgeMap)
    first = tuple(polygons[firstPolygonIndex][firstPolygonPointIndex])
    boundary = [first]
    prev = first

    second = tuple(nextPolygonPoint(polygons, firstPolygonIndex, firstPolygonPointIndex))
    if second in edgeMap[tuple(first)]:
        current = second
    else:
        beforeFirst = nextPolygonPoint(
            polygons, firstPolygonIndex, firstPolygonPointIndex, positiveStep=False
        )
        current = nextBoundaryPoint(beforeFirst, first, edgeMap)

    while compare(current, first) != 0:
        boundary.append(current)
        prev, current = current, nextBoundaryPoint(prev, current, edgeMap)

    boundary = compactPoints(boundary)
    if len(boundary) < 3:
        raise ValueError(f"Boundary {boundary} is not a polygon!")

    firstFace = compactPoints(polygons[0])
    firstFaceNormal = normal(firstFace[0], firstFace[1], firstFace[2])
    boundaryNormal = normal(boundary[0], boundary[1], boundary[2])
    if boundaryNormal != firstFaceNormal:
        boundary = [boundary[0]] + boundary[1:][::-1]
    return boundary


# --- MVC (Mean Value Coordinates) ---

def _normalise_weights(arr):
    s = sum(arr)
    return [a / s for a in arr]


def mvcPointOnVertex(n, index):
    arr = [0] * n
    arr[index] = 1
    return arr


def mvcPointOnEdgeWeight(n, distance1, distance2, index1):
    arr = [0] * n
    index2 = (index1 + 1) % n
    dist = distance1 + distance2
    arr[index1] = distance2 / dist
    arr[index2] = distance1 / dist
    return arr


def mvcPointWeight(polygon, point):
    p = np.array(point)
    distances = []
    tanThetas = []

    for i in range(len(polygon)):
        vertex = np.array(polygon[i])
        v1 = vertex - p
        v1Dist = np.linalg.norm(v1)

        if compare(v1Dist, 0) == 0:
            return mvcPointOnVertex(len(polygon), i)

        nextVertex = polygon[(i + 1) % len(polygon)]
        v2 = nextVertex - p
        v2Dist = np.linalg.norm(v2)

        if compare(v2Dist, 0) == 0:
            return mvcPointOnVertex(len(polygon), (i + 1) % len(polygon))

        cos = np.dot(v1, v2) / (v1Dist * v2Dist)
        if compare(cos, -1) == 0:
            return mvcPointOnEdgeWeight(len(polygon), v1Dist, v2Dist, i)

        theta = np.arccos(np.dot(v1, v2) / (v1Dist * v2Dist))
        distances.append(v1Dist)
        tanThetas.append(np.tan(theta / 2))

    weight = []
    for i in range(len(polygon)):
        prevTan = tanThetas[(i - 1) % len(tanThetas)]
        tan = tanThetas[i]
        w = (prevTan + tan) / distances[i]
        weight.append(w)

    return _normalise_weights(weight)


def mvcWeights(polygon, points):
    weights = []
    for point in points:
        try:
            iter(point[0])
            weights.append(mvcWeights(polygon, point))
        except (TypeError, IndexError):
            weights.append(mvcPointWeight(polygon, point))
    return deepToList(weights)


def applyMvcWeight(polygon, weights):
    newX = 0.0
    newY = 0.0
    for i in range(len(polygon)):
        x, y = polygon[i]
        newX += weights[i] * np.array(x)
        newY += weights[i] * np.array(y)
    return [float(newX), float(newY)]


def applyMvcWeights(polygon, weights):
    if not hasattr(weights[0], '__iter__'):
        return applyMvcWeight(polygon, weights)
    return [applyMvcWeights(polygon, weights[i]) for i in range(len(weights))]


# --- Polygon containment ---

def minMaxCoords(points):
    minX, minY = points[0]
    maxX, maxY = points[0]
    for point in points:
        if point[0] < minX:
            minX = point[0]
        elif point[0] > maxX:
            maxX = point[0]
        if point[1] < minY:
            minY = point[1]
        elif point[1] > maxY:
            maxY = point[1]
    return [minX, minY, maxX, maxY]


def minMaxCoordsPolygons(polygons):
    minX, minY = polygons[0][0]
    maxX, maxY = polygons[0][0]
    for polygon in polygons:
        mm = minMaxCoords(polygon)
        if mm[0] < minX:
            minX = mm[0]
        if mm[1] < minY:
            minY = mm[1]
        if mm[2] > maxX:
            maxX = mm[2]
        if mm[3] > maxY:
            maxY = mm[3]
    return [minX, minY, maxX, maxY]


def containmentMatrix(innerPolygons, outerPolygon, boundByX=True, boundByY=True):
    if not boundByX and not boundByY:
        raise ValueError("Cannot contain without bounds!")

    innerCoords = minMaxCoordsPolygons(innerPolygons)
    outerCoords = minMaxCoords(outerPolygon)

    innerDistX = innerCoords[2] - innerCoords[0]
    innerDistY = innerCoords[3] - innerCoords[1]
    outerDistX = outerCoords[2] - outerCoords[0]
    outerDistY = outerCoords[3] - outerCoords[1]

    innerRatio = innerDistX / innerDistY
    outerRatio = outerDistX / outerDistY

    if not boundByX or (boundByY and innerRatio < outerRatio):
        scale = outerDistY / innerDistY
    else:
        scale = outerDistX / innerDistX

    S = np.array([[scale, 0], [0, scale]])
    scaledOrigin = S @ innerCoords[0:2]

    T = np.eye(3)
    T[:2, :2] = S
    T[:2, 2] = outerCoords[0] - scaledOrigin[0], outerCoords[1] - scaledOrigin[1]
    return T


def transformPolygons(polygons, matrix):
    paddedPolygons = padPoints(polygons, len(matrix[0]))
    newPolygons = []
    for i in range(len(paddedPolygons)):
        newPolygons.append([])
        for vertex in paddedPolygons[i]:
            newPolygons[i].append(deepToList(matrix @ np.array(vertex)))
    return padPoints(newPolygons, len(matrix[0]) - 1)


def containedPolygons(innerPolygons, outerPolygon, boundByX=True, boundByY=True):
    matrix = containmentMatrix(innerPolygons, outerPolygon, boundByX, boundByY)
    return roundList(deepToList(transformPolygons(innerPolygons, matrix)))


# --- Mirror / Rotate ---

def mirrorPoints(points):
    if len(points) == 0:
        return []
    mirrored = copy.deepcopy(points)
    for i in range(len(mirrored)):
        for j in range(len(mirrored[i])):
            point = list(mirrored[i][j])
            point[0] *= -1
            mirrored[i][j] = type(mirrored[i][j])(point)
    return mirrored


def rotatePointsFill(points, step=1):
    if len(points) == 0:
        return []
    boundary = boundaryVertices(points)
    step = step % len(boundary)
    weights = mvcWeights(boundary, points)
    rotatedBoundary = boundary[step:] + boundary[0:step]
    return applyMvcWeights(rotatedBoundary, weights)


def rotatePointsFit(points, degrees):
    radians = np.radians(degrees)
    sinTheta = np.sin(radians)
    cosTheta = np.cos(radians)
    R = np.array([[cosTheta, -sinTheta], [sinTheta, cosTheta]])
    return applyMatrix(points, R)
