#!/usr/bin/env python3
"""Retain and query an explicit bounded WoW navigation selection without rebaking."""

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


FORMAT = "bnav-wow-selection-v1"
PROFILES = {"cmangos-v8": (20, 8, 32), "cmangos-v8-ref64": (20, 8, 64), "acore-v20": (56, 20, 64)}
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
SCOPE = {"kind": "explicit-selected-tiles", "whole_map_coverage": False,
         "unselected_tiles": "unknown; neither empty nor evaluated"}


class Invalid(ValueError):
    pass


def need(value, message):
    if not value:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, limit=MAX_FILE):
    need(path.is_file(), f"not a regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit, f"file exceeds {limit} byte limit: {path}")
    return data


def identity(path, data=None, limit=MAX_FILE):
    data = read(path, limit) if data is None else data
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def label(value, name):
    need(isinstance(value, str) and 0 < len(value) <= 2048 and value.strip() == value
         and not any(ord(c) < 32 for c in value), f"invalid {name}")
    return value


def integer(value, name, low, high):
    need(type(value) is int and low <= value <= high, f"{name} must be an integer in {low}..{high}")
    return value


def valid_identity(value, limit):
    need(isinstance(value, dict), "file identity must be an object")
    label(value.get("path"), "file identity path")
    integer(value.get("bytes"), "file identity bytes", 1, limit)
    need(isinstance(value.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
         "invalid file identity SHA-256")


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


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def retain(root, relative, data):
    with (root / relative).open("xb") as stream:
        stream.write(data)
    return identity(Path(relative), data)


def run(argv):
    argv = list(map(str, argv))
    result = subprocess.run(argv, capture_output=True, timeout=120)
    return {"argv": argv, "exit_code": result.returncode,
            "stdout": result.stdout.decode(errors="replace")[-16384:],
            "stderr": result.stderr.decode(errors="replace")[-16384:],
            "output_truncated": len(result.stdout) > 16384 or len(result.stderr) > 16384}


def backend_bits(path):
    result = run([path, "--version"])
    found = re.search(r"\breference_bits=(32|64)\b", result["stdout"])
    need(result["exit_code"] == 0 and found is not None, "backend did not identify its reference ABI")
    return int(found.group(1))


def profile_info(profile):
    need(isinstance(profile, str) and profile in PROFILES, "unsupported explicit WoW profile")
    return PROFILES[profile]


def inspect_map(data, profile):
    profile_info(profile)
    need(len(data) == 28, "map parameters must contain exactly 28 bytes")
    ox, oy, oz, width, height, max_tiles, max_polys = struct.unpack("<5fII", data)
    need(all(math.isfinite(v) for v in (ox, oy, oz, width, height)), "nonfinite map parameters")
    need(all(abs(v) <= 10_000_000 for v in (ox, oy, oz)) and width > 0 and height > 0,
         "invalid map origin or tile dimensions")
    need(1 <= max_tiles <= 4096, "map maximum tile count exceeds native diagnostic budget")
    need(1 <= max_polys <= 0x7fffffff or (profile == "cmangos-v8-ref64" and max_polys == 0x80000000),
         "invalid map maximum polygon count for selected profile")
    return {"origin": [ox, oy, oz], "tile_width": width, "tile_height": height,
            "max_tiles": max_tiles, "max_polygons": max_polys,
            "max_polygons_semantics": "fixed-31bit-capacity" if max_polys == 0x80000000 else "positive-i32"}


def inspect_raw(data, bits, params):
    need(bits in (32, 64), "unsupported Detour reference width")
    need(100 <= len(data) <= MAX_FILE, "invalid raw Detour tile size")
    magic, version, x, z, layer = struct.unpack_from("<IIiii", data)
    need((magic, version) == (0x444e4156, 7), "unsupported Detour magic/version")
    need(-4095 <= x <= 4095 and -4095 <= z <= 4095 and layer == 0,
         "unsupported Detour tile coordinates/layer")
    counts = struct.unpack_from("<9i", data, 24)
    need(all(v >= 0 for v in counts), "negative Detour section count")
    poly, verts, links, details, detail_verts, detail_tris, bvs, offmesh, offbase = counts
    need(poly > 0 and verts > 0 and offbase <= poly and offmesh == poly - offbase and details == offbase,
         "invalid Detour polygon/detail/off-mesh partition")
    sections = zip((verts, poly, links, details, detail_verts, detail_tris, bvs, offmesh),
                   (12, 32, 12 if bits == 32 else 16, 12, 12, 4, 16, 36))
    need(100 + sum(count * size for count, size in sections) == len(data),
         "Detour section sizes differ from selected ABI")
    dimensions = struct.unpack_from("<3f", data, 60)
    low, high = struct.unpack_from("<3f", data, 72), struct.unpack_from("<3f", data, 84)
    quant = struct.unpack_from("<f", data, 96)[0]
    need(all(math.isfinite(v) and v >= 0 for v in (*dimensions, quant)), "invalid Detour agent dimensions")
    need(all(math.isfinite(v) and abs(v) <= 10_000_000 for v in (*low, *high))
         and all(a <= b for a, b in zip(low, high)), "invalid Detour bounds")
    ox, _, oz = params["origin"]
    width, height = params["tile_width"], params["tile_height"]
    expected = (ox + x * width, ox + (x + 1) * width, oz + z * height, oz + (z + 1) * height)
    for got, wanted, scale in zip((low[0], high[0], low[2], high[2]), expected, (width, width, height, height)):
        need(abs(got - wanted) <= max(1e-5, scale * 1e-5), "tile placement differs from map grid")
    flags, areas, types = {}, {}, {}
    polygon_start = 100 + verts * 12
    for index in range(poly):
        offset = polygon_start + index * 32
        flag, vertex_count, packed = struct.unpack_from("<HBB", data, offset + 28)
        area, kind = packed & 63, packed >> 6
        need(kind == (1 if index >= offbase else 0), "polygon type differs from off-mesh partition")
        need(vertex_count == 2 if kind else 3 <= vertex_count <= 6, "invalid polygon vertex count")
        for histogram, key in ((flags, flag), (areas, area), (types, kind)):
            histogram[str(key)] = histogram.get(str(key), 0) + 1
    return {"coordinates": [x, z, layer], "polygons": poly, "vertices": verts,
            "bounds_min": list(low), "bounds_max": list(high), "agent_dimensions": list(dimensions),
            "off_mesh_connections": offmesh, "polygon_flags": flags, "polygon_areas": areas,
            "polygon_types": types}


def inspect_wrapper(data, profile, params):
    wrapper, version, bits = profile_info(profile)
    need(len(data) >= wrapper + 100, "truncated WoW tile wrapper")
    magic, detour_version, mmap_version, payload_size = struct.unpack_from("<4I", data)
    need((magic, detour_version, mmap_version) == (0x4d4d4150, 7, version), "tile wrapper/profile mismatch")
    need(payload_size == len(data) - wrapper, "wrapper payload length mismatch")
    liquids = struct.unpack_from("<I", data, 16)[0] if wrapper == 20 else data[16]
    need(liquids in (0, 1), "invalid usesLiquids flag")
    if wrapper == 56:
        need(all(math.isfinite(struct.unpack_from("<f", data, offset)[0]) for offset in (20, 40, 44, 48, 52)),
             "nonfinite AzerothCore wrapper settings")
    payload = data[wrapper:]
    result = inspect_raw(payload, bits, params)
    result.update(wrapper_bytes=wrapper, uses_liquids=bool(liquids), payload_bytes=len(payload))
    return result, payload


def flags_policy(include, exclude):
    integer(include, "include flags", 1, 65535)
    integer(exclude, "exclude flags", 0, 65535)
    need(include & ~exclude, "excluded flags eliminate every included flag")


def import_selection(args):
    profile_info(args.profile)
    label(args.map_id, "map identifier declaration")
    integer(len(args.tile), "selected tile count", 1, 256)
    source_map = args.map.expanduser().resolve(strict=True)
    source_tiles = [path.expanduser().resolve(strict=True) for path in args.tile]
    need(len(set(source_tiles)) == len(source_tiles), "duplicate selected source path")
    extractor, backend = (p.expanduser().resolve(strict=True) for p in (args.extractor, args.backend))
    tools = {"extractor": identity(extractor, limit=128 * 1024 * 1024),
             "backend": identity(backend, limit=128 * 1024 * 1024)}
    bits = backend_bits(backend)
    need(bits == PROFILES[args.profile][2], "backend ABI differs from explicit source profile")
    request = {"format": "bnav-wow-request-v1", "profile": args.profile, "map_id": args.map_id,
               "map": identity(source_map), "tiles": [identity(path) for path in source_tiles], "tools": tools}
    need(sum(item["bytes"] for item in request["tiles"]) <= MAX_TOTAL, "selected sources exceed 256 MiB")
    output = args.output_dir.expanduser().resolve()
    need(not any((parent / ".git").exists() for parent in (output, *output.parents)),
         "import output must remain outside Git repositories")
    need(not output.exists(), "output directory exists; choose a fresh path")
    output.mkdir(parents=True)
    for directory in ("source", "tiles", "receipts"):
        (output / directory).mkdir()
    write_json(output / "requested.json", request)
    manifest = {"format": FORMAT, "status": "INCOMPLETE", "game": "wow", "map_id": args.map_id,
                "profile": args.profile, "reference_bits": bits, "scope": SCOPE.copy(), "tools": tools,
                "request_sha256": sha(read(output / "requested.json", MAX_JSON)),
                "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
                "map": {"source": request["map"]},
                "tiles": [{"source": record, "status": "missing"} for record in request["tiles"]],
                "errors": [], "game_qa": "NOT_RUN", "producer_identity": "UNVERIFIED"}
    try:
        map_bytes = read(source_map)
        need(identity(source_map, map_bytes) == request["map"], "map changed before retention")
        manifest["map"]["retained"] = retain(output, "map.mmap", map_bytes)
        receipt = run([extractor, "inspect-mmap", args.profile, output / "map.mmap"])
        write_json(output / "receipts/map.json", receipt)
        manifest["map"]["receipt"] = identity(Path("receipts/map.json"), read(output / "receipts/map.json", MAX_JSON))
        need(receipt["exit_code"] == 0, f"map inspection failed: {receipt['stderr'].strip()}")
        params = inspect_map(map_bytes, args.profile)
        manifest["map"]["parameters"] = params
        need(len(source_tiles) <= params["max_tiles"], "selection exceeds original map tile capacity")
        seen = set()
        for index, (path, entry) in enumerate(zip(source_tiles, manifest["tiles"])):
            data = read(path)
            need(identity(path, data) == entry["source"], "source tile changed before retention")
            wrapped_name, raw_name = f"source/{index:03}.mmtile", f"tiles/{index:03}.navtile"
            entry["retained"] = retain(output, wrapped_name, data)
            receipt = run([extractor, "extract-mmtile", args.profile, output / wrapped_name, output / raw_name])
            receipt_name = f"receipts/{index:03}.json"
            write_json(output / receipt_name, receipt)
            entry["receipt"] = identity(Path(receipt_name), read(output / receipt_name, MAX_JSON))
            need(receipt["exit_code"] == 0, f"tile extraction failed: {receipt['stderr'].strip()}")
            inspection, payload = inspect_wrapper(data, args.profile, params)
            raw = read(output / raw_name)
            need(raw == payload, "extractor output differs from exact wrapped payload")
            coordinate = tuple(inspection["coordinates"])
            need(coordinate not in seen, "duplicate selected Detour tile coordinates")
            seen.add(coordinate)
            entry.update(status="imported", raw=identity(Path(raw_name), raw), inspection=inspection)
        for path, record in [(source_map, request["map"]), *zip(source_tiles, request["tiles"])]:
            need(identity(path) == record, "source changed during import")
        for name, path in (("extractor", extractor), ("backend", backend)):
            need(identity(path, limit=128 * 1024 * 1024) == tools[name], f"{name} changed during import")
        manifest["status"] = "SELECTED_REGION"
    except (OSError, Invalid, subprocess.TimeoutExpired) as error:
        manifest["errors"].append(str(error))
    manifest["counts"] = {state: sum(item["status"] == state for item in manifest["tiles"])
                          for state in ("imported", "missing")}
    manifest["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "manifest": str(output / "manifest.json"),
                      "counts": manifest["counts"], "errors": manifest["errors"], "scope": SCOPE, "game_qa": "NOT_RUN"}))
    return 0 if manifest["status"] == "SELECTED_REGION" else 3


def validate_selection(path):
    path = path.expanduser().resolve(strict=True)
    root = path.parent
    manifest = decode(read(path, MAX_JSON))
    need(manifest.get("format") == FORMAT and manifest.get("status") == "SELECTED_REGION"
         and manifest.get("errors") == [], "selection is incomplete or unsupported")
    need(manifest.get("game") == "wow" and manifest.get("scope") == SCOPE, "invalid selected-region scope")
    profile = manifest.get("profile")
    _, _, bits = profile_info(profile)
    need(type(manifest.get("reference_bits")) is int and manifest["reference_bits"] == bits, "profile ABI mismatch")
    label(manifest.get("map_id"), "map identifier declaration")
    def local(relative, limit):
        selected = root / relative
        need(not selected.is_symlink() and selected.resolve().is_relative_to(root), "retained file escapes collection")
        return read(selected, limit)
    def retained(record, expected, limit):
        valid_identity(record, limit)
        need(record["path"] == expected, "unexpected retained file path")
        data = local(expected, limit)
        need(identity(Path(expected), data) == record, "retained file size/hash mismatch")
        return data
    request_bytes = local("requested.json", MAX_JSON)
    need(sha(request_bytes) == manifest.get("request_sha256"), "request receipt hash mismatch")
    request = decode(request_bytes)
    need(request.get("format") == "bnav-wow-request-v1", "unsupported request receipt")
    for key in ("profile", "map_id", "tools"):
        need(request.get(key) == manifest.get(key), f"request differs from manifest {key}")
    tools = manifest.get("tools")
    need(isinstance(tools, dict), "tool identities must be an object")
    for name in ("extractor", "backend"):
        valid_identity(tools.get(name), 128 * 1024 * 1024)
    map_record = manifest.get("map")
    need(isinstance(map_record, dict), "missing map record")
    valid_identity(map_record.get("source"), MAX_FILE)
    need(map_record["source"] == request.get("map"), "map source differs from request")
    map_bytes = retained(map_record.get("retained"), "map.mmap", MAX_FILE)
    need(sha(map_bytes) == map_record["source"]["sha256"] and len(map_bytes) == map_record["source"]["bytes"],
         "map differs from source identity")
    params = inspect_map(map_bytes, profile)
    need(params == map_record.get("parameters"), "map parameters differ from retained bytes")
    receipt = decode(retained(map_record.get("receipt"), "receipts/map.json", MAX_JSON))
    argv = receipt.get("argv")
    need(receipt.get("exit_code") == 0 and isinstance(argv, list) and len(argv) == 4
         and argv[:3] == [tools["extractor"]["path"], "inspect-mmap", profile]
         and isinstance(argv[3], str) and Path(argv[3]).as_posix().endswith("/map.mmap"), "map receipt mismatch")
    tiles, requested = manifest.get("tiles"), request.get("tiles")
    need(isinstance(tiles, list) and isinstance(requested, list) and len(tiles) == len(requested), "selection inventory differs from request")
    integer(len(tiles), "selected tile count", 1, min(256, params["max_tiles"]))
    paths, seen, source_paths, total = [], set(), set(), 0
    for index, (entry, source) in enumerate(zip(tiles, requested)):
        need(isinstance(entry, dict) and entry.get("status") == "imported", "missing selected tile")
        valid_identity(source, MAX_FILE)
        need(entry.get("source") == source, "tile source differs from request")
        need(source["path"] not in source_paths, "duplicate source path")
        source_paths.add(source["path"])
        wrapped_name, raw_name = f"source/{index:03}.mmtile", f"tiles/{index:03}.navtile"
        data = retained(entry.get("retained"), wrapped_name, MAX_FILE)
        need(sha(data) == source["sha256"] and len(data) == source["bytes"], "retained wrapper differs from source identity")
        total += len(data)
        inspection, payload = inspect_wrapper(data, profile, params)
        need(inspection == entry.get("inspection"), "tile metadata differs from retained payload")
        coordinate = tuple(inspection["coordinates"])
        need(coordinate not in seen, "duplicate selected Detour tile coordinates")
        seen.add(coordinate)
        raw = retained(entry.get("raw"), raw_name, MAX_FILE)
        need(raw == payload, "raw tile differs from exact source payload")
        receipt = decode(retained(entry.get("receipt"), f"receipts/{index:03}.json", MAX_JSON))
        argv = receipt.get("argv")
        need(receipt.get("exit_code") == 0 and isinstance(argv, list) and len(argv) == 5
             and all(isinstance(v, str) for v in argv)
             and argv[:3] == [tools["extractor"]["path"], "extract-mmtile", profile]
             and Path(argv[3]).as_posix().endswith("/" + wrapped_name)
             and Path(argv[4]).as_posix().endswith("/" + raw_name), "tile extraction receipt mismatch")
        paths.append(root / raw_name)
    need(total <= MAX_TOTAL, "selected sources exceed 256 MiB")
    need(manifest.get("counts") == {"imported": len(tiles), "missing": 0}, "selection summary mismatch")
    return manifest, root / "map.mmap", paths


def check(args):
    manifest, _, paths = validate_selection(args.manifest)
    print(json.dumps({"status": "VERIFIED_SELECTED_REGION", "map_id": manifest["map_id"],
                      "profile": manifest["profile"], "selected_tiles": len(paths), "scope": SCOPE, "game_qa": "NOT_RUN"}))
    return 0


def query(args):
    flags_policy(args.include_flags, args.exclude_flags)
    path = args.manifest.expanduser().resolve(strict=True)
    manifest_hash = sha(read(path, MAX_JSON))
    manifest, map_path, paths = validate_selection(path)
    backend = args.backend.expanduser().resolve(strict=True)
    backend_hash = manifest["tools"]["backend"]["sha256"]
    need(identity(backend, limit=128 * 1024 * 1024)["sha256"] == backend_hash, "backend differs from import receipt")
    need(backend_bits(backend) == manifest["reference_bits"], "backend ABI differs from selected profile")
    coordinates = [*args.start, *args.end]
    need(all(math.isfinite(v) and abs(v) <= 10_000_000 for v in coordinates), "invalid query coordinate")
    result = run([backend, "query-map", manifest["profile"], map_path, args.include_flags, args.exclude_flags,
                  *coordinates, *paths])
    need(result["exit_code"] == 0, f"native query failed: {result['stderr'].strip()}")
    native = decode(result["stdout"])
    need(native.get("complete") is True and native.get("whole_map_coverage") is False
         and native.get("scope") == "selected-tiles", "native query did not report a selected-region projected path")
    need(native.get("profile") == manifest["profile"] and native.get("reference_bits") == manifest["reference_bits"]
         and native.get("include_flags") == args.include_flags and native.get("exclude_flags") == args.exclude_flags,
         "native query profile/flag policy differs from request")
    validate_selection(path)
    need(sha(read(path, MAX_JSON)) == manifest_hash, "selection changed during query")
    need(identity(backend, limit=128 * 1024 * 1024)["sha256"] == backend_hash, "backend changed during query")
    print(json.dumps({"status": "SELECTED_REGION_PROJECTED_PATH", "map_id": manifest["map_id"], "scope": SCOPE,
                      "include_flags": args.include_flags, "exclude_flags": args.exclude_flags,
                      "result": native, "game_qa": "NOT_RUN"}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("import", help="retain only explicitly selected map/tile inputs in a fresh directory")
    ingest.add_argument("--profile", choices=PROFILES, required=True)
    ingest.add_argument("--map-id", required=True, help="caller-declared map identity; not authenticated by mmap format")
    for name in ("map", "extractor", "backend", "output-dir"):
        ingest.add_argument("--" + name, type=Path, required=True)
    ingest.add_argument("--tile", type=Path, action="append", required=True)
    ingest.set_defaults(action=import_selection)
    verify = commands.add_parser("check", help="verify retained sources, exact payloads and selected-map placement")
    verify.add_argument("manifest", type=Path)
    verify.set_defaults(action=check)
    route = commands.add_parser("query", help="query selected tiles with an explicit polygon flag policy")
    route.add_argument("manifest", type=Path)
    route.add_argument("--backend", type=Path, required=True)
    route.add_argument("--include-flags", type=int, required=True)
    route.add_argument("--exclude-flags", type=int, required=True)
    route.add_argument("--start", type=float, nargs=3, required=True)
    route.add_argument("--end", type=float, nargs=3, required=True)
    route.set_defaults(action=query)
    args = parser.parse_args()
    try:
        return args.action(args)
    except (Invalid, OSError, KeyError, TypeError, ValueError, struct.error, subprocess.TimeoutExpired) as error:
        print(f"import_wow_nav: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
