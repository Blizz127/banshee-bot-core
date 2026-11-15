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
        exit_code = 3 if value["status"] in ("PROJECTION_LIMIT_EXCEEDED", "QUERY_REFUSED") else 0
    return {"exit_code": exit_code, "stdout": json.dumps(value), "stderr": "", "output_truncated": False}


def refusal(reason="START_POLYGON_NOT_FOUND", stage="nearest_start", bits=32):
    return {"format": "bnav-query-refusal-v1", "complete": False, "reference_bits": bits,
            "reason": reason, "stage": stage, "node_limit": 2048, "path_limit": 256,
            "nearest_extents": [2, 4, 2]}


def negative_probe(outcome="start_polygon_not_found"):
    value = probe()
    value["expect"] = {"outcome": outcome}
    return value


def refusal_response(selected_probe, diagnostic=None):
    return {"status": "QUERY_REFUSED", "diagnostic": refusal() if diagnostic is None else diagnostic,
            "requested_start": list(selected_probe["start"]), "requested_end": list(selected_probe["end"]),
            "game_qa": "NOT_RUN"}


class NamedRouteProbeTests(unittest.TestCase):
    def assert_verdict(self, selected_probe, call, kind, bits, expected, actual=None, *, allow_refusals=None):
        before_probe, before_call = copy.deepcopy(selected_probe), copy.deepcopy(call)
        if allow_refusals is None:
            result = probes.assess(selected_probe, call, kind, bits)
        else:
            result = probes.assess(selected_probe, call, kind, bits, allow_refusals=allow_refusals)
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
            lambda value: value.update(format="bnav-route-probes-v3"),
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

    def test_valid_native_refusal_shapes_preserve_inputs(self):
        for bits in (32, 64):
            for reason, stage in (("START_POLYGON_NOT_FOUND", "nearest_start"),
                                  ("END_POLYGON_NOT_FOUND", "nearest_end"),
                                  ("NO_COMPLETE_CORRIDOR", "find_path"),
                                  ("QUERY_BUDGET_EXCEEDED", "find_path"),
                                  ("QUERY_BUDGET_EXCEEDED", "straight_path")):
                value = refusal(reason, stage, bits)
                before = copy.deepcopy(value)
                with self.subTest(bits=bits, reason=reason, stage=stage):
                    self.assertEqual(probes.validate_query_refusal(value, bits), value)
                    self.assertEqual(value, before)
        value = refusal()
        value["nearest_extents"] = [2.0, 4.0, 2.0]
        self.assertEqual(probes.validate_query_refusal(value, 32), value)

    def test_native_refusal_schema_is_exact_and_strict(self):
        mutations = (
            lambda value: value.pop("reason"),
            lambda value: value.update(extra="unknown"),
            lambda value: value.update(points=[[0, 0, 0], [1, 0, 0]]),
            lambda value: value.update(format="bnav-query-refusal-v2"),
            lambda value: value.update(complete=True),
            lambda value: value.update(complete=0),
            lambda value: value.update(reference_bits=64),
            lambda value: value.update(reference_bits=32.0),
            lambda value: value.update(reference_bits=True),
            lambda value: value.update(reason="UNKNOWN"),
            lambda value: value.update(reason="COMPLETE"),
            lambda value: value.update(reason=[]),
            lambda value: value.update(stage="find_path"),
            lambda value: value.update(reason="END_POLYGON_NOT_FOUND", stage="nearest_start"),
            lambda value: value.update(reason="NO_COMPLETE_CORRIDOR", stage="straight_path"),
            lambda value: value.update(reason="QUERY_BUDGET_EXCEEDED", stage="nearest_end"),
            lambda value: value.update(node_limit=2049),
            lambda value: value.update(node_limit=2048.0),
            lambda value: value.update(node_limit=True),
            lambda value: value.update(path_limit=257),
            lambda value: value.update(path_limit=256.0),
            lambda value: value.update(nearest_extents=[2, 4]),
            lambda value: value.update(nearest_extents=[2, 4, 3]),
            lambda value: value.update(nearest_extents=[True, 4, 2]),
            lambda value: value.update(nearest_extents=[2, float("nan"), 2]),
            lambda value: value.update(nearest_extents=(2, 4, 2)),
        )
        for index, change in enumerate(mutations):
            value = refusal()
            change(value)
            with self.subTest(index=index), self.assertRaises(ValueError):
                probes.validate_query_refusal(value, 32)
        for bits in (16, 32.0, True, None):
            with self.subTest(expected_bits=bits), self.assertRaises(ValueError):
                probes.validate_query_refusal(refusal(), bits)

    def test_v2_allows_only_spatial_refusal_expectations(self):
        outcomes = ("start_polygon_not_found", "end_polygon_not_found", "no_complete_corridor")
        for kind in ("collection", "wow-selection"):
            value = suite(kind)
            value["format"] = "bnav-route-probes-v2"
            self.assertEqual(probes.validate_suite(value), value)
            for outcome in outcomes:
                value = suite(kind)
                value["format"] = "bnav-route-probes-v2"
                value["probes"] = [negative_probe(outcome)]
                before = copy.deepcopy(value)
                with self.subTest(kind=kind, outcome=outcome):
                    self.assertEqual(probes.validate_suite(value), value)
                    self.assertEqual(value, before)
                value["format"] = "bnav-route-probes-v1"
                with self.assertRaises(probes.Invalid):
                    probes.validate_suite(value)
                value["probes"][0]["expect"] = {**probe()["expect"], "outcome": outcome}
                with self.assertRaises(probes.Invalid):
                    probes.validate_suite(value)
        for expectation in ({"outcome": "query_budget_exceeded"},
                            {"outcome": "query_budget_exceeded", "direct_path_blocked": False, "min_traversed_tiles": 1},
                            {"outcome": "complete"},
                            {"outcome": "no_complete_corridor", "direct_path_blocked": True},
                            {"outcome": "no_complete_corridor", "min_traversed_tiles": 1}):
            value = suite()
            value["format"] = "bnav-route-probes-v2"
            value["probes"][0]["expect"] = expectation
            with self.subTest(expectation=expectation), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)
        for limit in (None, True, -1, float("nan")):
            value = suite()
            value["format"] = "bnav-route-probes-v2"
            value["probes"] = [negative_probe()]
            value["probes"][0]["max_projection_distance"] = limit
            with self.subTest(negative_limit=limit), self.assertRaises(probes.Invalid):
                probes.validate_suite(value)

    def test_typed_spatial_refusals_require_opt_in_and_match_exactly(self):
        for kind in ("collection", "wow-selection"):
            for bits in (32, 64):
                for reason, stage in (("START_POLYGON_NOT_FOUND", "nearest_start"),
                                      ("END_POLYGON_NOT_FOUND", "nearest_end"),
                                      ("NO_COMPLETE_CORRIDOR", "find_path")):
                    outcome = reason.lower()
                    selected = negative_probe(outcome)
                    call = invocation(refusal_response(selected, refusal(reason, stage, bits)))
                    call["stderr"] = "An unrelated END_POLYGON_NOT_FOUND string must not determine the outcome"
                    with self.subTest(kind=kind, bits=bits, reason=reason):
                        self.assert_verdict(selected, call, kind, bits, "MATCH", outcome, allow_refusals=True)
                        self.assert_verdict(probe(), call, kind, bits, "ERROR")
                        self.assert_verdict(probe(), call, kind, bits, "ERROR", allow_refusals=False)
                        self.assert_verdict(probe(), call, kind, bits, "MISMATCH", outcome, allow_refusals=True)
        selected = negative_probe("end_polygon_not_found")
        self.assert_verdict(selected, invocation(refusal_response(selected)), "collection", 32,
                            "MISMATCH", "start_polygon_not_found", allow_refusals=True)

    def test_budget_refusals_are_errors_not_connectivity_expectations(self):
        for kind in ("collection", "wow-selection"):
            for bits in (32, 64):
                for stage in ("find_path", "straight_path"):
                    diagnostic = refusal("QUERY_BUDGET_EXCEEDED", stage, bits)
                    for selected in (probe(), negative_probe("no_complete_corridor")):
                        with self.subTest(kind=kind, bits=bits, stage=stage, expected=selected["expect"]):
                            result = self.assert_verdict(selected, invocation(refusal_response(selected, diagnostic)),
                                                         kind, bits, "ERROR", allow_refusals=True)
                            self.assertEqual(result.get("diagnostic"), diagnostic)
                            self.assertTrue(any("budget" in reason for reason in result["reasons"]))
                            self.assertNotIn("actual_outcome", result)

    def test_typed_refusal_transport_and_request_binding_fail_closed(self):
        selected = negative_probe()
        for code in (0, 2, False):
            self.assert_verdict(selected, invocation(refusal_response(selected), exit_code=code),
                                "collection", 32, "ERROR", allow_refusals=True)
        self.assert_verdict(selected, invocation(refusal_response(selected)),
                            "collection", 32, "ERROR", allow_refusals=1)
        for change in (lambda value: value.pop("diagnostic"),
                       lambda value: value["diagnostic"].update(complete=True),
                       lambda value: value["diagnostic"].update(reference_bits=64),
                       lambda value: value.update(requested_start=[False, 1, 0]),
                       lambda value: value.update(requested_start=[0, 1]),
                       lambda value: value.update(requested_end=[99, 1, 0]),
                       lambda value: value.update(game_qa="VERIFIED")):
            value = refusal_response(selected)
            change(value)
            self.assert_verdict(selected, invocation(value), "collection", 32, "ERROR", allow_refusals=True)
        for change in (lambda call: call.update(timed_out=True),
                       lambda call: call.update(output_truncated=True),
                       lambda call: call.update(exit_code=2, stdout="", stderr=json.dumps(refusal()))):
            call = invocation(refusal_response(selected))
            change(call)
            self.assert_verdict(selected, call, "collection", 32, "ERROR", allow_refusals=True)

    def test_valid_routes_mismatch_negative_expectations(self):
        for kind in ("collection", "wow-selection"):
            for limit, actual in ((2.0, "complete"), (0.5, "projection_limit_exceeded")):
                selected = negative_probe("no_complete_corridor")
                selected["max_projection_distance"] = limit
                self.assert_verdict(selected, invocation(response(selected, kind, 32)), kind, 32,
                                    "MISMATCH", actual, allow_refusals=True)


if __name__ == "__main__":
    unittest.main()
