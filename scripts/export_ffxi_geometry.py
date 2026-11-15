#!/usr/bin/env python3
"""Build a pinned external FFXI reader and export one explicit offline region.

The repository contains only this original wrapper and its original Rust driver.
Sources, asset snapshots, compiler output and geometry stay in a fresh private
directory. No server/client processes, dependency downloads or source edits.
"""
import argparse
from datetime import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tomllib
from zoneinfo import ZoneInfo

SOURCE_REVISION = "a13dabcd550e0a777be5077804ba3d51683cfa19"
UPSTREAM_REVISION = "a8c75ab4e981d6056cd2860d8f8e12eacfff7671"
SOURCE_PATHS = [
    "server/crates/forever-audit", "server/crates/forever-safety",
    "server/crates/ffxi-dat", "server/crates/detour-sys",
    "server/Cargo.lock", "ffxi_check/data/oplen.json",
]
MAX_INPUT_BYTES = 64 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open("x") as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.write("\n")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def copy_input(source, destination):
    """Bound each immutable snapshot; hash precisely the bytes actually copied."""
    before = source.stat()
    if not source.is_file() or before.st_size > MAX_INPUT_BYTES:
        raise ValueError(f"not a bounded input file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    with source.open("rb") as src, destination.open("xb") as dst:
        while block := src.read(1024 * 1024):
            size += len(block)
            if size > MAX_INPUT_BYTES:
                raise ValueError(f"input grew beyond limit: {source}")
            digest.update(block)
            dst.write(block)
    after = source.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError(f"input changed during snapshot: {source}")
    return {"path": str(source), "snapshot": str(destination), "bytes": size, "sha256": digest.hexdigest()}


def run_logged(argv, directory, log_name, env=None):
    with (directory / f"{log_name}.log").open("x") as log:
        run = subprocess.run(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT, env=env)
    write_json(directory / f"{log_name}.json", {"argv": list(map(str, argv)), "exit_code": run.returncode})
    if run.returncode:
        raise RuntimeError(f"{log_name} failed ({run.returncode}); see {directory / (log_name + '.log')}")


def stage_sources(repo, output):
    if git(repo, "rev-parse", SOURCE_REVISION + "^{commit}").decode().strip() != SOURCE_REVISION:
        raise ValueError("owning source commit did not resolve exactly")
    archive = git(repo, "archive", "--format=tar", SOURCE_REVISION, *SOURCE_PATHS)
    if len(archive) > MAX_INPUT_BYTES:
        raise ValueError("source archive exceeds 64 MiB")
    stage = output / "external-source"
    stage.mkdir()
    identities = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not (member.isdir() or member.isfile()):
                raise ValueError(f"unsupported archive member: {member.name}")
            dest = stage / member.name
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                data = tar.extractfile(member).read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as file:
                    file.write(data)
                identities.append({"path": member.name, "bytes": len(data), "sha256": sha(data)})
    return stage, {"repository": str(repo), "revision": SOURCE_REVISION,
                   "archive_sha256": sha(archive), "files": identities}


def main():
    wrapper_path = Path(__file__).resolve()
    wrapper_sha256 = sha(wrapper_path.read_bytes())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffxi-source", required=True, type=Path)
    parser.add_argument("--forever-client-source", required=True, type=Path, help="MIT licence provenance only; never launched")
    parser.add_argument("--client-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--bounds-min", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--bounds-max", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--metres-per-unit-assumption", type=float, required=True, help="explicit unverified declaration; no coordinate scaling")
    parser.add_argument("--format-evidence", required=True, help="known reader source/format evidence; entropy alone is not format proof")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 2:
        parser.error("--jobs must be 1 or 2; default 1 for current host pressure")
    if not all(math.isfinite(n) for n in args.bounds_min + args.bounds_max) or not all(a < b for a, b in zip(args.bounds_min, args.bounds_max)):
        parser.error("bounds must be finite, strictly increasing source-frame AABB")
    if not math.isfinite(args.metres_per_unit_assumption) or args.metres_per_unit_assumption <= 0:
        parser.error("explicit metres-per-unit assumption must be finite and positive")
    if not args.format_evidence.strip():
        parser.error("--format-evidence cannot be empty")
    repo = Path(__file__).resolve().parents[1]
    source = args.ffxi_source.resolve(strict=True)
    upstream = args.forever_client_source.resolve(strict=True)
    client = args.client_root.resolve(strict=True)
    output = args.output_dir.expanduser().resolve()
    private_root = (Path.home() / ".local/share/banshee-bot-core").resolve()
    if not output.is_relative_to(private_root) or any(output.is_relative_to(p) for p in (repo, source, upstream, client)):
        parser.error("output must be in ~/.local/share/banshee-bot-core and outside all source/client/repository trees")
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        parser.error("output must not be inside any Git checkout or worktree")
    output.mkdir(parents=True, exist_ok=False)
    # This first adapter intentionally selects one exact zone; no all-zone scan.
    relative = "ROM/1/31.DAT"
    stage, source_identity = stage_sources(source, output)
    licence = git(upstream, "show", UPSTREAM_REVISION + ":LICENSE")
    (output / "FOREVER-CLIENT-MIT-LICENSE.txt").write_bytes(licence)
    write_json(output / "source-identity.json", {**source_identity,
        "reader_upstream": {"repository": str(upstream), "revision": UPSTREAM_REVISION,
                            "licence": "MIT", "licence_sha256": sha(licence)},
        "licence_scope": "MIT applies to attributed forever-client reader; owning FFXI workspace declares no blanket licence",
        "owning_repository_modified": False, "staged_crate_files_modified": False})

    server = stage / "server"
    driver = server / "crates/bnav-ffxi-export-driver"
    (driver / "src").mkdir(parents=True)
    original_driver = repo / "scripts/ffxi_geometry_driver.rs"
    driver_bytes = original_driver.read_bytes()
    (driver / "src/main.rs").write_bytes(driver_bytes)
    (driver / "Cargo.toml").write_text('[package]\nname = "bnav-ffxi-export-driver"\nversion = "0.1.0"\nedition = "2021"\npublish = false\n\n[dependencies]\nforever-audit = { path = "../forever-audit" }\nserde_json = "1"\nsha2 = "0.10"\n')
    (server / "Cargo.toml").write_text('[workspace]\nresolver = "2"\nmembers = ["crates/bnav-ffxi-export-driver", "crates/forever-audit", "crates/ffxi-dat", "crates/forever-safety", "crates/detour-sys"]\n\n[workspace.package]\nedition = "2021"\npublish = false\n')
    lock = server / "Cargo.lock"
    original_lock = lock.read_bytes()
    pinned_packages = {(p["name"], p["version"], p.get("source"), p.get("checksum"))
                       for p in tomllib.loads(original_lock.decode())["package"]}
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(output / "cargo-target")
    env["CARGO_NET_OFFLINE"] = "true"
    manifest = server / "Cargo.toml"
    # Prune the copied lock to this smaller workspace without updating any
    # dependency identity. Missing cache entries fail instead of downloading.
    run_logged(["nice", "-n", "19", "cargo", "metadata", "--offline", "--format-version", "1",
                "--manifest-path", manifest], output, "resolve", env)
    resolved_packages = tomllib.loads(lock.read_text())["package"]
    for package in resolved_packages:
        identity = (package["name"], package["version"], package.get("source"), package.get("checksum"))
        if package.get("source") and identity not in pinned_packages:
            raise RuntimeError(f"offline resolution changed a pinned registry dependency: {identity[:2]}")
    lock_before = sha(lock.read_bytes())
    run_logged(["nice", "-n", "19", "cargo", "build", "--offline", "--locked", "--manifest-path", manifest,
                "--package", "bnav-ffxi-export-driver", "-j", args.jobs], output, "build", env)
    if sha(lock.read_bytes()) != lock_before:
        raise RuntimeError("locked build changed staged Cargo.lock")
    if original_driver.read_bytes() != driver_bytes or (driver / "src/main.rs").read_bytes() != driver_bytes:
        raise RuntimeError("original or staged driver changed during build; refusing to label binary")
    for entry in source_identity["files"]:
        if entry["path"] != "server/Cargo.lock" and sha((stage / entry["path"]).read_bytes()) != entry["sha256"]:
            raise RuntimeError(f"external source changed during build: {entry['path']}")
    binary = output / "cargo-target/debug/bnav-ffxi-export-driver"
    run_logged([binary, "--help"], output, "startup")
    if sha(wrapper_path.read_bytes()) != wrapper_sha256:
        raise RuntimeError("export wrapper changed during build; refuse mismatched provenance")
    write_json(output / "build-manifest.json", {"status": "VERIFIED", "scope": "offline driver build and startup only",
        "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "cargo": subprocess.check_output(["cargo", "--version"], text=True).strip(),
        "wrapper_sha256": wrapper_sha256,
        "binary": str(binary), "binary_sha256": sha(binary.read_bytes()), "source_revision": SOURCE_REVISION,
        "original_driver_sha256": sha(driver_bytes), "locked_resolution_sha256": lock_before,
        "jobs": args.jobs, "offline": True, "external_source_edited": False,
        "original_source_lock_sha256": sha(original_lock),
        "staging_changes": "new minimal workspace and original driver; original crate files unchanged; copied lock reduced offline with registry identities verified against original"})

    snapshot = output / "owned-inputs"
    snapshot.mkdir()
    inputs = []
    names = ["FFXiMain.dll", relative]
    for n in range(1, 10):
        directory, suffix = ("", "") if n == 1 else (f"ROM{n}/", str(n))
        names += [f"{directory}{kind}{suffix}.DAT" for kind in ("VTABLE", "FTABLE")]
    for name in names:
        path = client / name
        if not path.is_file():
            if name in ("FFXiMain.dll", relative, "VTABLE.DAT", "FTABLE.DAT"):
                raise ValueError(f"missing required owned input: {path}")
            continue
        if not path.resolve().is_relative_to(client):
            raise ValueError(f"owned input resolves outside selected client: {path}")
        inputs.append(copy_input(path, snapshot / name))
    write_json(output / "owned-inputs.json", inputs)
    selected = next(r for r in inputs if r["path"] == str(client / relative))
    request = {"snapshot_root": str(snapshot), "output_dir": str(output), "zone_id": 230,
        "zone_name": "Southern San d'Oria", "region_name": "bounded homepoint-source region",
        "asset_relative": relative, "asset_sha256": selected["sha256"], "owner_asset_path": str(client / relative),
        "bounds_min": args.bounds_min, "bounds_max": args.bounds_max, "source_revision": SOURCE_REVISION,
        "metres_per_unit_assumption": args.metres_per_unit_assumption, "format_evidence": args.format_evidence}
    write_json(output / "request.json", request)
    run_logged(["nice", "-n", "19", binary, output / "request.json"], output, "export")
    exported = json.loads((output / "export-manifest.json").read_text())
    geometry = output / "region.obj"
    geometry_sha = sha(geometry.read_bytes())
    if exported["extraction"]["obj_sha256"] != geometry_sha:
        raise RuntimeError("returned exporter digest differs from OBJ")
    limitations = exported["coverage"]["omissions"] + [
        "selected type-9 water causes total refusal; other surface semantics are not certified",
        "physical metres/unit, navigation agent settings and game walkability are uncalibrated",
        "no server/client runtime, native adapter query or Game QA proof",
        "existing reader may skip malformed source records; completeness cannot be inferred from success",
    ]
    write_json(output / "geometry.json", {"format": "bnav-geometry-v1", "game": "FFXI",
        "zone": "230 Southern San d'Oria bounded homepoint-source region",
        "geometry": {"path": str(geometry), "sha256": geometry_sha},
        "coordinates": {"up_axis": "Y", "units": f"FFXI source world units; {args.metres_per_unit_assumption:g} metre/unit caller assumption, uncalibrated; no rescale",
                        "transform": "(x,-y,-z), applied once by owning exporter; winding aligned to transformed stored normals"},
        "coverage": {"scope": "incomplete static source-AABB whole-triangle selection, not a complete zone", "limitations": limitations,
                     "requested_source_bounds": {"min": args.bounds_min, "max": args.bounds_max},
                     "actual_output_bounds": exported["coordinates"]["actual_output_bounds"], "collision_complete": False},
        "provenance": {"classification": "owner_asset", "description": "Known pinned FFXI source decoder and bounded exporter run offline on explicitly staged owned files; not unknown-format research",
                       "artifacts": [{"path": str(output / name), "sha256": sha((output / name).read_bytes())}
                                     for name in ("source-identity.json", "owned-inputs.json", "build-manifest.json", "request.json", "export-manifest.json", "raw-observation.json")]}})
    print(json.dumps({"status": "OBSERVED", "geometry_manifest": str(output / "geometry.json"),
                      "obj_sha256": geometry_sha, "triangles": exported["coverage"]["included_triangles"],
                      "game_qa": "unverified", "collision_complete": False}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FFXI geometry export stopped: {exc}", file=sys.stderr)
        sys.exit(1)
