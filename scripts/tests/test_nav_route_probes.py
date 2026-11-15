"""Focused pure tests for named offline route probes; no processes or assets."""

import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import unittest


SCRIPT = Path(os.environ.get(
    "BNAV_ROUTE_PROBES_SCRIPT", Path(__file__).resolve().parents[1] / "probe_nav_routes.py"
))
sys.path.insert(0, str(SCRIPT.resolve().parent))
SPEC = importlib.util.spec_from_file_location("nav_route_probes", SCRIPT)
probes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probes)


def probe(limit=2.0, outcome="complete"):
    return {"name": "seam-wall.detour-1", "start": [0.0, 1.0, 0.0], "end": [4.0, 1.0, 0.0],
            "max_projection_distance": limit,
            "expect": {"outcome": outcome, "direct_path_blocked": True, "min_traversed_tiles": 2}}


def suite(kind="collection"):
    value = {"format": "bnav-route-probes-v1", "target_kind": kind, "manifest_sha256": "a" * 64,
             "units": "synthetic metres", "scope": "original pure route fixture",
             "limitations": ["No game geometry, native query or calibrated movement evidence"],
             "probes": [probe()]}
    if kind == "wow-selection":
        value["query_flags"] = {"include": 1, "exclude": 2}
    return value


def response(selected_probe=None, kind="collection", bits=32):
    selected_probe = probe() if selected_probe is None else selected_probe
    limit = selected_probe["max_projection_distance"]
    within = 1.0 <= limit
    native = {"complete": True, "reference_bits": bits, "loaded_tiles": 2, "traversed_tiles": 2,
              "corridor_polygons": 3, "direct_path_blocked": True,
              "points": [[0.0, 0.0, 0.0], [2.0, 0.0, 1.0], [4.0, 0.0, 0.0]]}
    # Independent simple geometry: each endpoint projects down by exactly one;
    # the V-shaped polyline comprises two segments of length sqrt(5).
    metrics = {"basis": "serialized-native-polyline", "requested_start": [0.0, 1.0, 0.0],
               "requested_end": [4.0, 1.0, 0.0], "reported_start": [0.0, 0.0, 0.0],
               "reported_end": [4.0, 0.0, 0.0], "start_projection_distance": 1.0,
               "end_projection_distance": 1.0, "max_projection_distance": 1.0,
               "requested_separation": 4.0, "reported_endpoint_separation": 4.0,
               "path_length": 2 * math.sqrt(5), "point_count": 3, "corridor_polygons": 3,
               "multi_polygon_corridor": True, "reported_endpoints_equal_requested": False,
               "projection_limit": limit, "within_projection_limit": within}
    status = "COMPLETE_PROJECTED_PATH" if kind == "collection" else "SELECTED_REGION_PROJECTED_PATH"
    value = {"status": status if within else "PROJECTION_LIMIT_EXCEEDED", "result": native,
             "route_metrics": metrics, "game_qa": "NOT_RUN"}
    if kind == "collection":
        value.update(game="synthetic", zone="unit-fixture",
                     coverage={"scope": "synthetic fixture", "limitations": ["No game QA"]},
                     native_adapter_compatibility="NOT_VERIFIED")
    else:
        value.update(map_id="synthetic-fixture", include_flags=1, exclude_flags=2,
                     scope={"kind": "explicit-selected-tiles", "whole_map_coverage": False,
                            "unselected_tiles": "unknown; neither empty nor evaluated"})
        native.update(scope="selected-tiles", whole_map_coverage=False,
                      profile="cmangos-v8" if bits == 32 else "cmangos-v8-ref64",
                      include_flags=1, exclude_flags=2, requested_start=selected_probe["start"],
                      requested_end=selected_probe["end"], snapped_start=native["points"][0],
                      snapped_end=native["points"][-1])
    return value


def invocation(value=None, exit_code=None):
    value = response() if value is None else value
    if exit_code is None:
        exit_code = 3 if value["status"] == "PROJECTION_LIMIT_EXCEEDED" else 0
    return {"exit_code": exit_code, "stdout": json.dumps(value), "stderr": "", "output_truncated": False}


class NamedRouteProbeTests(unittest.TestCase):
    def assert_verdict(self, selected_probe, call, kind, bits, expected, actual=None):
        before_probe, before_call = copy.deepcopy(selected_probe), copy.deepcopy(call)
        result = probes.assess(selected_probe, call, kind, bits)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("verdict"), expected, result)
        self.assertIsInstance(result.get("reasons"), list)
        self.assertTrue(all(isinstance(reason, str) and reason for reason in result["reasons"]))
        if expected != "MATCH":
            self.assertTrue(result["reasons"], result)
        if actual is not None:
            self.assertEqual(result.get("actual_outcome"), actual, result)
        self.assertEqual(selected_probe, before_probe)
        self.assertEqual(call, before_call)
        return result

    def test_valid_suites_require_explicit_policy_and_preserve_inputs(self):
        for kind in ("collection", "wow-selection"):
            value = suite(kind)
            value["probes"][0]["max_projection_distance"] = 0
            value["probes"][0]["expect"]["outcome"] = "projection_limit_exceeded"
            before = copy.deepcopy(value)
            with self.subTest(kind=kind):
                self.assertEqual(probes.validate_suite(value), value)
                self.assertEqual(value, before)
        value = suite()
        value["probes"] = [{**probe(), "name": f"route-{index}"} for index in range(32)]
        self.assertEqual(len(probes.validate_suite(value)["probes"]), 32)

    def test_suite_schema_strings_and_count_bounds_fail_closed(self):
        mutations = (
            lambda value: value.update(extra="unexpected"),
            lambda value: value.pop("manifest_sha256"),
            lambda value: value.update(format="bnav-route-probes-v2"),
            lambda value: value.update(target_kind="automatic"),
            lambda value: value.update(manifest_sha256="g" * 64),
            lambda value: value.update(manifest_sha256="a" * 63),
            lambda value: value.update(units=""),
            lambda value: value.update(units="u" * 129),
            lambda value: value.update(scope=""),
            lambda value: value.update(scope="s" * 1025),
            lambda value: value.update(limitations=[""]),
            lambda value: value.update(limitations=["x" * 1025]),
            lambda value: value.update(limitations=["x"] * 65),
            lambda value: value.update(probes=[]),
            lambda value: value.update(probes=[{**probe(), "name": f"route-{index}"} for index in range(33)]),
        )
        for index, change in enumerate(mutations):
            value = suite()
            change(value)
            with self.subTest(index=index), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)

    def test_target_flags_are_required_only_for_wow_and_strictly_bounded(self):
        value = suite()
        value["query_flags"] = {"include": 1, "exclude": 0}
        with self.assertRaises(probes.Invalid):
            probes.validate_suite(value)
        for flags in (None, {}, {"include": 0, "exclude": 0}, {"include": 65536, "exclude": 0},
                      {"include": True, "exclude": 0}, {"include": 1, "exclude": -1},
                      {"include": 1, "exclude": 65536}, {"include": 1, "exclude": False},
                      {"include": 1, "exclude": 1}, {"include": 1, "exclude": 0, "extra": 2}):
            value = suite("wow-selection")
            if flags is None:
                value.pop("query_flags")
            else:
                value["query_flags"] = flags
            with self.subTest(flags=flags), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)

    def test_probe_names_exact_keys_and_expectations_are_validated(self):
        changes = (
            lambda p: p.update(name=""),
            lambda p: p.update(name="a" * 65),
            lambda p: p.update(name="../route"),
            lambda p: p.update(name="white space"),
            lambda p: p.update(name="-starts-with-punctuation"),
            lambda p: p.update(extra=True),
            lambda p: p.pop("max_projection_distance"),
            lambda p: p["expect"].update(outcome="blocked"),
            lambda p: p["expect"].update(direct_path_blocked=1),
            lambda p: p["expect"].update(min_traversed_tiles=True),
            lambda p: p["expect"].update(min_traversed_tiles=0),
            lambda p: p["expect"].update(min_traversed_tiles=257),
            lambda p: p["expect"].update(extra="unexpected"),
        )
        for index, change in enumerate(changes):
            value = suite()
            change(value["probes"][0])
            with self.subTest(index=index), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)
        value = suite()
        value["probes"].append(copy.deepcopy(value["probes"][0]))
        with self.assertRaises(probes.Invalid):
            probes.validate_suite(value)

    def test_coordinates_and_projection_limits_reject_non_numbers_and_nonfinite_values(self):
        for field in ("start", "end"):
            for bad in ([], [0, 1], [0, 1, 2, 3], [True, 0, 0], ["0", 0, 0],
                        [float("nan"), 0, 0], [float("inf"), 0, 0], [10_000_001, 0, 0],
                        [-10_000_001, 0, 0], [10 ** 400, 0, 0], (0, 0, 0)):
                value = suite()
                value["probes"][0][field] = bad
                with self.subTest(field=field, bad=repr(bad)), self.assertRaises(probes.Invalid):
                    probes.validate_suite(value)
        for bad in (None, True, "1", -1, float("nan"), float("inf"), 10 ** 400):
            value = suite()
            value["probes"][0]["max_projection_distance"] = bad
            with self.subTest(limit=repr(bad)), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)

    def test_valid_projected_outcomes_match_both_wrappers_and_abis(self):
        for kind in ("collection", "wow-selection"):
            for bits in (32, 64):
                for limit, outcome in ((2.0, "complete"), (1.0, "complete"),
                                       (0.5, "projection_limit_exceeded"), (0.0, "projection_limit_exceeded")):
                    selected = probe(limit, outcome)
                    with self.subTest(kind=kind, bits=bits, limit=limit):
                        self.assert_verdict(selected, invocation(response(selected, kind, bits)),
                                            kind, bits, "MATCH", outcome)

    def test_valid_but_unexpected_observations_are_mismatches_not_errors(self):
        for change in (lambda p: p["expect"].update(outcome="projection_limit_exceeded"),
                       lambda p: p["expect"].update(direct_path_blocked=False),
                       lambda p: p["expect"].update(min_traversed_tiles=3)):
            selected = probe()
            change(selected)
            self.assert_verdict(selected, invocation(), "collection", 32, "MISMATCH", "complete")
        selected = probe(0.5, "complete")
        self.assert_verdict(selected, invocation(response(selected)), "collection", 32,
                            "MISMATCH", "projection_limit_exceeded")

    def test_process_failures_and_malformed_invocations_never_match(self):
        changes = (
            lambda call: call.update(exit_code=2, stdout="", stderr="native query failed: no complete path"),
            lambda call: call.update(exit_code=None, timed_out=True),
            lambda call: call.update(output_truncated=True),
            lambda call: call.update(exit_code=False),
            lambda call: call.update(exit_code=0.0),
            lambda call: call.update(stdout="{"),
            lambda call: call.update(stdout="[]"),
            lambda call: call.update(stdout=None),
            lambda call: call.update(output_truncated=0),
        )
        for index, change in enumerate(changes):
            call = invocation()
            change(call)
            with self.subTest(index=index):
                self.assert_verdict(probe(), call, "collection", 32, "ERROR")
        selected = probe(0.5, "projection_limit_exceeded")
        call = invocation(response(selected))
        call.update(exit_code=2, stdout="", stderr="native query failed: no complete path")
        self.assert_verdict(selected, call, "collection", 32, "ERROR")

    def test_native_shape_counts_abi_and_boolean_types_are_errors(self):
        fields = (
            ("complete", False), ("complete", 1), ("reference_bits", 64), ("reference_bits", 32.0),
            ("loaded_tiles", 0), ("loaded_tiles", 257), ("loaded_tiles", True),
            ("traversed_tiles", 0), ("traversed_tiles", 3), ("traversed_tiles", True),
            ("corridor_polygons", 0), ("corridor_polygons", 257), ("corridor_polygons", True),
            ("direct_path_blocked", 1), ("points", [[0, 0, 0]]),
            ("points", [[0, 0, 0]] * 257), ("points", [[0, 0], [4, 0, 0]]),
            ("points", [[True, 0, 0], [4, 0, 0]]), ("points", [[float("nan"), 0, 0], [4, 0, 0]]),
        )
        for field, bad in fields:
            value = response()
            value["result"][field] = bad
            with self.subTest(field=field, value=repr(bad)):
                self.assert_verdict(probe(), invocation(value), "collection", 32, "ERROR")

    def test_declared_metrics_status_exit_and_qa_must_agree(self):
        for field, bad in (("path_length", 100.0), ("within_projection_limit", False),
                           ("within_projection_limit", 1), ("max_projection_distance", True),
                           ("requested_start", [0, 0, 0]), ("point_count", 2)):
            value = response()
            value["route_metrics"][field] = bad
            with self.subTest(metric=field, value=bad):
                self.assert_verdict(probe(), invocation(value), "collection", 32, "ERROR")
        for key, bad in (("game_qa", "VERIFIED"), ("status", "PROJECTION_LIMIT_EXCEEDED"),
                         ("status", "SELECTED_REGION_PROJECTED_PATH"), ("route_metrics", None)):
            value = response()
            value[key] = bad
            with self.subTest(key=key, value=bad):
                self.assert_verdict(probe(), invocation(value, exit_code=0), "collection", 32, "ERROR")
        self.assert_verdict(probe(), invocation(exit_code=3), "collection", 32, "ERROR")
        selected = probe(0.5, "projection_limit_exceeded")
        self.assert_verdict(selected, invocation(response(selected), exit_code=0), "collection", 32, "ERROR")


if __name__ == "__main__":
    unittest.main()
