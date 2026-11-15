"""Measure a serialized native path and an optional endpoint projection policy.

Distances use the input coordinate units. They include serialization rounding;
they do not establish calibration, walkability, or arrival in a game runtime.
"""

import math


class RouteError(ValueError):
    pass


def _finite(value, field):
    if type(value) not in (int, float):
        raise RouteError(f"{field} must be a finite number")
    try:
        number = float(value)
    except OverflowError as error:
        raise RouteError(f"{field} exceeds finite numeric range") from error
    if not math.isfinite(number):
        raise RouteError(f"{field} must be a finite number")
    return number


def _point(value, field):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise RouteError(f"{field} must contain exactly three coordinates")
    return [_finite(coordinate, f"{field}[{index}]")
            for index, coordinate in enumerate(value)]


def validate_projection_limit(value):
    """Validate before calling any backend, including its version command."""
    if value is None:
        return None
    limit = _finite(value, "max projection distance")
    if limit < 0:
        raise RouteError("max projection distance must be nonnegative")
    return limit


def measure_route(start, end, native, limit=None):
    """Return measurements without modifying the native result or inputs.

    A completed native corridor can still project either requested endpoint.
    The optional limit applies to the larger of those two 3D distances. A
    missing limit is unassessed (None), rather than an implicit policy pass.
    """
    limit = validate_projection_limit(limit)
    start = _point(start, "requested start")
    end = _point(end, "requested end")
    if not isinstance(native, dict) or native.get("complete") is not True:
        raise RouteError("native route must be explicitly complete")
    raw_points = native.get("points")
    if not isinstance(raw_points, list) or not 2 <= len(raw_points) <= 256:
        raise RouteError("native route must contain 2..256 points")
    points = [_point(point, f"native points[{index}]")
              for index, point in enumerate(raw_points)]
    polygons = native.get("corridor_polygons")
    if type(polygons) is not int or not 1 <= polygons <= 256:
        raise RouteError("native corridor_polygons must be an integer in 1..256")

    start_distance = _finite(math.dist(start, points[0]), "start projection distance")
    end_distance = _finite(math.dist(end, points[-1]), "end projection distance")
    requested_separation = _finite(math.dist(start, end), "requested separation")
    reported_separation = _finite(math.dist(points[0], points[-1]), "reported endpoint separation")
    try:
        length = math.fsum(math.dist(a, b) for a, b in zip(points, points[1:]))
    except OverflowError as error:
        raise RouteError("path length exceeds finite numeric range") from error
    length = _finite(length, "path length")
    maximum = max(start_distance, end_distance)

    return {
        "basis": "serialized-native-polyline",
        "requested_start": start,
        "requested_end": end,
        "reported_start": points[0],
        "reported_end": points[-1],
        "start_projection_distance": start_distance,
        "end_projection_distance": end_distance,
        "max_projection_distance": maximum,
        "requested_separation": requested_separation,
        "reported_endpoint_separation": reported_separation,
        "path_length": length,
        "point_count": len(points),
        "corridor_polygons": polygons,
        "multi_polygon_corridor": polygons > 1,
        "reported_endpoints_equal_requested": points[0] == start and points[-1] == end,
        "projection_limit": limit,
        "within_projection_limit": None if limit is None else maximum <= limit,
    }
