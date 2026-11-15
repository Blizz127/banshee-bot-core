#!/usr/bin/env python3
"""Build a private, reviewable QA candidate. Does not publish or deploy it."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib
from datetime import datetime
from zoneinfo import ZoneInfo


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, help="Unique numeric build number")
    parser.add_argument("--output", type=Path, required=True, help="Private build directory outside git")
    parser.add_argument("--backend", type=Path, help="Optional built native Recast executable")
    parser.add_argument("--backend-manifest", type=Path)
    parser.add_argument("--backend-license", type=Path)
    parser.add_argument("--verification", action="append", type=Path, default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not re.fullmatch(r"[0-9]{1,8}", args.build):
        parser.error("build must be 1..8 decimal digits")
    if any((args.backend, args.backend_manifest, args.backend_license)) and not all(
        (args.backend, args.backend_manifest, args.backend_license)
    ):
        parser.error("backend, backend-manifest and backend-license must be supplied together")
    output = args.output.expanduser().resolve()
    if output == root or root in output.parents:
        parser.error("build output must remain outside the repository")

    def command(argv, expected=0):
        result = subprocess.run(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode != expected:
            raise RuntimeError(f"{argv!r}: expected {expected}, got {result.returncode}\n{result.stdout.decode(errors='replace')}")
        return result.stdout

    if command(["git", "status", "--porcelain"]):
        parser.error("commit the reviewed source first; refusing to label a dirty build")
    commit = command(["git", "rev-parse", "HEAD"]).decode().strip()
    tree = command(["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
    version = tomllib.loads((root / "crates/banshee-bot-core/Cargo.toml").read_text())["package"]["version"]
    name = f"banshee-bot-core-{version}-build{args.build}"
    destination = output / name
    destination.mkdir(parents=True, exist_ok=False)
    build_log = command(["nice", "-n", "19", "cargo", "build", "--release", "--locked", "--offline", "-j2"])
    (destination / "build.log").write_bytes(build_log)

    payload = {}
    checks = {}
    for binary in ("bnav-extract", "bot-soak"):
        path = root / "target" / "release" / binary
        payload[f"bin/{binary}"] = (path.read_bytes(), 0o755)
        checks[f"{binary}_help"] = command([str(path), "--help"]).decode()
        checks[f"{binary}_version"] = command([str(path), "--version"]).decode().strip()
    checks["synthetic_soak_exit3"] = command([
        str(root / "target/release/bot-soak"), "replay",
        str(root / "crates/bot-soak/examples/synthetic-short.csv"), "--zone", "100"
    ], expected=3).decode()
    if args.backend:
        payload["bin/bnav-recast"] = (args.backend.read_bytes(), 0o755)
        payload["provenance/backend-manifest.json"] = (args.backend_manifest.read_bytes(), 0o644)
        payload["provenance/Recast-LICENSE.txt"] = (args.backend_license.read_bytes(), 0o644)
        checks["bnav_recast_help"] = command([str(args.backend.resolve()), "--help"]).decode()
    for i, path in enumerate(args.verification):
        data = path.read_bytes()
        if path.suffix == ".json":
            receipt = json.loads(data)
            for relative, expected in receipt.get("core_files_after", {}).items():
                if digest((root / relative).read_bytes()) != expected:
                    raise RuntimeError(f"compatibility evidence no longer matches {relative}")
        payload[f"verification/{i + 1}-{path.name}"] = (data, 0o644)

    # Archive the exact clean commit, without game assets, ignored outputs or .git.
    source = command(["git", "archive", "--format=tar", "--prefix=source/", commit])
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:") as archive:
        for item in archive:
            if item.isfile():
                payload[item.name] = (archive.extractfile(item).read(), item.mode)
            elif not item.isdir():
                raise RuntimeError(f"unsupported source archive member: {item.name}")

    if command(["git", "status", "--porcelain"]) or command(["git", "rev-parse", "HEAD"]).decode().strip() != commit:
        raise RuntimeError("source changed during build; candidate not packaged")
    manifest = {
        "format": "banshee-private-build-v1",
        "name": name,
        "build": args.build,
        "version": version,
        "created_cst": datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source_commit": commit,
        "source_tree": tree,
        "spec_sha256": digest((root / "docs/BANSHEE_BOT_CORE_SPEC_20261115.md").read_bytes()),
        "rustc": command(["rustc", "--version"]).decode().strip(),
        "status": "QA_CANDIDATE",
        "game_qa": "NOT_RUN",
        "native_ffxi_p0": "NOT_RUN",
        "live_deployment": "NOT_PERFORMED",
        "publication": "NOT_PERFORMED",
        "default_features": "OFF",
        "startup_checks": checks,
        "files": {key: {"sha256": digest(value[0]), "bytes": len(value[0])} for key, value in sorted(payload.items())},
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    (destination / "manifest.json").write_bytes(manifest_bytes)
    payload["manifest.json"] = (manifest_bytes, 0o644)
    payload["build.log"] = (build_log, 0o644)
    artifact = destination / f"{name}.tar.gz"
    with artifact.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as compressed:
        with tarfile.open(fileobj=compressed, mode="w|") as archive:
            for relative, (data, mode) in sorted(payload.items()):
                member = tarfile.TarInfo(f"{name}/{relative}")
                member.size, member.mode, member.mtime = len(data), mode, 0
                archive.addfile(member, io.BytesIO(data))
    sha256 = digest(artifact.read_bytes())
    (destination / "SHA256SUMS").write_text(f"{sha256}  {artifact.name}\n")
    print(json.dumps({"artifact": str(artifact), "sha256": sha256, "bytes": artifact.stat().st_size,
                      "manifest": str(destination / "manifest.json"), "status": "QA_CANDIDATE"}, indent=2))


if __name__ == "__main__":
    main()
