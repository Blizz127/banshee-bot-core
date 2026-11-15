"""Focused serialized-route metric checks; no native tools or game data."""

import copy
import math
from pathlib import Path
import sys
import unittest


sys.dont_write_bytecode = True
# PYTHONPATH can select the integrator's module before this test-only branch is
# merged. The local scripts directory supplies the normal post-merge import.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from nav_route_metrics import RouteError, measure_route, validate_projection_limit


def native(points=None, corridor_polygons=1):
    return {
        "complete": True,
        "points": [[0, 0, 0], [0, 3, 4]] if points is None else points,
        "corridor_polygons": corridor_polygons,
    }


class ProjectionLimit(unittest.TestCase):
    def test_omitted_and_nonnegative_numeric_limits(self):
        self.assertIsNone(validate_projection_limit(None))
        for value in (0, 5, 0.25, 1e200, -0.0):
            with self.subTest(value=value):
                validated = validate_projection_limit(value)
                self.assertIsInstance(validated, float)
                self.assertEqual(validated, value)

    def test_invalid_limits_raise_the_public_value_error(self):
        self.assertTrue(issubclass(RouteError, ValueError))
        for value in (True, False, "5", "", [], {}, -1, -0.01,
                      math.nan, math.inf, -math.inf, 10**400):
            with self.subTest(type=type(value).__name__, value=repr(value)[:40]):
                with self.assertRaises(RouteError):
                    validate_projection_limit(value)


class RouteMetrics(unittest.TestCase):
    def test_exact_three_four_five_in_all_three_dimensions(self):
        result = measure_route([0, 0, 0], [0, 3, 4], native())
        expected = {
            "requested_start": [0, 0, 0], "requested_end": [0, 3, 4],
            "reported_start": [0, 0, 0], "reported_end": [0, 3, 4],
            "start_projection_distance": 0, "end_projection_distance": 0,
            "max_projection_distance": 0, "requested_separation": 5,
            "reported_endpoint_separation": 5, "path_length": 5,
            "point_count": 2, "corridor_polygons": 1,
            "multi_polygon_corridor": False,
            "reported_endpoints_equal_requested": True,
            "projection_limit": None, "within_projection_limit": None,
            "basis": "serialized-native-polyline",
        }
        for name, value in expected.items():
            with self.subTest(field=name):
                self.assertEqual(result[name], value)
        self.assertIs(result["within_projection_limit"], None)
        self.assertIs(result["multi_polygon_corridor"], False)

    def test_bent_polyline_length_is_not_endpoint_separation(self):
        result = measure_route([0, 0, 0], [3, 4, 0],
                               native([[0, 0, 0], [3, 0, 0], [3, 4, 0]], 3))
        self.assertEqual(result["path_length"], 7)
        self.assertEqual(result["requested_separation"], 5)
        self.assertEqual(result["reported_endpoint_separation"], 5)
        self.assertEqual(result["point_count"], 3)
        self.assertIs(result["multi_polygon_corridor"], True)

    def test_both_end_projections_use_three_dimensional_source_units(self):
        result = measure_route([0, 0, 0], [10, 0, 0],
                               native([[0, 3, 4], [10, 0, 12]], 2), limit=12)
        self.assertEqual(result["start_projection_distance"], 5)
        self.assertEqual(result["end_projection_distance"], 12)
        self.assertEqual(result["max_projection_distance"], 12)
        self.assertEqual(result["requested_separation"], 10)
        self.assertAlmostEqual(result["reported_endpoint_separation"], math.sqrt(173))
        self.assertAlmostEqual(result["path_length"], math.sqrt(173))
        self.assertIs(result["reported_endpoints_equal_requested"], False)
        self.assertIs(result["within_projection_limit"], True)

    def test_vertical_projection_and_equal_limit_boundary(self):
        result = measure_route([1, -3, 2], [1, 10, 2],
                               native([[1, 0, 2], [1, 6, 2]]), limit=4)
        self.assertEqual(result["start_projection_distance"], 3)
        self.assertEqual(result["end_projection_distance"], 4)
        self.assertEqual(result["max_projection_distance"], 4)
        self.assertEqual(result["requested_separation"], 13)
        self.assertEqual(result["reported_endpoint_separation"], 6)
        self.assertEqual(result["path_length"], 6)
        self.assertIs(result["within_projection_limit"], True)
        outside = measure_route([1, -3, 2], [1, 10, 2],
                                native([[1, 0, 2], [1, 6, 2]]), limit=math.nextafter(4, 0))
        self.assertIs(outside["within_projection_limit"], False)

    def test_zero_length_and_zero_projection_limit(self):
        result = measure_route([1, 2, 3], [1, 2, 3],
                               native([[1, 2, 3], [1, 2, 3]]), limit=0)
        for field in ("start_projection_distance", "end_projection_distance",
                      "max_projection_distance", "requested_separation",
                      "reported_endpoint_separation", "path_length"):
            with self.subTest(field=field):
                self.assertEqual(result[field], 0)
        self.assertIs(result["within_projection_limit"], True)
        self.assertIs(result["reported_endpoints_equal_requested"], True)
        projected = measure_route([1, 1, 3], [1, 2, 3],
                                  native([[1, 2, 3], [1, 2, 3]]), limit=0)
        self.assertIs(projected["within_projection_limit"], False)

    def test_omitted_limit_is_unknown_not_failed(self):
        route = native([[0, 3, 4], [0, 6, 8]])
        omitted = measure_route([0, 0, 0], [0, 6, 8], route)
        strict = measure_route([0, 0, 0], [0, 6, 8], route, limit=0)
        self.assertIsNone(omitted["projection_limit"])
        self.assertIsNone(omitted["within_projection_limit"])
        self.assertEqual(strict["projection_limit"], 0)
        self.assertIs(strict["within_projection_limit"], False)

    def test_requested_and_reported_vectors_are_preserved_without_input_mutation(self):
        start, end = (1, 2, 3), [4, 6, 3]
        route = native([(1, 2, 3), (4, 6, 3)], 2)
        before = copy.deepcopy((start, end, route))
        result = measure_route(start, end, route)
        self.assertEqual(list(result["requested_start"]), list(start))
        self.assertEqual(list(result["requested_end"]), end)
        self.assertEqual(list(result["reported_start"]), list(route["points"][0]))
        self.assertEqual(list(result["reported_end"]), list(route["points"][-1]))
        self.assertEqual((start, end, route), before)

    def test_finite_large_distances_do_not_overflow_when_squared(self):
        result = measure_route([0, 0, 0], [1e200, 0, 0],
                               native([[0, 0, 0], [1e200, 0, 0]]))
        self.assertEqual(result["path_length"], 1e200)
        self.assertEqual(result["requested_separation"], 1e200)
        self.assertTrue(math.isfinite(result["reported_endpoint_separation"]))

    def test_upper_point_and_corridor_bounds_are_inclusive(self):
        points = [[x, 0, 0] for x in range(256)]
        result = measure_route(points[0], points[-1], native(points, 256))
        self.assertEqual(result["path_length"], 255)
        self.assertEqual(result["point_count"], 256)
        self.assertEqual(result["corridor_polygons"], 256)


class InvalidRoutes(unittest.TestCase):
    def assert_invalid(self, route, start=None, end=None, limit=None):
        start = [0, 0, 0] if start is None else start
        end = [0, 3, 4] if end is None else end
        with self.assertRaises(RouteError):
            measure_route(start, end, route, limit=limit)

    def test_partial_and_truthy_nonboolean_complete_are_rejected(self):
        for complete in (False, None, 0, 1, "true", [], {}):
            route = native()
            route["complete"] = complete
            with self.subTest(complete=complete):
                self.assert_invalid(route)
        route = native()
        route.pop("complete")
        self.assert_invalid(route)

    def test_missing_fields_and_nonobject_results_are_rejected(self):
        for route in (None, [], "complete", True, 3):
            with self.subTest(route=route):
                self.assert_invalid(route)
        for field in ("points", "corridor_polygons"):
            route = native()
            route.pop(field)
            with self.subTest(field=field):
                self.assert_invalid(route)

    def test_point_collection_and_coordinate_shape_are_checked(self):
        for points in (None, [], [[0, 0, 0]], ((0, 0, 0), (0, 3, 4)),
                       [[0, 0, 0]] * 257, [[], [0, 3, 4]],
                       [[0, 0], [0, 3, 4]], [[0, 0, 0, 0], [0, 3, 4]],
                       ["000", [0, 3, 4]], [{0: 0, 1: 0, 2: 0}, [0, 3, 4]]):
            route = native()
            route["points"] = points
            with self.subTest(points_type=type(points).__name__, preview=repr(points)[:70]):
                self.assert_invalid(route)

    def test_nonnumeric_boolean_and_nonfinite_coordinates_are_rejected(self):
        for value in (True, False, "0", None, [], {}, math.nan, math.inf, -math.inf, 10**400):
            with self.subTest(type=type(value).__name__, value=repr(value)[:40]):
                self.assert_invalid(native([[0, value, 0], [0, 3, 4]]))
                self.assert_invalid(native(), start=[value, 0, 0])
                self.assert_invalid(native(), end=[0, 3, value])

    def test_requested_coordinate_shape_is_checked(self):
        for vector in ([], [0, 0], [0, 0, 0, 0], "000", True, {0: 0, 1: 0, 2: 0}):
            with self.subTest(vector=vector):
                self.assert_invalid(native(), start=vector)
                self.assert_invalid(native(), end=vector)
        for start, end in ((None, [0, 3, 4]), ([0, 0, 0], None)):
            with self.assertRaises(RouteError):
                measure_route(start, end, native())

    def test_corridor_count_is_a_bounded_integer(self):
        for count in (False, True, 0, -1, 257, 1.0, "1", None, [], math.nan, math.inf):
            with self.subTest(count=count):
                self.assert_invalid(native(corridor_polygons=count))

    def test_overflowing_distances_and_polyline_sum_are_rejected(self):
        cases = [
            ([1e308, 0, 0], [-1e308, 0, 0], native([[1e308, 0, 0], [-1e308, 0, 0]])),
            ([0, 0, 0], [0, 0, 0], native([[0, 0, 0], [1e308, 0, 0], [0, 0, 0]])),
            ([-1e308, 0, 0], [-1e308, 1, 0], native([[1e308, 0, 0], [1e308, 1, 0]])),
        ]
        for start, end, route in cases:
            with self.subTest(start=start, end=end):
                self.assert_invalid(route, start=start, end=end)

    def test_measure_route_also_validates_the_optional_limit(self):
        for limit in (False, "5", -1, math.nan, math.inf, 10**400):
            with self.subTest(limit=repr(limit)[:40]):
                self.assert_invalid(native(), limit=limit)


if __name__ == "__main__":
    unittest.main()
