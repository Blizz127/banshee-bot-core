#!/usr/bin/env python3
"""Build and verify a bounded collection of real Detour tiles; no game runtime."""

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
from zoneinfo import ZoneInfo

from nav_route_metrics import RouteError, measure_route, validate_projection_limit, validate_query_refusal


FORMAT = "bnav-collection-v1"
BATCH_FORMAT = "bnav-collection-batch-v1"
SOURCE_FORMAT = "bnav-geometry-v1"
MAX_TILES = 256
MAX_TILE_BYTES = 64 * 1024 * 1024
MAX_COLLECTION_BYTES = 256 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_BATCH_BYTES = 128 * 1024 * 1024
SETTINGS = ("cell_size", "cell_height", "agent_height", "agent_radius", "agent_climb", "max_slope")


class Invalid(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_file(path, limit):
    need(path.is_file(), f"not a regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit, f"file exceeds {limit} byte limit: {path}")
    return data


def json_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_json(data):
    def constant(value):
        raise Invalid(f"nonfinite JSON number: {value}")
    result = json.loads(data, object_pairs_hook=json_object, parse_constant=constant)
    need(isinstance(result, dict), "JSON root must be an object")
    return result


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def text(value, field):
    need(isinstance(value, str) and 0 < len(value) <= 1024 and value.strip() == value,
         f"{field} must be a nonempty string without surrounding whitespace")
    need(not any(ord(char) < 32 for char in value), f"{field} contains a control character")
    return value


def hash_text(value, field):
    need(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), f"invalid {field} SHA-256")
    return value


def finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    need(valid, f"{field} must be finite")
    return float(value)


def integer(value, field, low, high):
    need(type(value) is int and low <= value <= high, f"{field} must be an integer in {low}..{high}")
    return value


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def validate_source(source):
    need(isinstance(source, dict), "geometry sidecar must be an object")
    need(source.get("format") == SOURCE_FORMAT, "unsupported geometry sidecar format")
    text(source.get("game"), "game")
    text(source.get("zone"), "zone")
    coords = source.get("coordinates", {})
    need(isinstance(coords, dict) and coords.get("up_axis") == "Y", "geometry must explicitly declare Y-up")
    text(coords.get("units"), "coordinates.units")
    text(coords.get("transform"), "coordinates.transform")
    coverage = source.get("coverage", {})
    need(isinstance(coverage, dict), "coverage must be an object")
    text(coverage.get("scope"), "coverage.scope")
    limitations = coverage.get("limitations")
    need(isinstance(limitations, list) and len(limitations) <= 128, "coverage.limitations must be a bounded list")
    for value in limitations:
        text(value, "coverage.limitations item")
    provenance = source.get("provenance", {})
    need(isinstance(provenance, dict), "provenance must be an object")
    text(provenance.get("description"), "provenance.description")
    # Classification is a caller declaration, not proof of origin or permission.
    need(provenance.get("classification") in ("synthetic", "owner_asset"),
         "provenance.classification must be synthetic or owner_asset")
    artifacts = provenance.get("artifacts", [])
    need(isinstance(artifacts, list) and len(artifacts) <= 256, "provenance.artifacts must be a bounded list")
    for artifact in artifacts:
        need(isinstance(artifact, dict), "provenance artifact must be an object")
        text(artifact.get("path"), "provenance artifact path")
        hash_text(artifact.get("sha256"), "provenance artifact")
    geometry = source.get("geometry", {})
    need(isinstance(geometry, dict), "geometry must be an object")
    text(geometry.get("path"), "geometry.path")
    hash_text(geometry.get("sha256"), "geometry")


def source_record(path):
    data = read_file(path, MAX_JSON_BYTES)
    source = decode_json(data)
    validate_source(source)
    geometry = source["geometry"]
    selected = Path(text(geometry.get("path"), "geometry.path")).expanduser()
    selected = (path.parent / selected).resolve() if not selected.is_absolute() else selected.resolve()
    expected = hash_text(geometry.get("sha256"), "geometry")
    geometry_bytes = read_file(selected, MAX_TILE_BYTES)
    need(sha(geometry_bytes) == expected, "geometry input does not match sidecar SHA-256")
    return source, data, selected, geometry_bytes


def validate_grid(grid):
    need(isinstance(grid, dict), "grid must be an object")
    for key in ("origin_x", "origin_z", "min_y", "max_y"):
        value = finite(grid.get(key), key)
        need(abs(value) < 10_000_000, f"{key} exceeds supported coordinate range")
    need(grid["min_y"] <= grid["max_y"], "min_y must not exceed max_y")
    integer(grid.get("tile_cells"), "tile_cells", 8, 1024)
    for key in ("x_min", "x_max", "z_min", "z_max"):
        integer(grid.get(key), key, 0, 4095)
    need(grid["x_min"] <= grid["x_max"] and grid["z_min"] <= grid["z_max"], "inverted tile range")
    count = (grid["x_max"] - grid["x_min"] + 1) * (grid["z_max"] - grid["z_min"] + 1)
    need(count <= MAX_TILES, f"collection exceeds {MAX_TILES} cells")
    for key in SETTINGS:
        finite(grid.get(key), key)
        try:
            converted = f32(grid[key])
        except OverflowError:
            converted = math.inf
        need(math.isfinite(converted), f"{key} exceeds float32 backend range")
        if key in ("cell_size", "cell_height", "agent_height"):
            need(converted > 0, f"{key} rounds to a nonpositive backend value")
    cs, ch, height, radius, climb, slope = (grid[key] for key in SETTINGS)
    need(cs > 0 and ch > 0 and height > 0 and radius >= 0 and climb >= 0 and 0 <= slope < 90,
         "invalid Recast dimensions or slope")
    need(3 <= height / ch <= 8191 and radius / cs <= 1024 and climb / ch <= 8191,
         "agent dimensions exceed supported voxel limits")
    need(grid["tile_cells"] + 2 * (math.ceil(radius / cs) + 3) < 4096,
         "tile plus border exceeds backend grid limit")
    need((grid["tile_cells"] + 2 * (math.ceil(radius / cs) + 3)) ** 2 <= 4_000_000,
         "tile plus border exceeds backend cell budget")
    world = grid["tile_cells"] * cs
    for axis in ("x", "z"):
        for index in (grid[f"{axis}_min"], grid[f"{axis}_max"] + 1):
            need(abs(grid[f"origin_{axis}"] + index * world) < 10_000_000,
                 "grid extent exceeds supported coordinate range")
    return [(x, z) for z in range(grid["z_min"], grid["z_max"] + 1)
            for x in range(grid["x_min"], grid["x_max"] + 1)]


def close(left, right, cell_size):
    # Stored header values are float32; allow rounding from the padded-border bake.
    return abs(left - right) <= max(1e-5, abs(right) * 2 ** -21, cell_size * 1e-4)


def inspect_tile(data, grid, x, z, bits):
    need(bits in (32, 64), "unsupported Detour reference width")
    need(100 <= len(data) <= MAX_TILE_BYTES, "invalid Detour tile size")
    magic, version, tx, tz, layer = struct.unpack_from("<IIiii", data)
    need(magic == 0x444E4156 and version == 7, "unsupported Detour tile magic/version")
    need((tx, tz, layer) == (x, z, 0), "Detour tile coordinates/layer differ from manifest")
    counts = struct.unpack_from("<9i", data, 24)
    need(all(value >= 0 for value in counts), "negative Detour section count")
    poly, vert, links, details, detail_verts, detail_tris, bvs, connections, off_base = counts
    need(poly > 0 and vert > 0 and off_base <= poly and connections == poly - off_base
         and details == off_base, "invalid Detour polygon/detail counts")
    sizes = (12, 32, 12 if bits == 32 else 16, 12, 12, 4, 16, 36)
    section_counts = (vert, poly, links, details, detail_verts, detail_tris, bvs, connections)
    need(100 + sum(count * size for count, size in zip(section_counts, sizes)) == len(data),
         "Detour section lengths differ from selected ABI")
    dimensions = struct.unpack_from("<3f", data, 60)
    bounds_min = struct.unpack_from("<3f", data, 72)
    bounds_max = struct.unpack_from("<3f", data, 84)
    need(all(math.isfinite(v) for v in (*dimensions, *bounds_min, *bounds_max)), "nonfinite Detour header")
    cs, ch = grid["cell_size"], grid["cell_height"]
    world = grid["tile_cells"] * cs
    expected_min = (grid["origin_x"] + x * world, grid["min_y"] - ch, grid["origin_z"] + z * world)
    walkable_height = math.ceil(f32(f32(grid["agent_height"]) / f32(ch)))
    # Recast's compact heightfield extends bmax.y by walkableHeight * ch.
    expected_max = (expected_min[0] + world,
                    grid["max_y"] + grid["agent_height"] + grid["agent_climb"] + ch + walkable_height * ch,
                    expected_min[2] + world)
    for got, expected in zip(dimensions, (grid["agent_height"], grid["agent_radius"], grid["agent_climb"])):
        need(close(got, expected, cs), "Detour agent settings differ from manifest")
    for got, expected in zip((*bounds_min, *bounds_max), (*expected_min, *expected_max)):
        need(close(got, expected, cs), "Detour tile bounds differ from manifest grid")


def file_identity(path, limit=128 * 1024 * 1024):
    data = read_file(path, limit)
    return {"path": str(path), "sha256": sha(data), "bytes": len(data)}


def run(command, timeout=600):
    result = subprocess.run(list(map(str, command)), capture_output=True, timeout=timeout)
    return {"argv": list(map(str, command)), "exit_code": result.returncode,
            "stdout": result.stdout.decode(errors="replace")[-16384:],
            "stderr": result.stderr.decode(errors="replace")[-16384:],
            "output_truncated": len(result.stdout) > 16384 or len(result.stderr) > 16384}


def backend_bits(backend):
    result = run([backend, "--version"])
    need(result["exit_code"] == 0, "backend --version failed")
    match = re.search(r"\breference_bits=(32|64)\b", result["stdout"])
    need(match is not None, "backend did not identify its Detour reference ABI")
    return int(match.group(1))


def plan_batches(grid, limit):
    """Deterministic disjoint rectangles; native batches iterate X then Z."""
    integer(limit, "batch cells", 1, 16)
    width = min(grid["x_max"] - grid["x_min"] + 1, limit)
    height = min(grid["z_max"] - grid["z_min"] + 1, limit // width)
    result = []
    for z in range(grid["z_min"], grid["z_max"] + 1, height):
        for x in range(grid["x_min"], grid["x_max"] + 1, width):
            result.append({"id": len(result), "bounds": [x, min(x + width - 1, grid["x_max"]),
                                                       z, min(z + height - 1, grid["z_max"])]})
    return result


def rectangle_cells(bounds):
    xmin, xmax, zmin, zmax = bounds
    return [(x, z) for x in range(xmin, xmax + 1) for z in range(zmin, zmax + 1)]


def batch_json(data):
    try:
        return decode_json(data)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise Invalid(f"invalid batch JSON: {error}") from error


def batch_file(root, relative, limit):
    selected = root / relative
    need(selected.resolve().is_relative_to(root), "batch file escapes collection directory")
    for part in (selected, *selected.parents):
        if part == root:
            break
        need(not part.is_symlink(), "batch files/directories must not be symlinks")
    return selected, read_file(selected, limit)


def backend_number(value, field):
    value = finite(value, field)
    try:
        converted = f32(value)
    except OverflowError as error:
        raise Invalid(f"{field} exceeds float32 range") from error
    need(math.isfinite(converted), f"{field} exceeds float32 range")
    return converted


def validate_batch_output(root, manifest, batch):
    """Join one actual invocation to its complete native output, without queries."""
    group = integer(batch.get("id"), "batch id", 0, MAX_TILES - 1)
    prefix = f"batches/{group:04d}"
    grid, bits = manifest["grid"], manifest["reference_bits"]
    cells = rectangle_cells(batch["bounds"])

    def document(key, relative):
        need(batch.get(key) == relative, f"unexpected batch {key} path")
        _, data = batch_file(root, relative, MAX_JSON_BYTES)
        need(sha(data) == hash_text(batch.get(key + "_sha256"), key), f"batch {key} hash mismatch")
        return batch_json(data)

    receipt = document("receipt", f"receipts/batch-{group:04d}.json")
    need(type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0,
         "batch invocation did not succeed")
    need(receipt.get("output_truncated") is False and not receipt.get("timed_out", False),
         "batch invocation output is truncated or timed out")
    argv = receipt.get("argv")
    need(isinstance(argv, list) and len(argv) == 20 and all(isinstance(v, str) for v in argv),
         "invalid batch receipt command")
    need(argv[:4] == [manifest["tools"]["extractor"]["path"], "build-tiles-obj",
                      manifest["tools"]["backend"]["path"], manifest["geometry"]["path"]]
         and Path(argv[4]).is_absolute() and Path(argv[4]).as_posix().endswith("/" + prefix),
         "batch receipt source/tool/output mismatch")
    expected_args = [grid[key] for key in ("origin_x", "origin_z", "min_y", "max_y", "tile_cells")]
    expected_args += batch["bounds"] + [grid[key] for key in SETTINGS]
    for value, expected in zip(argv[5:], expected_args):
        try:
            actual = float(value)
        except ValueError:
            actual = math.nan
        need(math.isfinite(actual) and actual == expected, "batch receipt grid/settings mismatch")

    request = document("request", prefix + "/requested.json")
    result = document("result", prefix + "/manifest.json")
    need(isinstance(receipt.get("stdout"), str) and batch_json(receipt["stdout"]) == result,
         "batch stdout differs from retained native result")
    for record, complete in ((request, False), (result, True)):
        need(record.get("format") == "bnav-tile-batch-v1" and
             record.get("status") == ("COMPLETE" if complete else "INCOMPLETE"),
             "invalid native batch format/status")
        if complete:
            need(integer(record.get("reference_bits"), "batch ABI", 32, 64) == bits,
                 "native batch ABI differs from collection")
        else:
            need("reference_bits" in record and record["reference_bits"] is None,
                 "historical batch request must declare null ABI")
        need(record.get("game_qa") == "NOT_RUN", "native batch cannot claim Game QA")
        need(integer(record.get("requested_cells"), "requested batch cells", 1, 16) == len(cells),
             "native batch requested coverage differs")
        for field, keys in (("origin", ("origin_x", "origin_z")),
                            ("vertical_bounds", ("min_y", "max_y")), ("settings", SETTINGS)):
            values = record.get(field)
            need(isinstance(values, list) and len(values) == len(keys), f"invalid native batch {field}")
            need(all(backend_number(value, field) == backend_number(grid[key], key)
                     for value, key in zip(values, keys)), f"native batch {field} differ from collection")
        need(integer(record.get("tile_cells"), "native tile cells", 8, 1024) == grid["tile_cells"],
             "native batch tile cells differ from collection")
        for key in ("geometry_vertices", "geometry_triangles"):
            integer(record.get(key), key, 1, 1_000_000)
            need(record[key] == request.get(key), "native batch geometry counts changed")
        entries = record.get("tiles")
        need(isinstance(entries, list) and len(entries) == len(cells), "native batch inventory is incomplete")
        built, empty = 0, 0
        for entry, (x, z) in zip(entries, cells):
            need(isinstance(entry, dict), "native batch tile entry must be an object")
            need(integer(entry.get("x"), "native tile x", 0, 4095) == x and
                 integer(entry.get("z"), "native tile z", 0, 4095) == z,
                 "native batch cell order/coverage differs")
            status = entry.get("status")
            if not complete:
                need(status == "missing" and set(entry) == {"x", "z", "status"},
                     "historical batch inventory must remain missing")
            elif status == "empty":
                need(set(entry) == {"x", "z", "status"}, "empty batch cell declares a payload")
                empty += 1
            else:
                need(status == "built" and set(entry) == {"x", "z", "status", "path", "bytes"},
                     "invalid completed batch cell")
                need(entry["path"] == f"{x}_{z}.navtile", "unexpected native batch tile path")
                integer(entry["bytes"], "native tile bytes", 100, MAX_TILE_BYTES)
                built += 1
        need(integer(record.get("built"), "batch built count", 0, 16) == built and
             integer(record.get("empty"), "batch empty count", 0, 16) == empty,
             "native batch count summary differs")

    output = root / prefix
    need(output.is_dir() and not output.is_symlink(), "invalid batch output directory")
    expected_names = {"requested.json", "manifest.json"}
    accepted, total = [], 0
    for entry in result["tiles"]:
        x, z, state = entry["x"], entry["z"], entry["status"]
        converted = {"x": x, "z": z, "status": state, "batch": group}
        if state == "built":
            relative = prefix + "/" + entry["path"]
            _, data = batch_file(root, relative, MAX_TILE_BYTES)
            need(len(data) == entry["bytes"], "native batch tile size mismatch")
            inspect_tile(data, grid, x, z, bits)
            total += len(data)
            need(total <= MAX_BATCH_BYTES, "native batch exceeds 128 MiB payload budget")
            converted.update(path=relative, bytes=len(data), sha256=sha(data))
            expected_names.add(entry["path"])
        accepted.append(converted)
    need({p.name for p in output.iterdir()} == expected_names,
         "batch directory has unexpected or missing output (including an empty-cell payload)")
    return accepted, total


def bake_batches(output, manifest):
    grid = manifest["grid"]
    entries = {(entry["x"], entry["z"]): entry for entry in manifest["tiles"]}
    total = 0
    for batch in manifest["batches"]:
        group = batch["id"]
        prefix = f"batches/{group:04d}"
        command = [manifest["tools"]["extractor"]["path"], "build-tiles-obj",
                   manifest["tools"]["backend"]["path"], manifest["geometry"]["path"], output / prefix,
                   *(grid[key] for key in ("origin_x", "origin_z", "min_y", "max_y", "tile_cells")),
                   *batch["bounds"], *(grid[key] for key in SETTINGS)]
        try:
            receipt = run(command)
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            receipt = {"argv": list(map(str, command)), "exit_code": None, "timed_out": True,
                       "stdout": stdout.decode(errors="replace")[-16384:],
                       "stderr": stderr.decode(errors="replace")[-16384:],
                       "output_truncated": len(stdout) > 16384 or len(stderr) > 16384}
        receipt_name = f"receipts/batch-{group:04d}.json"
        write_json(output / receipt_name, receipt)
        batch.update(receipt=receipt_name, receipt_sha256=sha((output / receipt_name).read_bytes()))
        need(receipt["exit_code"] == 0, f"batch {group} bake failed: {receipt['stderr'].strip()}")
        for key, name in (("request", "requested.json"), ("result", "manifest.json")):
            relative = prefix + "/" + name
            _, data = batch_file(output, relative, MAX_JSON_BYTES)
            batch[key] = relative
            batch[key + "_sha256"] = sha(data)
        accepted, size = validate_batch_output(output, manifest, batch)
        need(total + size <= MAX_COLLECTION_BYTES, "collection exceeds native 256 MiB load budget")
        # Commit a batch's coverage only after all its output has been verified.
        for entry in accepted:
            entries[(entry["x"], entry["z"])].update(entry)
        total += size


def validate_batch_collection(path, manifest, cells, bits):
    plans = plan_batches(manifest["grid"], manifest.get("batch_cells"))
    batches = manifest.get("batches")
    need(isinstance(batches, list) and len(batches) == len(plans), "batch inventory does not cover requested grid")
    directory = path.parent / "batches"
    need(directory.is_dir() and not directory.is_symlink() and
         {p.name for p in directory.iterdir()} == {f"{p['id']:04d}" for p in plans},
         "batch directory inventory differs from requested plan")
    expected, total = {}, 0
    for batch, plan in zip(batches, plans):
        need(isinstance(batch, dict), "batch record must be an object")
        need(integer(batch.get("id"), "batch id", 0, MAX_TILES - 1) == plan["id"], "batch id/order differs from plan")
        bounds = batch.get("bounds")
        need(isinstance(bounds, list) and len(bounds) == 4, "invalid batch rectangle")
        for value, wanted in zip(bounds, plan["bounds"]):
            need(integer(value, "batch bound", 0, 4095) == wanted, "batch rectangle differs from plan")
        accepted, size = validate_batch_output(path.parent, manifest, batch)
        total += size
        need(total <= MAX_COLLECTION_BYTES, "collection exceeds native load budget")
        for entry in accepted:
            coordinate = entry["x"], entry["z"]
            need(coordinate not in expected, "batch rectangles overlap")
            expected[coordinate] = entry
    need(set(expected) == set(cells), "batches omit requested cells")
    tiles = manifest.get("tiles")
    need(isinstance(tiles, list) and len(tiles) == len(cells), "tile inventory does not cover requested grid")
    seen, paths = set(), []
    counts = {state: 0 for state in ("built", "empty", "missing")}
    for entry in tiles:
        need(isinstance(entry, dict), "tile entry must be an object")
        x = integer(entry.get("x"), "tile x", 0, 4095)
        z = integer(entry.get("z"), "tile z", 0, 4095)
        integer(entry.get("batch"), "tile batch", 0, MAX_TILES - 1)
        coordinate = x, z
        need(coordinate in expected and coordinate not in seen, "duplicate or out-of-grid tile coordinate")
        seen.add(coordinate)
        if entry.get("status") == "built":
            integer(entry.get("bytes"), "tile bytes", 100, MAX_TILE_BYTES)
        need(entry == expected[coordinate], "collection tile differs from bound batch result/hash")
        counts[entry["status"]] += 1
        if entry["status"] == "built":
            paths.append(path.parent / entry["path"])
    reported_counts = manifest.get("counts")
    need(isinstance(reported_counts, dict) and set(reported_counts) == set(counts),
         "invalid batch collection count summary")
    for key, value in counts.items():
        need(integer(reported_counts[key], key + " count", 0, MAX_TILES) == value,
             "collection count summary differs from batch inventory")
    return manifest, paths


def bake(args):
    sidecar = args.source.expanduser().resolve(strict=True)
    source, source_bytes, geometry, geometry_bytes = source_record(sidecar)
    grid = {key: getattr(args, key) for key in ("origin_x", "origin_z", "min_y", "max_y", "tile_cells",
                                               "x_min", "x_max", "z_min", "z_max")}
    grid.update(zip(SETTINGS, args.settings))
    cells = validate_grid(grid)
    batch_limit = getattr(args, "batch_cells", None)
    plans = plan_batches(grid, batch_limit) if batch_limit is not None else None
    extractor, backend = (p.expanduser().resolve(strict=True) for p in (args.extractor, args.backend))
    tools = {"extractor": file_identity(extractor), "backend": file_identity(backend)}
    bits = backend_bits(backend)
    output = args.output_dir.expanduser().resolve()
    repo = Path(__file__).resolve().parents[1]
    need(not output.is_relative_to(repo) and not any((parent / ".git").exists() for parent in (output, *output.parents)),
         "collection output must remain outside Git repositories")
    need(not output.exists(), "output directory already exists; choose a fresh path")
    output.mkdir(parents=True)
    (output / ("batches" if plans is not None else "tiles")).mkdir()
    (output / "receipts").mkdir()
    with (output / "source.json").open("xb") as stream:
        stream.write(source_bytes)
    manifest = {"format": BATCH_FORMAT if plans is not None else FORMAT,
                "status": "INCOMPLETE", "grid": grid, "reference_bits": bits,
                "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
                "geometry": {"path": str(geometry), "sha256": sha(geometry_bytes), "bytes": len(geometry_bytes)},
                "source_sidecar_sha256": sha(source_bytes), "game": source["game"], "zone": source["zone"],
                "coordinates": source["coordinates"], "coverage": source["coverage"],
                "provenance": source["provenance"], "tools": tools,
                "game_qa": "NOT_RUN", "native_adapter_compatibility": "NOT_VERIFIED",
                "coverage_meaning": "every requested grid cell evaluated; not whole-zone geometry or gameplay proof",
                "tiles": [{"x": x, "z": z, "status": "missing"} for x, z in cells], "errors": []}
    if plans is not None:
        manifest.update(batch_cells=batch_limit, batches=plans)
        owners = {cell: plan["id"] for plan in plans for cell in rectangle_cells(plan["bounds"])}
        for entry in manifest["tiles"]:
            entry["batch"] = owners[(entry["x"], entry["z"])]
    # Retain the requested coverage even if the process is interrupted before a final receipt.
    write_json(output / "requested.json", manifest)
    total_bytes = 0
    try:
        if plans is not None:
            bake_batches(output, manifest)
        for entry in (manifest["tiles"] if plans is None else ()):
            x, z = entry["x"], entry["z"]
            relative = f"tiles/{x}_{z}.navtile"
            tile = output / relative
            command = [extractor, "build-tile-obj", backend, geometry, tile,
                       grid["origin_x"], grid["origin_z"], grid["min_y"], grid["max_y"],
                       grid["tile_cells"], x, z, *(grid[key] for key in SETTINGS)]
            receipt = run(command)
            receipt_path = f"receipts/{x}_{z}.json"
            write_json(output / receipt_path, receipt)
            entry["receipt"] = receipt_path
            entry["receipt_sha256"] = sha((output / receipt_path).read_bytes())
            if receipt["exit_code"] == 3:
                need(not tile.exists(), "empty bake unexpectedly produced a tile")
                entry["status"] = "empty"
            else:
                need(receipt["exit_code"] == 0, f"tile {x},{z} bake failed: {receipt['stderr'].strip()}")
                data = read_file(tile, MAX_TILE_BYTES)
                inspect_tile(data, grid, x, z, bits)
                total_bytes += len(data)
                need(total_bytes <= MAX_COLLECTION_BYTES, "collection exceeds native 256 MiB load budget")
                entry.update(status="built", path=relative, sha256=sha(data), bytes=len(data))
        need(read_file(sidecar, MAX_JSON_BYTES) == source_bytes, "source sidecar changed during bake")
        need(sha(read_file(geometry, MAX_TILE_BYTES)) == manifest["geometry"]["sha256"], "geometry changed during bake")
        for name, path in (("extractor", extractor), ("backend", backend)):
            need(file_identity(path) == tools[name], f"{name} binary changed during bake")
        manifest["status"] = "COMPLETE"
    except (OSError, Invalid, subprocess.TimeoutExpired) as error:
        manifest["errors"].append(str(error))
    manifest["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    manifest["counts"] = {state: sum(entry["status"] == state for entry in manifest["tiles"])
                          for state in ("built", "empty", "missing")}
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "manifest": str(output / "manifest.json"),
                      "counts": manifest["counts"], "errors": manifest["errors"], "game_qa": "NOT_RUN"}))
    return 0 if manifest["status"] == "COMPLETE" else 3


def validate_collection(path):
    path = path.expanduser().resolve(strict=True)
    manifest = decode_json(read_file(path, MAX_JSON_BYTES))
    need(manifest.get("format") in (FORMAT, BATCH_FORMAT), "unsupported collection manifest format")
    need(manifest.get("status") == "COMPLETE" and manifest.get("errors") == [], "collection is incomplete or failed")
    cells = validate_grid(manifest.get("grid"))
    bits = integer(manifest.get("reference_bits"), "reference_bits", 32, 64)
    need(bits in (32, 64), "unsupported reference ABI")
    def retained(relative, limit):
        selected = path.parent / relative
        need(not selected.is_symlink() and selected.resolve().is_relative_to(path.parent),
             "collection files must stay inside their directory without symlinks")
        return selected, read_file(selected, limit)

    _, source_bytes = retained("source.json", MAX_JSON_BYTES)
    source = decode_json(source_bytes)
    need(sha(source_bytes) == manifest.get("source_sidecar_sha256"), "source sidecar hash mismatch")
    validate_source(source)
    for key in ("game", "zone", "coordinates", "coverage", "provenance"):
        need(source.get(key) == manifest.get(key), f"source declaration differs from collection {key}")
    need(isinstance(source.get("geometry"), dict) and isinstance(manifest.get("geometry"), dict),
         "missing geometry identity")
    need(source["geometry"].get("sha256") == manifest["geometry"].get("sha256"),
         "geometry source hash differs from collection")
    tools = manifest.get("tools", {})
    need(isinstance(tools, dict), "tool identities must be an object")
    for name in ("backend", "extractor"):
        need(isinstance(tools.get(name), dict), f"missing {name} tool identity")
        hash_text(tools[name].get("sha256"), name)
        text(tools[name].get("path"), f"{name} path")
        integer(tools[name].get("bytes"), f"{name} bytes", 1, 128 * 1024 * 1024)
    text(manifest["geometry"].get("path"), "recorded geometry path")
    integer(manifest["geometry"].get("bytes"), "recorded geometry bytes", 1, MAX_TILE_BYTES)
    if manifest["format"] == BATCH_FORMAT:
        return validate_batch_collection(path, manifest, cells, bits)
    need("batch_cells" not in manifest and "batches" not in manifest,
         "batch metadata cannot be downgraded to a legacy collection")
    tiles = manifest.get("tiles")
    need(isinstance(tiles, list) and len(tiles) == len(cells), "tile inventory does not cover requested grid")
    indexed = {}
    paths, total_bytes = [], 0
    counts = {state: 0 for state in ("built", "empty", "missing")}
    for entry in tiles:
        need(isinstance(entry, dict), "tile entry must be an object")
        x, z = entry.get("x"), entry.get("z")
        integer(x, "tile x", 0, 4095)
        integer(z, "tile z", 0, 4095)
        need((x, z) in cells and (x, z) not in indexed, "duplicate or out-of-grid tile coordinate")
        indexed[(x, z)] = entry
        status = entry.get("status")
        need(status in ("built", "empty"), "missing or unrecognized tile state")
        counts[status] += 1
        receipt_name = f"receipts/{x}_{z}.json"
        need(entry.get("receipt") == receipt_name, "unexpected tile receipt path")
        _, receipt_bytes = retained(receipt_name, MAX_JSON_BYTES)
        need(sha(receipt_bytes) == entry.get("receipt_sha256"), "tile receipt hash mismatch")
        receipt = decode_json(receipt_bytes)
        expected_name = f"tiles/{x}_{z}.navtile"
        tile_path = path.parent / expected_name
        argv = receipt.get("argv")
        need(isinstance(argv, list) and len(argv) == 18 and all(isinstance(arg, str) for arg in argv),
             "invalid bake receipt command")
        need(argv[:4] == [tools["extractor"]["path"], "build-tile-obj", tools["backend"]["path"],
                          manifest["geometry"]["path"]]
             and Path(argv[4]).as_posix().endswith("/" + expected_name), "bake receipt source/tool/output mismatch")
        expected_args = [manifest["grid"][key] for key in ("origin_x", "origin_z", "min_y", "max_y", "tile_cells")]
        expected_args += [x, z, *(manifest["grid"][key] for key in SETTINGS)]
        for value, expected in zip(argv[5:], expected_args):
            try:
                parsed = float(value)
            except ValueError:
                parsed = math.nan
            need(math.isfinite(parsed) and parsed == expected, "bake receipt grid/settings mismatch")
        if status == "empty":
            need(receipt.get("exit_code") == 3 and "path" not in entry and not tile_path.exists() and not tile_path.is_symlink(),
                 "empty tile has inconsistent receipt or output")
            continue
        need(receipt.get("exit_code") == 0, "built tile has a failed receipt")
        need(entry.get("path") == expected_name, "unexpected tile path")
        tile_path, data = retained(expected_name, MAX_TILE_BYTES)
        need(len(data) == entry.get("bytes") and sha(data) == entry.get("sha256"), "tile size/hash mismatch")
        inspect_tile(data, manifest["grid"], x, z, bits)
        total_bytes += len(data)
        paths.append(tile_path)
    need(total_bytes <= MAX_COLLECTION_BYTES, "collection exceeds native load budget")
    need(counts == manifest.get("counts"), "collection count summary differs from tile inventory")
    return manifest, paths


def check(args):
    manifest, paths = validate_collection(args.manifest)
    print(json.dumps({"status": "VERIFIED_COLLECTION", "counts": manifest["counts"],
                      "loaded_tiles": len(paths), "game_qa": "NOT_RUN", "native_adapter_compatibility": "NOT_VERIFIED"}))
    return 0


def query(args):
    limit = validate_projection_limit(args.max_projection_distance)
    manifest_path = args.manifest.expanduser().resolve(strict=True)
    manifest_hash = sha(read_file(manifest_path, MAX_JSON_BYTES))
    manifest, paths = validate_collection(manifest_path)
    need(paths, "collection is entirely empty; no navigation query is possible")
    backend = args.backend.expanduser().resolve(strict=True)
    need(file_identity(backend)["sha256"] == manifest["tools"]["backend"]["sha256"], "backend differs from recorded build")
    need(backend_bits(backend) == manifest["reference_bits"], "backend ABI differs from collection")
    coords = [finite(value, "query coordinate") for value in (*args.start, *args.end)]
    grid = manifest["grid"]
    diagnostics = getattr(args, "diagnostic_refusals", False)
    result = run([backend, "query-tiles-report" if diagnostics else "query-tiles", grid["origin_x"], grid["min_y"] - grid["cell_height"],
                  grid["origin_z"], grid["tile_cells"] * grid["cell_size"], *coords, *paths])
    refused = diagnostics and result["exit_code"] == 3
    need(result["exit_code"] == 0 or refused, f"native query failed: {result['stderr'].strip()}")
    native = decode_json(result["stdout"])
    if refused:
        need(not result.get("output_truncated", False), "native refusal output is truncated")
        validate_query_refusal(native, manifest["reference_bits"])
    else:
        need(native.get("complete") is True, "native query did not report a complete snapped-endpoint path")
        metrics = measure_route(args.start, args.end, native, limit)
    need(file_identity(backend)["sha256"] == manifest["tools"]["backend"]["sha256"], "backend changed during query")
    validate_collection(manifest_path)
    need(sha(read_file(manifest_path, MAX_JSON_BYTES)) == manifest_hash, "collection changed during query")
    if refused:
        print(json.dumps({"status": "QUERY_REFUSED", "game": manifest["game"], "zone": manifest["zone"],
                          "coverage": manifest["coverage"], "diagnostic": native,
                          "requested_start": args.start, "requested_end": args.end, "game_qa": "NOT_RUN",
                          "native_adapter_compatibility": "NOT_VERIFIED"}))
        return 3
    exceeded = metrics["within_projection_limit"] is False
    print(json.dumps({"status": "PROJECTION_LIMIT_EXCEEDED" if exceeded else "COMPLETE_PROJECTED_PATH",
                      "game": manifest["game"], "zone": manifest["zone"],
                      "coverage": manifest["coverage"], "result": native, "route_metrics": metrics, "game_qa": "NOT_RUN",
                      "native_adapter_compatibility": "NOT_VERIFIED"}))
    return 3 if exceeded else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("bake", help="evaluate every cell in a new bounded grid")
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--extractor", required=True, type=Path)
    build.add_argument("--backend", required=True, type=Path)
    build.add_argument("--output-dir", required=True, type=Path)
    for field in ("origin-x", "origin-z", "min-y", "max-y"):
        build.add_argument("--" + field, required=True, type=float)
    for field in ("tile-cells", "x-min", "x-max", "z-min", "z-max"):
        build.add_argument("--" + field, required=True, type=int)
    build.add_argument("--settings", nargs=6, type=float, default=[0.3, 0.2, 2.0, 0.6, 0.9, 45.0],
                       metavar=("CS", "CH", "HEIGHT", "RADIUS", "CLIMB", "SLOPE"))
    build.add_argument("--batch-cells", type=int, choices=range(1, 17),
                       help="opt in to batches of at most N cells; omitted preserves individual-cell format")
    build.set_defaults(action=bake)
    verify = commands.add_parser("check", help="verify complete inventory, raw tile grid/ABI and hashes")
    verify.add_argument("manifest", type=Path)
    verify.set_defaults(action=check)
    route = commands.add_parser("query", help="query only a complete verified collection with its exact backend")
    route.add_argument("manifest", type=Path)
    route.add_argument("--backend", required=True, type=Path)
    route.add_argument("--start", nargs=3, type=float, required=True)
    route.add_argument("--end", nargs=3, type=float, required=True)
    route.add_argument("--max-projection-distance", type=float,
                       help="optional maximum 3D endpoint projection distance in source coordinate units")
    route.add_argument("--diagnostic-refusals", action="store_true",
                       help="opt in to typed native query refusals; requires a report-capable backend")
    route.set_defaults(action=query)
    args = parser.parse_args()
    try:
        return args.action(args)
    except (Invalid, RouteError, OSError, KeyError, TypeError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"bake_nav_collection: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
