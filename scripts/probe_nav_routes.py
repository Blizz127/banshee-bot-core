#!/usr/bin/env python3
"""Record bounded, named offline route expectations against an exact nav manifest.

No geometry discovery, baking, game runtime or inferred unreachable verdicts.
Query errors are errors, even when a caller intended a negative route check.
"""

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
from zoneinfo import ZoneInfo

from nav_route_metrics import measure_route, validate_projection_limit, validate_query_refusal


FORMAT = "bnav-route-probes-v1"
REPORT_FORMAT = "bnav-route-probes-v2"
REFUSALS = {"start_polygon_not_found", "end_polygon_not_found", "no_complete_corridor"}
MAX_JSON = 2 * 1024 * 1024
MAX_LOG = 1024 * 1024
WRAPPERS = {"collection": "bake_nav_collection.py", "wow-selection": "import_wow_nav.py"}
SUCCESS = {"collection": "COMPLETE_PROJECTED_PATH", "wow-selection": "SELECTED_REGION_PROJECTED_PATH"}
VERIFIED = {"collection": "VERIFIED_COLLECTION", "wow-selection": "VERIFIED_SELECTED_REGION"}


class Invalid(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, maximum):
    need(path.is_file(), f"not a regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    need(len(data) <= maximum, f"file exceeds {maximum} bytes: {path}")
    return data


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise Invalid(f"nonfinite JSON number: {value}")

    value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    need(isinstance(value, dict), "JSON root must be an object")
    return value


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def integer(value, low, high, label):
    need(type(value) is int and low <= value <= high, f"invalid {label}")
    return value


def text(value, maximum, label):
    need(isinstance(value, str) and 0 < len(value) <= maximum and value.strip() == value
         and not any(ord(c) < 32 for c in value), f"invalid {label}")


def finite(value, label):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    need(valid, f"invalid {label}")
    return value


def validate_suite(suite):
    need(isinstance(suite, dict) and suite.get("format") in (FORMAT, REPORT_FORMAT), "unsupported probe format")
    kind = suite.get("target_kind")
    need(isinstance(kind, str) and kind in WRAPPERS, "unsupported target kind")
    fields = {"format", "target_kind", "manifest_sha256", "units", "scope", "limitations", "probes"}
    if kind == "wow-selection":
        fields.add("query_flags")
        flags = suite.get("query_flags")
        need(isinstance(flags, dict) and set(flags) == {"include", "exclude"}, "explicit WoW query flags required")
        included = integer(flags["include"], 1, 65535, "include flags")
        excluded = integer(flags["exclude"], 0, 65535, "exclude flags")
        need(included & ~excluded, "all included flags are excluded")
    need(set(suite) == fields, "missing or unexpected probe suite fields")
    need(isinstance(suite["manifest_sha256"], str) and
         re.fullmatch(r"[0-9a-f]{64}", suite["manifest_sha256"]), "invalid manifest SHA-256")
    text(suite["units"], 128, "units")
    text(suite["scope"], 1024, "scope")
    need(isinstance(suite["limitations"], list) and len(suite["limitations"]) <= 64, "invalid limitations")
    for value in suite["limitations"]:
        text(value, 1024, "limitation")
    probes = suite["probes"]
    need(isinstance(probes, list) and 1 <= len(probes) <= 32, "expected 1..32 probes")
    names = set()
    for probe in probes:
        need(isinstance(probe, dict) and
             set(probe) == {"name", "start", "end", "max_projection_distance", "expect"}, "invalid probe fields")
        name = probe["name"]
        need(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name), "invalid probe name")
        need(name not in names, "duplicate probe name")
        names.add(name)
        for key in ("start", "end"):
            point = probe[key]
            need(isinstance(point, list) and len(point) == 3, f"invalid {key} point")
            for value in point:
                need(abs(finite(value, key)) <= 10_000_000, f"{key} exceeds coordinate limit")
        need(probe["max_projection_distance"] is not None, "projection limit must be explicit")
        try:
            validate_projection_limit(probe["max_projection_distance"])
        except ValueError as error:
            raise Invalid(str(error)) from error
        expect = probe["expect"]
        if (suite["format"] == REPORT_FORMAT and isinstance(expect, dict)
                and isinstance(expect.get("outcome"), str) and expect["outcome"] in REFUSALS):
            need(set(expect) == {"outcome"}, "refusal expectation must not assert ray/tile observations")
            continue
        need(isinstance(expect, dict) and set(expect) ==
             {"outcome", "direct_path_blocked", "min_traversed_tiles"}, "invalid expectation fields")
        need(expect["outcome"] in ("complete", "projection_limit_exceeded"), "unsupported expected outcome")
        need(type(expect["direct_path_blocked"]) is bool, "expected ray observation must be boolean")
        integer(expect["min_traversed_tiles"], 1, 256, "minimum traversed tiles")
    return suite


def assess(probe, invocation, kind, bits, allow_refusals=False):
    """A process refusal cannot prove non-traversability or match an expectation."""
    try:
        need(kind in SUCCESS and type(bits) is int and bits in (32, 64), "invalid assessment profile")
        need(not invocation.get("timed_out", False) and invocation.get("output_truncated") is False,
             "query timed out or output is incomplete")
        code = invocation.get("exit_code")
        need(type(code) is int and code in (0, 3), "query command failed; no route classification")
        result = decode(invocation["stdout"])
        need(result.get("game_qa") == "NOT_RUN", "query cannot establish Game QA")
        if result.get("status") == "QUERY_REFUSED":
            need(allow_refusals is True and code == 3, "native refusal requires explicit report mode and exit 3")
            diagnostic = validate_query_refusal(result.get("diagnostic"), bits)
            for key in ("start", "end"):
                values = result.get("requested_" + key)
                need(isinstance(values, list) and len(values) == 3 and all(
                    finite(a, key) == b for a, b in zip(values, probe[key])), "refusal endpoints differ from request")
            if diagnostic["reason"] == "QUERY_BUDGET_EXCEEDED":
                return {"verdict": "ERROR", "reasons": ["native query budget exhausted; connectivity unassessed"],
                        "diagnostic": diagnostic}
            outcome = diagnostic["reason"].lower()
            reasons = [] if outcome == probe["expect"]["outcome"] else ["native refusal differs from expectation"]
            return {"verdict": "MISMATCH" if reasons else "MATCH", "reasons": reasons,
                    "actual_outcome": outcome, "diagnostic": diagnostic}
        native = result.get("result")
        need(isinstance(native, dict) and native.get("complete") is True, "native route is not complete")
        need(type(native.get("reference_bits")) is int and native["reference_bits"] == bits, "native ABI differs")
        loaded = integer(native.get("loaded_tiles"), 1, 256, "loaded tiles")
        traversed = integer(native.get("traversed_tiles"), 1, loaded, "traversed tiles")
        need(type(native.get("direct_path_blocked")) is bool, "invalid native ray observation")
        metrics = measure_route(probe["start"], probe["end"], native, probe["max_projection_distance"])
        reported = result.get("route_metrics")
        need(isinstance(reported, dict) and set(reported) == set(metrics), "invalid reported route measurements")
        for key, expected in metrics.items():
            actual = reported[key]
            if isinstance(expected, list):
                same = isinstance(actual, list) and len(actual) == len(expected) and all(
                    finite(a, key) == e for a, e in zip(actual, expected))
            elif type(expected) is float:
                same = finite(actual, key) == expected
            else:
                same = type(actual) is type(expected) and actual == expected
            need(same, "reported route measurements differ from recomputation")
        within = metrics["within_projection_limit"]
        expected_status = SUCCESS[kind] if within else "PROJECTION_LIMIT_EXCEEDED"
        need(result.get("status") == expected_status and code == (0 if within else 3),
             "query exit/status disagrees with measured projection policy")
        outcome = "complete" if within else "projection_limit_exceeded"
        expected = probe["expect"]
        reasons = []
        if outcome != expected["outcome"]:
            reasons.append("route outcome differs from expectation")
        if "direct_path_blocked" in expected and native["direct_path_blocked"] != expected["direct_path_blocked"]:
            reasons.append("native direct-ray observation differs from expectation")
        if "min_traversed_tiles" in expected and traversed < expected["min_traversed_tiles"]:
            reasons.append("fewer tiles traversed than expected")
        return {"verdict": "MISMATCH" if reasons else "MATCH", "reasons": reasons,
                "actual_outcome": outcome, "route_metrics": metrics,
                "direct_path_blocked": native["direct_path_blocked"], "traversed_tiles": traversed}
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as error:
        return {"verdict": "ERROR", "reasons": [str(error)]}


def identity(path, maximum=128 * 1024 * 1024):
    data = read(path, maximum)
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def invoke(argv, output, number):
    """Retain real commands and bounded logs; kill only this command's group."""
    stem = f"{number:03d}"
    stdout, stderr = output / (stem + ".stdout"), output / (stem + ".stderr")
    record = {"argv": list(map(str, argv)), "cwd": str(output), "timeout_seconds": 180}

    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_LOG, MAX_LOG))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            process = subprocess.Popen(record["argv"], cwd=output, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True, preexec_fn=limits)
            try:
                process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            record["exit_code"] = process.returncode
        except OSError as error:
            record.update(exit_code=None, launch_error=str(error))
    record["output_truncated"] = False
    for name, path in (("stdout", stdout), ("stderr", stderr)):
        data = read(path, MAX_LOG)
        record[name] = data.decode(errors="replace")
        record[name + "_file"] = path.name
        record[name + "_sha256"] = sha(data)
        record["output_truncated"] |= len(data) >= MAX_LOG
    return record


def run(args):
    suite_path, manifest_path, backend = (p.expanduser().resolve(strict=True)
                                          for p in (args.probes, args.manifest, args.backend))
    suite_bytes, manifest_bytes = read(suite_path, MAX_JSON), read(manifest_path, MAX_JSON)
    suite = validate_suite(decode(suite_bytes))
    need(sha(manifest_bytes) == suite["manifest_sha256"], "target manifest differs from probe suite")
    manifest = decode(manifest_bytes)
    kind = suite["target_kind"]
    reports = suite["format"] == REPORT_FORMAT
    formats = ("bnav-collection-v1", "bnav-collection-batch-v1") if kind == "collection" else ("bnav-wow-selection-v1",)
    need(manifest.get("format") in formats, "target format differs from probe suite")
    bits = manifest.get("reference_bits")
    need(type(bits) is int and bits in (32, 64), "invalid target ABI")
    if kind == "collection":
        need(suite["units"] == manifest.get("coordinates", {}).get("units"), "probe units differ from collection declaration")
    need(identity(backend)["sha256"] == manifest["tools"]["backend"]["sha256"], "backend differs from target manifest")
    scripts = Path(__file__).resolve().parent
    wrapper = scripts / WRAPPERS[kind]
    inputs = (suite_path, manifest_path, backend, Path(__file__).resolve(), wrapper,
              scripts / "nav_route_metrics.py", Path(sys.executable).resolve())
    before = [identity(p) for p in inputs]
    output = args.output_dir.expanduser().resolve()
    need(not output.exists() and not any((p / ".git").exists() for p in (output, *output.parents)),
         "probe output must be fresh and outside Git")
    need(not output.is_relative_to(manifest_path.parent), "probe output must be outside the target collection")
    output.mkdir(parents=True)
    (output / "probes.json").write_bytes(suite_bytes)
    receipt = {"format": "bnav-route-probe-results-v1", "status": "INCOMPLETE",
               "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
               "target_kind": kind, "manifest_sha256": suite["manifest_sha256"],
               "suite_sha256": sha(suite_bytes), "inputs_before": before, "commands": [],
               "probes": [{"name": p["name"], "verdict": "NOT_RUN"} for p in suite["probes"]],
               "errors": [], "game_qa": "NOT_RUN", "native_adapter_compatibility": "NOT_VERIFIED",
               "calibration": "NOT_VERIFIED", "unreachable_classification": "NOT_SUPPORTED",
               "native_refusal_diagnostics": reports}
    save(output / "requested.json", receipt)
    prefix = [sys.executable, "-E", "-s", "-B", wrapper]

    def unchanged():
        need([identity(p) for p in inputs] == before, "probe inputs or tools changed during run")

    def command(argv):
        index = len(receipt["commands"])
        record = invoke(argv, output, index)
        path = output / f"{index:03d}.json"
        save(path, record)
        receipt["commands"].append({"path": path.name, "sha256": sha(path.read_bytes()), "exit_code": record["exit_code"]})
        return record

    def check():
        record = command([*prefix, "check", manifest_path])
        need(record["exit_code"] == 0 and not record.get("timed_out") and not record["output_truncated"],
             "target integrity check failed")
        verified = decode(record["stdout"])
        need(verified.get("status") == VERIFIED[kind] and verified.get("game_qa") == "NOT_RUN",
             "unexpected target integrity result")

    try:
        unchanged()
        check()
        for index, probe in enumerate(suite["probes"]):
            unchanged()
            argv = [*prefix, "query", manifest_path, "--backend", backend, "--start", *probe["start"],
                    "--end", *probe["end"], "--max-projection-distance", probe["max_projection_distance"]]
            if kind == "wow-selection":
                argv += ["--include-flags", suite["query_flags"]["include"], "--exclude-flags", suite["query_flags"]["exclude"]]
            if reports:
                argv += ["--diagnostic-refusals"]
            record = command(argv)
            verdict = assess(probe, record, kind, bits, allow_refusals=reports)
            receipt["probes"][index].update(verdict, command=len(receipt["commands"]) - 1)
            need(verdict["verdict"] != "ERROR", f"probe {probe['name']}: {'; '.join(verdict['reasons'])}")
        check()
        unchanged()
        receipt["status"] = "MISMATCH" if any(p["verdict"] == "MISMATCH" for p in receipt["probes"]) else "MATCHED_EXPECTATIONS"
    except (ValueError, OSError, KeyError, TypeError) as error:
        receipt["status"] = "ERROR"
        receipt["errors"].append(str(error))
    try:
        receipt["inputs_after"] = [identity(p) for p in inputs]
        need(receipt["inputs_after"] == before, "probe inputs or tools changed during run")
    except (ValueError, OSError) as error:
        receipt["status"] = "ERROR"
        receipt["errors"].append(str(error))
    receipt["counts"] = {state: sum(p["verdict"] == state for p in receipt["probes"])
                         for state in ("MATCH", "MISMATCH", "ERROR", "NOT_RUN")}
    receipt["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    save(output / "result.json", receipt)
    print(json.dumps({"status": receipt["status"], "result": str(output / "result.json"),
                      "counts": receipt["counts"], "errors": receipt["errors"], "game_qa": "NOT_RUN"}))
    return {"MATCHED_EXPECTATIONS": 0, "MISMATCH": 4, "ERROR": 2}[receipt["status"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("probes", "manifest", "backend", "output-dir"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"probe_nav_routes: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
