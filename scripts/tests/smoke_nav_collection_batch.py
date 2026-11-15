#!/usr/bin/env python3
"""Synthetic opt-in collection batching smoke; run once per supplied native ABI.

All geometry, fake executables, receipts, failed imports and deliberately altered
copies are retained outside Git. No game files, servers or resource benchmarks.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
from zoneinfo import ZoneInfo


FORMAT = "bnav-collection-batch-v1"
SETTINGS = [0.5, 0.2, 2, 0.6, 0.9, 45]
EXPECTED_COMMANDS = 37
EXPECTED_CHECKS = 31
TAMPERS = [
    "receipt-hash", "receipt-command", "receipt-failed", "receipt-truncated", "receipt-stdout",
    "missing-result", "result-hash", "missing-request", "request-hash", "request-schema",
    "request-settings", "result-settings", "result-counts", "result-order", "result-coverage",
    "result-abi", "batch-bounds", "batch-membership", "raw-hash", "raw-layer", "empty-file", "raw-symlink",
]
TAMPER_ERRORS = {
    "receipt-hash": "batch receipt hash mismatch",
    "receipt-command": "batch receipt grid/settings mismatch",
    "receipt-failed": "batch invocation did not succeed",
    "receipt-truncated": "batch invocation output is truncated",
    "receipt-stdout": "batch stdout differs from retained native result",
    "missing-result": "not a regular file",
    "result-hash": "batch result hash mismatch",
    "missing-request": "not a regular file",
    "request-hash": "batch request hash mismatch",
    "request-schema": "invalid native batch format/status",
    "request-settings": "native batch settings differ",
    "result-settings": "native batch settings differ",
    "result-counts": "native batch count summary differs",
    "result-order": "native batch cell order/coverage differs",
    "result-coverage": "native batch requested coverage differs",
    "result-abi": "native batch abi differs",
    "batch-bounds": "batch rectangle differs from plan",
    "batch-membership": "collection tile differs from bound batch result/hash",
    "raw-hash": "collection tile differs from bound batch result/hash",
    "raw-layer": "detour tile coordinates/layer differ",
    "empty-file": "batch directory has unexpected or missing output",
    "raw-symlink": "batch file escapes collection directory",
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


def need(condition, message):
    if not condition:
        raise Failure(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": digest(data)}


def load(path):
    return json.loads(path.read_text())


def save(path, value, *, replace=False):
    # Replacement is used only in deliberately altered external copies.
    with path.open("w" if replace else "x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def create(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def expected_plan(bounds, maximum):
    xmin, xmax, zmin, zmax = bounds
    nx = min(xmax - xmin + 1, maximum)
    nz = min(zmax - zmin + 1, maximum // nx)
    return [[x, min(x + nx - 1, xmax), z, min(z + nz - 1, zmax)]
            for z in range(zmin, zmax + 1, nz) for x in range(xmin, xmax + 1, nx)]


def native_cells(bounds):
    xmin, xmax, zmin, zmax = bounds
    return [(x, z) for x in range(xmin, xmax + 1) for z in range(zmin, zmax + 1)]


def top_cells(bounds):
    xmin, xmax, zmin, zmax = bounds
    return [(x, z) for z in range(zmin, zmax + 1) for x in range(xmin, xmax + 1)]


def copy_collection(source, destination, omitted=()):
    omitted = set(omitted)
    def ignore(directory, names):
        return [name for name in names if (Path(directory) / name).relative_to(source).as_posix() in omitted]
    shutil.copytree(source, destination, ignore=ignore)


def seal_receipt(root, batch, receipt):
    save(root / batch["receipt"], receipt, replace=True)
    batch["receipt_sha256"] = digest((root / batch["receipt"]).read_bytes())


def seal_result(root, batch, result):
    save(root / batch["result"], result, replace=True)
    batch["result_sha256"] = digest((root / batch["result"]).read_bytes())
    receipt = load(root / batch["receipt"])
    receipt["stdout"] = json.dumps(result, separators=(",", ":")) + "\n"
    seal_receipt(root, batch, receipt)
    need(json.loads(receipt["stdout"]) == load(root / batch["result"]), "semantic fixture stdout reseal failed")


def seal_request(root, batch, request):
    save(root / batch["request"], request, replace=True)
    batch["request_sha256"] = digest((root / batch["request"]).read_bytes())


def mutate(source, target, name, bits):
    original = load(source / "manifest.json")
    first = original["batches"][0]
    first_raw = next(entry for entry in original["tiles"] if entry["status"] == "built") if name != "batch-membership" else None
    omitted = []
    if name == "missing-result":
        omitted = [first["result"]]
    elif name == "missing-request":
        omitted = [first["request"]]
    elif name == "raw-symlink":
        omitted = [first_raw["path"]]
    copy_collection(source, target, omitted)
    manifest = load(target / "manifest.json")
    batch = manifest["batches"][0]
    receipt = load(target / batch["receipt"])
    if name == "receipt-hash":
        with (target / batch["receipt"]).open("ab") as stream:
            stream.write(b" ")
    elif name == "receipt-command":
        receipt["argv"][14] = "0.75"
        seal_receipt(target, batch, receipt)
    elif name == "receipt-failed":
        receipt["exit_code"] = 2
        seal_receipt(target, batch, receipt)
    elif name == "receipt-truncated":
        receipt["output_truncated"] = True
        seal_receipt(target, batch, receipt)
    elif name == "receipt-stdout":
        changed = load(target / batch["result"])
        changed["empty"] += 1
        receipt["stdout"] = json.dumps(changed)
        seal_receipt(target, batch, receipt)
    elif name in ("missing-result", "missing-request"):
        pass
    elif name in ("result-hash", "request-hash"):
        field = name.split("-")[0]
        with (target / batch[field]).open("ab") as stream:
            stream.write(b" ")
    elif name in ("request-schema", "request-settings"):
        request = load(target / batch["request"])
        if name == "request-schema":
            request["status"] = "COMPLETE"
        else:
            request["settings"][0] = 0.75
        seal_request(target, batch, request)
    elif name.startswith("result-"):
        result = load(target / batch["result"])
        if name == "result-settings":
            result["settings"][0] = 0.75
        elif name == "result-counts":
            result["built"] += 1
        elif name == "result-order":
            result["tiles"][0], result["tiles"][1] = result["tiles"][1], result["tiles"][0]
        elif name == "result-coverage":
            removed = result["tiles"].pop()
            result["requested_cells"] -= 1
            result[removed["status"]] -= 1
        elif name == "result-abi":
            result["reference_bits"] = 64 if bits == 32 else 32
        else:
            raise Failure(f"unimplemented result tamper: {name}")
        seal_result(target, batch, result)
    elif name == "batch-bounds":
        batch["bounds"][1] += 1
    elif name == "batch-membership":
        victim = next(entry for entry in manifest["tiles"] if entry["batch"] != 0)
        victim["batch"] = 0
    elif name in ("raw-hash", "raw-layer"):
        entry = next(item for item in manifest["tiles"] if item["status"] == "built")
        path = target / entry["path"]
        data = bytearray(path.read_bytes())
        if name == "raw-hash":
            data[-1] ^= 1
        else:
            struct.pack_into("<i", data, 16, 1)
            entry["sha256"] = digest(data)
            entry["bytes"] = len(data)
        path.write_bytes(data)
    elif name == "empty-file":
        empty = next(item for item in manifest["tiles"] if item["status"] == "empty")
        path = target / f"batches/{empty['batch']:04}/{empty['x']}_{empty['z']}.navtile"
        create(path, (source / first_raw["path"]).read_bytes())
    elif name == "raw-symlink":
        (target / first_raw["path"]).symlink_to(source / first_raw["path"])
    else:
        raise Failure(f"unknown tamper: {name}")
    save(target / "manifest.json", manifest, replace=True)
    # Prove resealed fixtures reach semantic checks rather than a stale digest.
    if name in {"receipt-command", "receipt-failed", "receipt-truncated", "receipt-stdout",
                "request-schema", "request-settings", "result-settings", "result-counts",
                "result-order", "result-coverage", "result-abi"}:
        for field in ("receipt", "request", "result"):
            need(digest((target / batch[field]).read_bytes()) == batch[field + "_sha256"],
                 f"{name}: resealing left a stale {field} hash")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-script", type=Path,
                        default=Path(__file__).resolve().parents[1] / "bake_nav_collection.py")
    for option in ("extractor", "backend", "output-dir"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    need(not any((p / ".git").exists() for p in (root, *root.parents)), "evidence must stay outside Git")
    root.mkdir(parents=True, exist_ok=False)
    (root / "commands").mkdir()
    (root / "tampered").mkdir()
    script, extractor, backend = (p.expanduser().resolve(strict=True)
                                  for p in (args.collection_script, args.extractor, args.backend))
    geometry, source = root / "seam-wall.obj", root / "source.json"
    create(geometry, GEOMETRY.encode())
    save(source, {"format": "bnav-geometry-v1", "game": "synthetic", "zone": "batch-collection-seam-wall",
                  "geometry": {"path": geometry.name, "sha256": digest(geometry.read_bytes())},
                  "coordinates": {"up_axis": "Y", "units": "synthetic metres", "transform": "identity"},
                  "coverage": {"scope": "original 40 by 20 floor with a seam wall",
                               "limitations": ["Synthetic geometry only; no game runtime or full-map claim"]},
                  "provenance": {"classification": "synthetic", "description": "Original focused test fixture"}})
    result = {"status": "FAIL", "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
              "scope": "synthetic opt-in collection batch integration", "game_qa": "NOT_RUN",
              "native_ffxi_jobs": "NOT_RUN", "later_batch_failure_after_success": "NOT_EXERCISED",
              "expected_commands": EXPECTED_COMMANDS, "expected_checks": EXPECTED_CHECKS,
              "commands": [], "checks": [], "errors": [], "inputs_before": []}
    pinned = {}

    def pin(path):
        record = identity(path)
        if str(path) in pinned:
            need(record == pinned[str(path)], "pinned source changed before reuse")
        else:
            pinned[str(path)] = record
            result["inputs_before"].append(record)

    def pin_tree(path):
        for entry in sorted(path.rglob("*")):
            if entry.is_file():
                pin(entry)

    def passed(name, **details):
        result["checks"].append({"name": name, "passed": True, **details})

    def run(name, argv, expected=0):
        argv = list(map(str, argv))
        record = {"name": name, "argv": argv, "expected_exit": expected}
        started = time.monotonic()
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=180)
            record.update(exit_code=process.returncode, stdout=stdout.decode(errors="replace"),
                          stderr=stderr.decode(errors="replace"))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            record.update(exit_code=None, stdout=stdout.decode(errors="replace"), stderr=stderr.decode(errors="replace"),
                          timeout=True)
        record["elapsed_seconds"] = time.monotonic() - started
        relative = f"commands/{len(result['commands']):02}-{name}.json"
        save(root / relative, record)
        result["commands"].append({"name": name, "receipt": relative, "exit_code": record["exit_code"]})
        need(record["exit_code"] == expected,
             f"{name}: expected exit {expected}, got {record['exit_code']}; see {relative}")
        return record

    def bake(directory, batch_cells=None, bounds=(0, 1, 0, 1), selected_extractor=extractor):
        command = [sys.executable, script, "bake", "--source", source, "--extractor", selected_extractor,
                   "--backend", backend, "--output-dir", directory, "--origin-x", -20, "--origin-z", -20,
                   "--min-y", 0, "--max-y", 3, "--tile-cells", 40,
                   "--x-min", bounds[0], "--x-max", bounds[1], "--z-min", bounds[2], "--z-max", bounds[3],
                   "--settings", *SETTINGS]
        return command if batch_cells is None else [*command, "--batch-cells", batch_cells]

    def check(directory):
        return [sys.executable, script, "check", directory / "manifest.json"]

    def query(directory):
        return [sys.executable, script, "query", directory / "manifest.json", "--backend", backend,
                "--start", -18, 0, -10, "--end", 18, 0, -10]

    def inspect_batch_collection(directory, bounds, maximum, bits):
        manifest = load(directory / "manifest.json")
        need(manifest["format"] == FORMAT and manifest["status"] == "COMPLETE" and manifest["errors"] == [],
             "unexpected batch collection format/status")
        need(manifest["batch_cells"] == maximum and manifest["reference_bits"] == bits, "batch policy/ABI mismatch")
        plan = expected_plan(bounds, maximum)
        batches = manifest["batches"]
        need([entry["id"] for entry in batches] == list(range(len(plan)))
             and [entry["bounds"] for entry in batches] == plan, "batch planner differs from contract")
        need([(entry["x"], entry["z"]) for entry in manifest["tiles"]] == top_cells(bounds),
             "top collection inventory must retain legacy z-major order")
        indexed = {(entry["x"], entry["z"]): entry for entry in manifest["tiles"]}
        seen = set()
        for batch in batches:
            number = batch["id"]
            prefix = f"batches/{number:04d}"
            need(batch["receipt"] == f"receipts/batch-{number:04d}.json"
                 and batch["request"] == prefix + "/requested.json"
                 and batch["result"] == prefix + "/manifest.json", "unexpected batch receipt paths")
            for field in ("receipt", "request", "result"):
                need(digest((directory / batch[field]).read_bytes()) == batch[field + "_sha256"], "batch file hash mismatch")
            receipt, requested, native = (load(directory / batch[field]) for field in ("receipt", "request", "result"))
            need(receipt["exit_code"] == 0 and receipt["output_truncated"] is False
                 and json.loads(receipt["stdout"]) == native, "native receipt/result disagreement")
            argv = receipt["argv"]
            need(len(argv) == 20 and argv[:4] == [str(extractor), "build-tiles-obj", str(backend), str(geometry)]
                 and Path(argv[4]).as_posix().endswith("/" + prefix), "actual batch command receipt mismatch")
            need([int(value) for value in argv[10:14]] == batch["bounds"], "command bounds disagree with plan")
            cells = native_cells(batch["bounds"])
            need(1 <= len(cells) <= maximum and not seen.intersection(cells), "batch coverage overlaps or exceeds policy")
            seen.update(cells)
            need(requested["status"] == "INCOMPLETE" and requested["reference_bits"] is None
                 and requested["built"] == 0 and requested["empty"] == 0
                 and all(entry["status"] == "missing" for entry in requested["tiles"]), "historical request changed")
            need([(entry["x"], entry["z"]) for entry in requested["tiles"]] == cells
                 and [(entry["x"], entry["z"]) for entry in native["tiles"]] == cells,
                 "native batch order differs from x-major/z-minor request")
            need(native["status"] == "COMPLETE" and native["requested_cells"] == len(cells)
                 and native["reference_bits"] == bits and native["game_qa"] == "NOT_RUN", "native result contract mismatch")
            wanted = {"requested.json", "manifest.json"}
            for entry in native["tiles"]:
                coordinate = (entry["x"], entry["z"])
                outer = indexed[coordinate]
                need(outer["batch"] == number and outer["status"] == entry["status"], "outer tile ownership/state mismatch")
                if entry["status"] == "built":
                    name = f"{entry['x']}_{entry['z']}.navtile"
                    need(entry["path"] == name and outer["path"] == prefix + "/" + name, "wrong raw tile path")
                    data = (directory / outer["path"]).read_bytes()
                    need(len(data) == entry["bytes"] == outer["bytes"] and digest(data) == outer["sha256"],
                         "raw tile identity mismatch")
                    wanted.add(name)
                else:
                    need(entry["status"] == "empty" and "path" not in outer, "empty cell unexpectedly declares a tile")
            need({p.name for p in (directory / prefix).iterdir()} == wanted, "unexpected native batch directory inventory")
        need(seen == set(top_cells(bounds)), "batch union does not exactly cover requested grid")
        need({p.name for p in (directory / "receipts").iterdir()} == {f"batch-{i:04d}.json" for i in range(len(plan))},
             "collection contains fabricated per-cell or extra receipts")
        return manifest

    try:
        for path in (Path(__file__).resolve(), Path(sys.executable).resolve(), script,
                     script.parent / "nav_route_metrics.py", extractor, backend, geometry, source):
            pin(path)
        version = run("backend-version", [backend, "--version"])
        found = re.search(r"\breference_bits=(32|64)\b", version["stdout"])
        need(found is not None, "backend omitted its reference ABI")
        bits = int(found.group(1))
        result["reference_bits"] = bits
        legacy, batched, ragged = root / "legacy", root / "batched", root / "ragged-empty"
        run("legacy-bake", bake(legacy))
        run("legacy-check", check(legacy))
        legacy_query = json.loads(run("legacy-query", query(legacy))["stdout"])
        control = load(legacy / "manifest.json")
        need(control["format"] == "bnav-collection-v1" and "batch_cells" not in control and "batches" not in control,
             "omitted option changed legacy manifest format")
        need(control["counts"] == {"built": 2, "empty": 2, "missing": 0}, "legacy fixture did not separate built/empty cells")
        passed("legacy-mode-control", counts=control["counts"])
        pin_tree(legacy)

        run("batch-bake", bake(batched, 4))
        run("batch-check", check(batched))
        batch_query = json.loads(run("batch-query", query(batched))["stdout"])
        mixed = inspect_batch_collection(batched, (0, 1, 0, 1), 4, bits)
        need(mixed["counts"] == control["counts"], "batch counts differ from default path")
        for old, new in zip(control["tiles"], mixed["tiles"]):
            need((old["x"], old["z"], old["status"]) == (new["x"], new["z"], new["status"]), "batch cells differ from legacy")
            if old["status"] == "built":
                need((legacy / old["path"]).read_bytes() == (batched / new["path"]).read_bytes(), "batch payload differs from legacy")
        need(batch_query["status"] == legacy_query["status"] == "COMPLETE_PROJECTED_PATH"
             and batch_query["result"] == legacy_query["result"]
             and batch_query["route_metrics"] == legacy_query["route_metrics"], "batch query differs from legacy")
        native_route = batch_query["result"]
        need(native_route["complete"] is True and native_route["loaded_tiles"] == 2
             and native_route["traversed_tiles"] == 2 and native_route["direct_path_blocked"] is True,
             "query did not cross the seam and detour around the wall")
        passed("batch-byte-query-equivalence", counts=mixed["counts"], native_result=native_route)
        pin_tree(batched)

        run("ragged-empty-bake", bake(ragged, 4, (8, 12, 8, 10)))
        run("ragged-empty-check", check(ragged))
        distant = inspect_batch_collection(ragged, (8, 12, 8, 10), 4, bits)
        need(distant["counts"] == {"built": 0, "empty": 15, "missing": 0}
             and len(distant["batches"]) == 6, "ragged all-empty fixture did not produce six chunks")
        passed("ragged-all-empty-coverage", bounds=[entry["bounds"] for entry in distant["batches"]], cells=15)
        refusal = run("ragged-empty-query", query(ragged), 2)
        need("empty" in refusal["stderr"].lower(), "all-empty query failed for an unrelated reason")
        passed("all-empty-query-refusal")
        pin_tree(ragged)

        portable = root / "portable-valid-copy"
        copy_collection(batched, portable)
        run("portable-copy-check", check(portable))
        passed("valid-relocated-copy")
        for maximum in (0, 17):
            destination = root / f"invalid-maximum-{maximum}"
            refusal = run(f"invalid-maximum-{maximum}", bake(destination, maximum), 2)
            need(not destination.exists() and "batch" in refusal["stderr"].lower(), "invalid policy was not rejected before output")
            passed(f"invalid-maximum-{maximum}")

        for name in TAMPERS:
            destination = root / "tampered" / name
            mutate(ragged if name == "batch-membership" else batched, destination, name, bits)
            refusal = run("tamper-" + name, check(destination), 2)
            need(refusal["stderr"] and not refusal["stdout"], "tamper refusal must not emit a success result")
            need(TAMPER_ERRORS[name] in refusal["stderr"].lower(), f"{name}: failed at an unrelated guard")
            if name in {"receipt-command", "receipt-failed", "receipt-truncated", "receipt-stdout", "request-schema",
                        "request-settings", "result-settings", "result-counts", "result-order", "result-coverage", "result-abi"}:
                need("hash mismatch" not in refusal["stderr"].lower(), "resealed semantic case only hit a stale hash")
            passed("tamper-" + name, refusal=refusal["stderr"].strip())

        fake_root = root / "fake-extractor"
        fake_root.mkdir()
        fake = fake_root / "extractor.py"
        raw_entry = next(entry for entry in mixed["tiles"] if entry["status"] == "built")
        request_path = batched / mixed["batches"][0]["request"]
        raw_path = batched / raw_entry["path"]
        program = f"""#!{sys.executable}
import json
from pathlib import Path
import sys
home = Path(__file__).resolve().parent
with (home / 'dispatch.jsonl').open('a') as stream:
    stream.write(json.dumps(sys.argv) + '\\n')
if len(sys.argv) != 20 or sys.argv[1] != 'build-tiles-obj':
    raise SystemExit(79)
output = Path(sys.argv[4])
output.mkdir()
with (output / 'requested.json').open('xb') as stream:
    stream.write(Path({str(request_path)!r}).read_bytes())
with (output / '0_0.navtile').open('xb') as stream:
    stream.write(Path({str(raw_path)!r}).read_bytes())
print('intentional fake extractor failure after one retained tile', file=sys.stderr)
raise SystemExit(2)
"""
        create(fake, program.encode())
        fake.chmod(0o700)
        pin(fake)
        failed = root / "failed-batch"
        run("partial-batch-failure", bake(failed, 4, selected_extractor=fake), 3)
        failed_manifest = load(failed / "manifest.json")
        need(failed_manifest["format"] == FORMAT and failed_manifest["status"] == "INCOMPLETE"
             and failed_manifest["counts"] == {"built": 0, "empty": 0, "missing": 4}
             and all(entry["status"] == "missing" for entry in failed_manifest["tiles"]), "failed batch accepted partial cells")
        need((failed / "batches/0000/0_0.navtile").read_bytes() == raw_path.read_bytes()
             and (failed / "batches/0000/requested.json").read_bytes() == request_path.read_bytes()
             and not (failed / "batches/0000/manifest.json").exists(), "failed batch did not preserve expected partial output")
        dispatches = [json.loads(line) for line in (fake_root / "dispatch.jsonl").read_text().splitlines()]
        need(len(dispatches) == 1 and len(dispatches[0]) == 20, "fake extractor dispatch count/shape differs")
        failed_record = failed_manifest["batches"][0]
        failed_receipt = load(failed / failed_record["receipt"])
        need(failed_receipt["argv"] == dispatches[0] and failed_receipt["exit_code"] == 2
             and failed_record["receipt_sha256"] == digest((failed / failed_record["receipt"]).read_bytes()),
             "failed batch did not retain its actual process receipt")
        need({p.name for p in (failed / "receipts").iterdir()} == {"batch-0000.json"}, "failed batch fabricated per-cell receipts")
        passed("partial-batch-preservation", child_exit=2, collection_exit=3, all_failed_batch_cells_missing=True)
        refusal = run("partial-batch-check", check(failed), 2)
        need("incomplete" in refusal["stderr"].lower(), "incomplete collection failed for unrelated reason")
        passed("partial-batch-check-refusal")
        need(len(result["commands"]) == EXPECTED_COMMANDS and len(result["checks"]) == EXPECTED_CHECKS,
             "planned command/check counts drifted")
        result["status"] = "PASS"
    except (Failure, OSError, ValueError, TypeError, KeyError, struct.error) as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        try:
            result["inputs_after"] = [identity(Path(item["path"])) for item in result["inputs_before"]]
            need(result["inputs_before"] == result["inputs_after"], "pinned original/tool/script inputs changed")
            result["inputs_unchanged"] = True
        except (Failure, OSError) as error:
            result["status"] = "FAIL"
            result["errors"].append(f"input readback: {error}")
        result["command_count"] = len(result["commands"])
        result["passed_check_count"] = len(result["checks"])
        result["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
        save(root / "result.json", result)
    print(json.dumps({"status": result["status"], "result": str(root / "result.json"),
                      "command_count": result["command_count"], "passed_check_count": result["passed_check_count"],
                      "errors": result["errors"], "game_qa": "NOT_RUN"}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Failure, OSError) as error:
        print(f"smoke_nav_collection_batch: {error}", file=sys.stderr)
        sys.exit(2)
