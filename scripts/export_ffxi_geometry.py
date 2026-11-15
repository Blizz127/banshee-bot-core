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
MAX_MANIFEST_BYTES = 1024 * 1024


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


def pinned_source(repo):
    if git(repo, "rev-parse", SOURCE_REVISION + "^{commit}").decode().strip() != SOURCE_REVISION:
        raise ValueError("owning source commit did not resolve exactly")
    archive = git(repo, "archive", "--format=tar", SOURCE_REVISION, *SOURCE_PATHS)
    if len(archive) > MAX_INPUT_BYTES:
        raise ValueError("source archive exceeds 64 MiB")
    identities = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or not (member.isdir() or member.isfile()):
                raise ValueError(f"unsupported archive member: {member.name}")
            if member.isfile():
                data = tar.extractfile(member).read()
                identities.append({"path": member.name, "bytes": len(data), "sha256": sha(data)})
    return archive, {"repository": str(repo), "revision": SOURCE_REVISION,
                     "archive_sha256": sha(archive), "files": identities}


def stage_sources(repo, output):
    archive, identity = pinned_source(repo)
    stage = output / "external-source"
    stage.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            dest = stage / member.name
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as file:
                    file.write(tar.extractfile(member).read())
    return stage, identity


def asset_relative(value):
    relative = PurePosixPath(value)
    if (not value or relative.is_absolute() or ".." in relative.parts
            or "\\" in value or str(relative) != value or relative.suffix != ".DAT"):
        raise ValueError("expected asset path must be a normalized relative .DAT path without traversal")
    return value


def bounded_bytes(path, limit=MAX_INPUT_BYTES):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"not a bounded retained file: {path}")
    with path.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"retained file exceeds limit: {path}")
    return data


def retained_file(root, relative):
    path = root / relative
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError(f"retained input resolves outside its build: {path}")
    return path


def verify_retained_build(root, expected_source, driver_bytes, licence_bytes):
    """Verify an original staged build against independently read pinned objects.

    This checks local provenance consistency, not a signed compiler attestation.
    Reused outputs intentionally have no source snapshot and cannot be chained.
    """
    source_path = retained_file(root, "source-identity.json")
    build_path = retained_file(root, "build-manifest.json")
    source_bytes = bounded_bytes(source_path, MAX_MANIFEST_BYTES)
    build_bytes = bounded_bytes(build_path, MAX_MANIFEST_BYTES)
    source, build = json.loads(source_bytes), json.loads(build_bytes)
    if not isinstance(source, dict) or not isinstance(build, dict):
        raise ValueError("retained manifests must be objects")
    for key in ("revision", "archive_sha256", "files"):
        if source.get(key) != expected_source[key]:
            raise ValueError(f"retained source manifest differs from pinned objects: {key}")
    if (build.get("status") != "VERIFIED" or build.get("source_revision") != SOURCE_REVISION
            or build.get("offline") is not True or build.get("external_source_edited") is not False):
        raise ValueError("retained build is not a verified offline build of the pinned source")
    if build.get("original_driver_sha256") != sha(driver_bytes):
        raise ValueError("retained driver source differs from the current original driver")
    staged_driver = retained_file(root, "external-source/server/crates/bnav-ffxi-export-driver/src/main.rs")
    if bounded_bytes(staged_driver) != driver_bytes:
        raise ValueError("retained staged driver bytes changed")
    original_lock_sha = next(p["sha256"] for p in expected_source["files"] if p["path"] == "server/Cargo.lock")
    if build.get("original_source_lock_sha256") != original_lock_sha:
        raise ValueError("retained original lock identity differs from pinned source")
    for entry in expected_source["files"]:
        path = retained_file(root, "external-source/" + entry["path"])
        expected = build.get("locked_resolution_sha256") if entry["path"] == "server/Cargo.lock" else entry["sha256"]
        if sha(bounded_bytes(path)) != expected:
            raise ValueError(f"retained staged source or lock changed: {entry['path']}")
    upstream = source.get("reader_upstream", {})
    if (not isinstance(upstream, dict) or upstream.get("revision") != UPSTREAM_REVISION or upstream.get("licence") != "MIT"
            or upstream.get("licence_sha256") != sha(licence_bytes)
            or bounded_bytes(retained_file(root, "FOREVER-CLIENT-MIT-LICENSE.txt")) != licence_bytes):
        raise ValueError("retained reader licence provenance differs from pinned source")
    binary = retained_file(root, "cargo-target/debug/bnav-ffxi-export-driver")
    if Path(build.get("binary", "")).resolve() != binary.resolve():
        raise ValueError("retained binary path differs from the recorded build")
    binary_bytes = bounded_bytes(binary)
    if sha(binary_bytes) != build.get("binary_sha256"):
        raise ValueError("retained executable digest differs from the build manifest")
    return binary_bytes, {
        "retained_root": str(root), "source_revision": SOURCE_REVISION,
        "retained_build_manifest": {"path": str(build_path), "sha256": sha(build_bytes)},
        "retained_source_manifest": {"path": str(source_path), "sha256": sha(source_bytes)},
        "retained_binary": {"path": str(binary), "sha256": sha(binary_bytes)},
        "original_driver_sha256": sha(driver_bytes), "source_archive_sha256": expected_source["archive_sha256"],
        "source_files_verified": len(expected_source["files"]),
        "source_snapshots_copied": False, "scope": "local retained build consistency against pinned owning git objects; no new compilation",
    }


def reuse_driver(args, repo, source, upstream, output, wrapper_path, wrapper_sha256):
    root = args.reuse_build.expanduser().resolve(strict=True)
    if not root.is_relative_to((Path.home() / ".local/share/banshee-bot-core").resolve()):
        raise ValueError("retained build must be beneath the private Banshee data root")
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("retained build must not be inside a Git checkout or worktree")
    _, expected_source = pinned_source(source)
    driver_path = repo / "scripts/ffxi_geometry_driver.rs"
    driver_bytes = driver_path.read_bytes()
    licence_bytes = git(upstream, "show", UPSTREAM_REVISION + ":LICENSE")
    binary_bytes, verification = verify_retained_build(root, expected_source, driver_bytes, licence_bytes)
    binary = output / "reused-driver"
    with binary.open("xb") as file:
        file.write(binary_bytes)
    binary.chmod(0o700)
    (output / "FOREVER-CLIENT-MIT-LICENSE.txt").write_bytes(licence_bytes)
    run_logged([binary, "--help"], output, "startup")
    if (driver_path.read_bytes() != driver_bytes or sha(wrapper_path.read_bytes()) != wrapper_sha256
            or binary.read_bytes() != binary_bytes):
        raise RuntimeError("wrapper, driver or executable changed during reuse verification")
    write_json(output / "source-reference.json", verification)
    write_json(output / "build-manifest.json", {"status": "VERIFIED", "mode": "retained_build_reuse",
        "scope": "retained source/driver/executable verification and startup only; no compilation",
        "created_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(), "wrapper_sha256": wrapper_sha256,
        "binary": str(binary), "binary_sha256": sha(binary_bytes), "source_revision": SOURCE_REVISION,
        "original_driver_sha256": sha(driver_bytes), "binary_copied": True, "source_snapshots_copied": False,
        "retained_build_manifest": verification["retained_build_manifest"]})
    return binary, "source-reference.json"


def build_driver(args, repo, source, upstream, output, wrapper_path, wrapper_sha256):
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

    return binary, "source-identity.json"


def main():
    wrapper_path = Path(__file__).resolve()
    wrapper_sha256 = sha(wrapper_path.read_bytes())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffxi-source", required=True, type=Path)
    parser.add_argument("--forever-client-source", required=True, type=Path, help="MIT licence provenance only; never launched")
    parser.add_argument("--client-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--zone-id", required=True, type=int, help="one explicit source zone ID; no zone scan")
    parser.add_argument("--zone-name", required=True, help="caller-declared zone name for provenance")
    parser.add_argument("--region-name", required=True, help="source-backed region/fixture description")
    parser.add_argument("--expected-asset-relative", required=True, help="exact source-backed DAT path; existing ROM table resolver must agree")
    parser.add_argument("--reuse-build", type=Path, help="verify and reuse an original retained driver build; no dependency rebuild")
    parser.add_argument("--bounds-min", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--bounds-max", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--metres-per-unit-assumption", type=float, required=True, help="explicit unverified declaration; no coordinate scaling")
    parser.add_argument("--format-evidence", required=True, help="known reader source/format evidence; entropy alone is not format proof")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.zone_id <= 65535:
        parser.error("--zone-id must be an explicit positive u16 source zone ID")
    if not args.zone_name.strip() or not args.region_name.strip():
        parser.error("zone and region names must not be empty")
    try:
        relative = asset_relative(args.expected_asset_relative)
    except ValueError as exc:
        parser.error(str(exc))
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
    if args.reuse_build is None:
        binary, source_artifact = build_driver(args, repo, source, upstream, output, wrapper_path, wrapper_sha256)
    else:
        binary, source_artifact = reuse_driver(args, repo, source, upstream, output, wrapper_path, wrapper_sha256)

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
    request = {"snapshot_root": str(snapshot), "output_dir": str(output), "zone_id": args.zone_id,
        "zone_name": args.zone_name, "region_name": args.region_name,
        "asset_relative": relative, "asset_sha256": selected["sha256"], "owner_asset_path": str(client / relative),
        "bounds_min": args.bounds_min, "bounds_max": args.bounds_max, "source_revision": SOURCE_REVISION,
        "metres_per_unit_assumption": args.metres_per_unit_assumption, "format_evidence": args.format_evidence}
    write_json(output / "request.json", request)
    run_logged(["nice", "-n", "19", binary, output / "request.json"], output, "export")
    build_identity = json.loads((output / "build-manifest.json").read_text())
    if (sha(binary.read_bytes()) != build_identity["binary_sha256"]
            or sha(wrapper_path.read_bytes()) != wrapper_sha256
            or sha((repo / "scripts/ffxi_geometry_driver.rs").read_bytes()) != build_identity["original_driver_sha256"]):
        raise RuntimeError("wrapper, driver or executable changed during export")
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
        "zone": f"{args.zone_id} {args.zone_name} {args.region_name}",
        "geometry": {"path": str(geometry), "sha256": geometry_sha},
        "coordinates": {"up_axis": "Y", "units": f"FFXI source world units; {args.metres_per_unit_assumption:g} metre/unit caller assumption, uncalibrated; no rescale",
                        "transform": "(x,-y,-z), applied once by owning exporter; winding aligned to transformed stored normals"},
        "coverage": {"scope": "incomplete static source-AABB whole-triangle selection, not a complete zone", "limitations": limitations,
                     "requested_source_bounds": {"min": args.bounds_min, "max": args.bounds_max},
                     "actual_output_bounds": exported["coordinates"]["actual_output_bounds"], "collision_complete": False},
        "provenance": {"classification": "owner_asset", "description": "Known pinned FFXI source decoder and bounded exporter run offline on explicitly staged owned files; not unknown-format research",
                       "artifacts": [{"path": str(output / name), "sha256": sha((output / name).read_bytes())}
                                     for name in (source_artifact, "owned-inputs.json", "build-manifest.json", "request.json", "export-manifest.json", "raw-observation.json")]}})
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
