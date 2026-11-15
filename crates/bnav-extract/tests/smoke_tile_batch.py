#!/usr/bin/env python3
"""Focused batch protocol smoke; synthetic files and receipts stay outside Git.

This runner executes only when explicitly invoked. It builds one small negative-
origin seam-wall fixture, compares old per-cell output, and sends bounded bad
frames from private fake backends. It never opens game assets or a game runtime.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import time
from zoneinfo import ZoneInfo


HEADER = 0x54424E42
FOOTER = 0x444E4542
MAX_TILE_BYTES = 64 * 1024 * 1024
SETTINGS = ["0.5", "0.2", "2", "0.6", "0.9", "45"]
GRID = ["-20", "-20", "0", "3", "40"]
CELLS = [(0, 0), (0, 1), (1, 0), (1, 1)]
BUILT_CELLS = [(0, 0), (1, 0)]
EXPECTED_COMMANDS = 32
EXPECTED_CHECKS = 29
PROTOCOL_ERRORS = {
    "wrong-magic": "unsupported batch header",
    "wrong-version": "unsupported batch header",
    "unsupported-abi": "unsupported batch header",
    "payload-abi-mismatch": "section lengths",
    "wrong-count": "unsupported batch header",
    "wrong-coordinate": "cell order or coordinates",
    "wrong-status": "invalid batch cell status or payload length",
    "empty-with-payload": "invalid batch cell status or payload length",
    "oversized-length": "invalid batch cell status or payload length",
    "truncated-frame": "truncated batch stream",
    "truncated-payload": "truncated batch tile",
    "trailing-bytes": "trailing bytes",
    "missing-footer": "truncated batch stream",
    "wrong-footer-count": "completion footer",
    "nonzero-child-exit": "backend failed after stream readback",
    "retained-before-truncation": "truncated batch stream",
}
GEOMETRY = """v -20 0 -20
v 20 0 -20
v 20 0 0
v -20 0 0
f 1 3 2
f 1 4 3
v 0 0 -15
v 0 3 -15
v 0 3 -5
v 0 0 -5
f 5 6 7
f 5 7 8
"""


class Failure(ValueError):
    pass


def need(value, message):
    if not value:
        raise Failure(message)


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_bytes(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def words(*values):
    return struct.pack("<" + "I" * len(values), *values)


def header(bits, count=1, magic=HEADER, version=1):
    return words(magic, version, bits, count)


def cell(x=0, z=0, status=3, data=b"", length=None):
    return words(x, z, status, len(data) if length is None else length) + data


def footer(count=1, built=0, empty=1):
    return words(FOOTER, count, built, empty)


def protocol_cases(bits, raw):
    """Each response is small; declared oversized lengths allocate no payload."""
    empty = cell()
    complete_empty = header(bits) + empty + footer()
    return [
        ("wrong-magic", header(bits, magic=0) + empty + footer(), 0, (0, 0, 0, 0), False),
        ("wrong-version", header(bits, version=2) + empty + footer(), 0, (0, 0, 0, 0), False),
        ("unsupported-abi", header(16) + empty + footer(), 0, (0, 0, 0, 0), False),
        ("payload-abi-mismatch", header(64 if bits == 32 else 32) + cell(status=0, data=raw)
         + footer(built=1, empty=0), 0, (0, 0, 0, 0), False),
        ("wrong-count", header(bits, count=2) + empty + footer(), 0, (0, 0, 0, 0), False),
        ("wrong-coordinate", header(bits) + cell(x=1) + footer(), 0, (0, 0, 0, 0), False),
        ("wrong-status", header(bits) + cell(status=1) + footer(), 0, (0, 0, 0, 0), False),
        ("empty-with-payload", header(bits) + cell(data=b"x") + footer(), 0, (0, 0, 0, 0), False),
        ("oversized-length", header(bits) + cell(status=0, length=MAX_TILE_BYTES + 1),
         0, (0, 0, 0, 0), False),
        ("truncated-frame", header(bits) + words(0, 0), 0, (0, 0, 0, 0), False),
        ("truncated-payload", header(bits) + cell(status=0, data=raw[:-1], length=len(raw)),
         0, (0, 0, 0, 0), False),
        ("trailing-bytes", complete_empty + b"x", 0, (0, 0, 0, 0), False),
        ("missing-footer", header(bits) + empty, 0, (0, 0, 0, 0), False),
        ("wrong-footer-count", header(bits) + empty + footer(count=2), 0, (0, 0, 0, 0), False),
        ("nonzero-child-exit", complete_empty, 7, (0, 0, 0, 0), False),
        ("retained-before-truncation", header(bits, count=2) + cell(status=0, data=raw) + words(1, 0),
         0, (0, 1, 0, 0), True),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("extractor", "backend", "baseline-backend", "output-dir"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    need(not any((parent / ".git").exists() for parent in (root, *root.parents)),
         "smoke output must be external to every Git checkout")
    root.mkdir(parents=True, exist_ok=False)
    (root / "commands").mkdir()
    (root / "fake-backends").mkdir()
    extractor = args.extractor.expanduser().resolve(strict=True)
    backend = args.backend.expanduser().resolve(strict=True)
    baseline = args.baseline_backend.expanduser().resolve(strict=True)
    source = root / "seam-wall.obj"
    write_bytes(source, GEOMETRY.encode())
    result = {"status": "FAIL", "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
              "scope": "bounded original synthetic batch protocol and per-cell equivalence",
              "game_qa": "NOT_RUN", "whole_map_coverage": False,
              "native_ffxi_jobs": "NOT_RUN", "aggregate_128mib_boundary": "NOT_EXERCISED",
              "expected_commands": EXPECTED_COMMANDS,
              "expected_checks": EXPECTED_CHECKS, "commands": [], "checks": [], "errors": [],
              "inputs_before": [], "inputs_after": []}
    pinned = {}

    def pin(path):
        record = identity(path)
        need(str(path) not in pinned or pinned[str(path)] == record, "pinned input changed before reuse")
        if str(path) not in pinned:
            pinned[str(path)] = record
            result["inputs_before"].append(record)

    def run(name, argv, expected=0):
        argv = list(map(str, argv))
        started = time.monotonic()
        receipt = {"name": name, "argv": argv, "expected_exit": expected, "stdin": "empty"}
        # Own process group only: a timeout must not strand a fake/backend child
        # holding inherited pipes or touch an unrelated worker/session.
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(input=b"", timeout=90)
            receipt.update(exit_code=process.returncode, stdout=stdout.decode(errors="replace"),
                           stderr=stderr.decode(errors="replace"))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            receipt.update(exit_code=None, stdout=stdout.decode(errors="replace"),
                           stderr=stderr.decode(errors="replace"), timeout=True)
        receipt["elapsed_seconds"] = time.monotonic() - started
        relative = f"commands/{len(result['commands']):02}-{name}.json"
        write_json(root / relative, receipt)
        result["commands"].append({"name": name, "receipt": relative, "exit_code": receipt["exit_code"]})
        need(receipt["exit_code"] == expected,
             f"{name}: expected exit {expected}, got {receipt['exit_code']}; see {relative}")
        return receipt

    def passed(name, **details):
        result["checks"].append({"name": name, "passed": True, **details})

    def batch_command(selected_backend, destination, bounds=(0, 1, 0, 1), settings=SETTINGS):
        return [extractor, "build-tiles-obj", selected_backend, source, destination,
                *GRID, *bounds, *settings]

    def historical_request(directory):
        request = directory / "requested.json"
        need(request.is_file(), f"missing historical request in {directory}")
        value = json.loads(request.read_text())
        need(value.get("format") == "bnav-tile-batch-v1" and value.get("status") == "INCOMPLETE",
             "historical request must remain INCOMPLETE")
        need(value.get("reference_bits") is None and value.get("built") == 0 and value.get("empty") == 0,
             "historical request unexpectedly records completed cells")
        entries = value.get("tiles")
        need(isinstance(entries, list) and value.get("requested_cells") == len(entries)
             and all(entry.get("status") == "missing" for entry in entries), "historical inventory changed")
        pin(request)

    def complete_manifest(directory, expected_cells, expected_built, bits):
        historical_request(directory)
        value = json.loads((directory / "manifest.json").read_text())
        need(value.get("format") == "bnav-tile-batch-v1" and value.get("status") == "COMPLETE",
             "unexpected batch manifest format/status")
        need(value.get("reference_bits") == bits and value.get("game_qa") == "NOT_RUN",
             "batch manifest ABI/QA mismatch")
        need(value.get("requested_cells") == len(expected_cells)
             and value.get("built") == len(expected_built)
             and value.get("empty") == len(expected_cells) - len(expected_built), "batch counts differ")
        entries = value.get("tiles")
        need(isinstance(entries, list) and [(v.get("x"), v.get("z")) for v in entries] == expected_cells,
             "batch order is not the requested x-major/z-minor rectangle")
        wanted_files = {"requested.json", "manifest.json"}
        for entry in entries:
            coordinate = (entry["x"], entry["z"])
            if coordinate in expected_built:
                name = f"{coordinate[0]}_{coordinate[1]}.navtile"
                tile = directory / name
                need(entry.get("status") == "built" and entry.get("path") == name and tile.is_file(),
                     "missing built tile or incorrect relative path")
                raw = tile.read_bytes()
                need(type(entry.get("bytes")) is int and entry["bytes"] == len(raw), "built tile byte count mismatch")
                need(struct.unpack_from("<IIiii", raw) == (0x444E4156, 7, *coordinate, 0),
                     "raw tile coordinate/header mismatch")
                wanted_files.add(name)
            else:
                need(entry.get("status") == "empty" and "path" not in entry and "bytes" not in entry,
                     "empty cell unexpectedly declares a payload")
        need({p.name for p in directory.iterdir()} == wanted_files, "unexpected batch output inventory")
        return value

    def fake_backend(name, response, exit_code, bits):
        directory = root / "fake-backends" / name
        directory.mkdir()
        binary, payload, marker = directory / "backend.py", directory / "response.bin", directory / "invocations.jsonl"
        write_bytes(payload, response)
        program = f"""#!{sys.executable}
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent
with (root / 'invocations.jsonl').open('a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:] == ['--version']:
    print('bnav-recast synthetic-protocol-fixture reference_bits={bits}')
    raise SystemExit(0)
sys.stdin.buffer.read()
sys.stdout.buffer.write((root / 'response.bin').read_bytes())
sys.stdout.buffer.flush()
raise SystemExit({exit_code})
"""
        write_bytes(binary, program.encode())
        binary.chmod(0o700)
        pin(binary)
        pin(payload)
        return binary, marker

    try:
        for path in (Path(__file__).resolve(), Path(sys.executable).resolve(), extractor, backend, baseline, source):
            pin(path)
        versions = []
        for label, path in (("batch-backend-version", backend), ("baseline-backend-version", baseline)):
            receipt = run(label, [path, "--version"])
            found = re.search(r"\breference_bits=(32|64)\b", receipt["stdout"])
            need(found is not None, f"{label}: missing reference ABI")
            versions.append(int(found.group(1)))
        need(versions[0] == versions[1], "batch and baseline backends must use the same reference ABI")
        bits = versions[0]
        result["reference_bits"] = bits

        mixed = root / "mixed"
        run("mixed-batch", batch_command(backend, mixed))
        result["mixed_manifest"] = complete_manifest(mixed, CELLS, BUILT_CELLS, bits)
        passed("mixed-batch", built=2, empty=2, requested_order=CELLS, origin=[-20, -20])

        old = root / "baseline-cells"
        old.mkdir()
        for x, z in CELLS:
            tile = old / f"{x}_{z}.navtile"
            built = (x, z) in BUILT_CELLS
            run(f"baseline-{x}-{z}", [extractor, "build-tile-obj", baseline, source, tile,
                                       *GRID, x, z, *SETTINGS], 0 if built else 3)
            if built:
                need(tile.read_bytes() == (mixed / tile.name).read_bytes(), "batch differs from old per-cell tile bytes")
                passed(f"baseline-{x}-{z}", sha256=identity(tile)["sha256"], exact_bytes=True)
            else:
                need(not tile.exists() and not (mixed / tile.name).exists(), "empty cell created output")
                passed(f"baseline-{x}-{z}", empty_in_both=True)

        routes = []
        for label, selected_backend, directory in (("batch-query", backend, mixed), ("baseline-query", baseline, old)):
            receipt = run(label, [selected_backend, "query-tiles", -20, -0.2, -20, 20,
                                  -18, 0, -10, 18, 0, -10,
                                  *[directory / f"{x}_{z}.navtile" for x, z in BUILT_CELLS]])
            routes.append(json.loads(receipt["stdout"]))
        need(routes[0] == routes[1], "batch path query differs from old per-cell query")
        route = routes[0]
        need(route.get("complete") is True and route.get("direct_path_blocked") is True
             and route.get("loaded_tiles") == 2 and route.get("traversed_tiles") == 2,
             "seam-wall path did not cross two tiles and detour")
        points = route["points"]
        need(len(points) > 2, "wall detour needs an intermediate point")
        for a, b in zip(points, points[1:]):
            if min(a[0], b[0]) <= 0 <= max(a[0], b[0]):
                if a[0] == b[0]:
                    need(max(a[2], b[2]) < -15 or min(a[2], b[2]) > -5, "path overlaps seam wall")
                else:
                    crossing = a[2] + (-a[0]) / (b[0] - a[0]) * (b[2] - a[2])
                    need(crossing < -15 or crossing > -5, "path crosses seam wall")
        passed("cross-seam-query-equivalence", native_result=route)

        empty = root / "all-empty"
        run("all-empty-default-settings", batch_command(backend, empty, (8, 11, 8, 11), []))
        complete_manifest(empty, [(x, z) for x in range(8, 12) for z in range(8, 12)], [], bits)
        passed("all-empty-default-settings", requested=16, built=0, empty=16)

        for name, pairs, diagnostic in (
            ("native-duplicate-cells", [0, 0, 0, 0], "duplicate batch tile coordinates"),
            ("native-too-many-cells", [v for x in range(17) for v in (x, 0)], "1..16 coordinate pairs"),
        ):
            receipt = run(name, [backend, "build-tiles", *SETTINGS, *GRID, *pairs], 2)
            need(receipt["stdout"] == "", f"{name}: refusal emitted protocol bytes")
            need(diagnostic in receipt["stderr"], f"{name}: wrong refusal diagnostic")
            passed(name, protocol_bytes=0, empty_stdin=True)

        guard, marker = fake_backend("argument-guard", header(bits) + cell() + footer(), 0, bits)
        existing = root / "existing-output"
        existing.mkdir()
        sentinel = existing / "sentinel.txt"
        write_bytes(sentinel, b"existing output must remain unchanged\n")
        pin(sentinel)
        git_marker = root / "synthetic-git-ancestor"
        git_marker.mkdir()
        # An external Git-worktree indicator exercises ancestor checks without
        # creating a real repository or risking files in the project checkout.
        write_bytes(git_marker / ".git", b"gitdir: /nonexistent-synthetic-git-metadata\n")
        pin(git_marker / ".git")
        invalid_arguments = [
            ("too-many-cells", root / "over-limit", (0, 16, 0, 0), "rectangle must contain"),
            ("inverted-range", root / "inverted", (1, 0, 0, 0), "rectangle must contain"),
            ("existing-output", existing, (0, 0, 0, 0), "already exists"),
            ("git-ancestor", git_marker / "refused-output", (0, 0, 0, 0), "outside Git"),
        ]
        for name, destination, bounds, diagnostic in invalid_arguments:
            receipt = run(name, batch_command(guard, destination, bounds), 2)
            need(diagnostic in receipt["stderr"], f"{name}: wrong refusal diagnostic")
            need(not marker.exists(), f"{name}: invalid arguments dispatched the backend")
            if destination == existing:
                need({p.name for p in existing.iterdir()} == {"sentinel.txt"}, "existing output gained files")
                need(identity(sentinel) == pinned[str(sentinel)], "existing output was changed")
            else:
                need(not destination.exists(), f"{name}: invalid arguments created an output directory")
            passed(name, backend_dispatched=False)

        raw_path = old / "0_0.navtile"
        raw = raw_path.read_bytes()
        pin(raw_path)
        need(struct.unpack_from("<I", raw, 32)[0] > 0, "ABI mismatch fixture requires nonzero link count")
        for name, response, child_exit, bounds, retained_first in protocol_cases(bits, raw):
            fake, marker = fake_backend(name, response, child_exit, bits)
            destination = root / ("bad-" + name)
            receipt = run(name, batch_command(fake, destination, bounds), 2)
            need(PROTOCOL_ERRORS[name] in receipt["stderr"], f"{name}: wrong protocol failure diagnostic")
            need(marker.is_file(), f"{name}: fake backend was not dispatched")
            historical_request(destination)
            need(not (destination / "manifest.json").exists(), f"{name}: failure produced a final manifest")
            if retained_first:
                need((destination / "0_0.navtile").read_bytes() == raw, "first completed tile was not retained exactly")
                need(not (destination / "1_0.navtile").exists(), "truncated frame created a second tile")
            passed(name, final_manifest_absent=True, completed_tile_retained=retained_first)
        need(len(result["commands"]) == EXPECTED_COMMANDS and len(result["checks"]) == EXPECTED_CHECKS,
             "smoke command/check inventory drifted")
        result["status"] = "PASS"
    except (Failure, OSError, ValueError, KeyError, TypeError, struct.error) as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        try:
            result["inputs_after"] = [identity(Path(record["path"])) for record in result["inputs_before"]]
            need(result["inputs_before"] == result["inputs_after"], "pinned inputs changed during smoke")
            result["inputs_unchanged"] = True
        except (Failure, OSError) as error:
            result["status"] = "FAIL"
            result["errors"].append(f"input readback: {error}")
        result["command_count"] = len(result["commands"])
        result["passed_check_count"] = len(result["checks"])
        result["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
        write_json(root / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(root / "result.json"),
                      "command_count": result["command_count"], "passed_check_count": result["passed_check_count"],
                      "errors": result["errors"], "game_qa": "NOT_RUN"}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Failure, OSError) as error:
        print(f"smoke_tile_batch: {error}", file=sys.stderr)
        sys.exit(2)
