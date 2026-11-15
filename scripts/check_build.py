#!/usr/bin/env python3
"""Read back a local private build and smoke its packaged tools; never publish it."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
import tarfile
from zoneinfo import ZoneInfo


MIB = 1024 * 1024
MAX_ARCHIVE = 256 * MIB
MAX_EXPANDED = 512 * MIB
MAX_MEMBER = 128 * MIB
MAX_MANIFEST = 4 * MIB
MAX_FILES = 4096
MAX_LOG = MIB
CHUNK = MIB
TOOLS = ("bnav-extract", "bot-soak", "bnav-recast", "bnav-recast64")
PYTHON_QUERY_TOOLS = ("source/scripts/bake_nav_collection.py", "source/scripts/import_wow_nav.py")
PYTHON_PROBE_TOOL = "source/scripts/probe_nav_routes.py"
PYTHON_TOOLS = (*PYTHON_QUERY_TOOLS, PYTHON_PROBE_TOOL)
PYTHON_MODULE = "source/scripts/nav_route_metrics.py"
FIXTURE = "source/crates/bot-soak/examples/synthetic-short.csv"
EXTRAS = {"manifest.json", "build.log"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def integer(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, f"invalid {label}")
    return value


def relative_name(value):
    need(isinstance(value, str) and 0 < len(value) <= 512, "invalid archive path length")
    need(not any(ord(c) < 32 or ord(c) == 127 or c in "\\:" for c in value),
         f"unsupported path characters: {value!r}")
    need(all(part not in ("", ".", "..") for part in value.split("/")),
         f"noncanonical relative path: {value!r}")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def open_regular(path):
    # O_NONBLOCK also prevents a substituted FIFO from hanging before fstat.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        stream.close()
        raise ValueError(f"input is not a regular file: {path}")
    return stream


def read_small(path, maximum):
    with open_regular(path) as stream:
        data = stream.read(maximum + 1)
    need(len(data) <= maximum, f"input exceeds {maximum} bytes: {path}")
    return data


def file_digest(stream, maximum):
    result, size = hashlib.sha256(), 0
    while data := stream.read(CHUNK):
        size += len(data)
        need(size <= maximum, f"file exceeds {maximum} bytes")
        result.update(data)
    return result.hexdigest(), size


class BoundedReader:
    """Bound decompressed tar bytes, including metadata and trailing padding."""
    def __init__(self, stream):
        self.stream, self.count = stream, 0

    def read(self, size):
        need(0 <= size <= MAX_MANIFEST, "oversized archive metadata read")
        data = self.stream.read(min(size, MAX_EXPANDED - self.count + 1))
        self.count += len(data)
        need(self.count <= MAX_EXPANDED, "expanded archive exceeds 512 MiB")
        return data


def validate_manifest(data, artifact):
    manifest = json.loads(data, object_pairs_hook=unique_object)
    need(isinstance(manifest, dict), "manifest must be an object")
    need(manifest.get("format") == "banshee-private-build-v1", "unsupported manifest format")
    name = manifest.get("name")
    need(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,159}", name),
         "invalid build name")
    need(artifact.name == f"{name}.tar.gz", "artifact filename does not match build name")
    need(isinstance(manifest.get("source_commit"), str)
         and re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]), "invalid source commit")
    need(isinstance(manifest.get("version"), str) and len(manifest["version"]) <= 80,
         "invalid manifest version")
    files = manifest.get("files")
    need(isinstance(files, dict) and 0 < len(files) <= MAX_FILES, "invalid manifest file count")
    total = 0
    for path, record in files.items():
        relative_name(path)
        need(path not in EXTRAS, f"reserved manifest entry: {path}")
        need(isinstance(record, dict), f"invalid file record: {path}")
        need(isinstance(record.get("sha256"), str)
             and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]), f"invalid file digest: {path}")
        total += integer(record.get("bytes"), MAX_MEMBER, f"file size: {path}")
        if path.startswith("bin/"):
            need(path in {f"bin/{tool}" for tool in TOOLS}, f"unknown packaged executable: {path}")
    need(total <= MAX_EXPANDED, "manifest payload exceeds 512 MiB")
    need({"bin/bnav-extract", "bin/bot-soak", FIXTURE} <= files.keys(),
         "required tools or synthetic fixture missing from manifest")
    need(files[FIXTURE]["bytes"] <= MIB, "synthetic fixture exceeds 1 MiB")
    for path in (*PYTHON_TOOLS, PYTHON_MODULE):
        if path in files:
            need(files[path]["bytes"] <= MIB, f"Python startup source exceeds 1 MiB: {path}")
    native = manifest.get("native_backends", {})
    need(isinstance(native, dict), "native backend identities must be an object")
    for path, identity in native.items():
        need(path in ("bin/bnav-recast", "bin/bnav-recast64") and path in files,
             "native identity names an absent or unsupported executable")
        need(isinstance(identity, dict) and type(identity.get("reference_bits")) is int
             and identity["reference_bits"] in (32, 64), "invalid native reference ABI")
        need(path != "bin/bnav-recast64" or identity["reference_bits"] == 64,
             "explicit 64-bit helper identity has a different ABI")
        need(identity.get("sha256") == files[path]["sha256"], "native executable digest mismatch")
        source_manifest = identity.get("source_manifest")
        need(isinstance(source_manifest, str) and source_manifest.startswith("provenance/")
             and source_manifest in files, "native source manifest is absent")
    need("bin/bnav-recast64" not in files or "bin/bnav-recast64" in native,
         "explicit 64-bit helper requires a native identity")
    return manifest


def verify_archive(raw, manifest, manifest_bytes, output, receipt):
    files = manifest["files"]
    selected = {f"bin/{tool}": output / "bin" / tool for tool in TOOLS if f"bin/{tool}" in files}
    selected[FIXTURE] = output / "synthetic-short.csv"
    for path in (*PYTHON_TOOLS, PYTHON_MODULE):
        if path in files:
            selected[path] = output / path
    seen = set()
    (output / "bin").mkdir(mode=0o700)
    for destination in selected.values():
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with gzip.GzipFile(fileobj=raw, mode="rb") as compressed:
        bounded = BoundedReader(compressed)
        with tarfile.open(fileobj=bounded, mode="r|") as archive:
            for item in archive:
                need(len(seen) < MAX_FILES + len(EXTRAS), "archive member count exceeded")
                relative_name(item.name)
                prefix = manifest["name"] + "/"
                need(item.name.startswith(prefix), f"member outside build root: {item.name}")
                path = item.name[len(prefix):]
                relative_name(path)
                need(path not in seen, f"duplicate archive member: {path}")
                seen.add(path)
                need(item.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and item.sparse is None,
                     f"only ordinary regular files are accepted: {path}")
                need(not item.linkname and not (item.mode & 0o7000), f"unsafe member mode/link: {path}")
                need(path in files or path in EXTRAS, f"unlisted archive member: {path}")
                integer(item.size, MAX_MEMBER, f"member size: {path}")
                expected = files.get(path)
                if expected:
                    need(item.size == expected["bytes"], f"member size differs from manifest: {path}")
                if path == "manifest.json":
                    need(item.size == len(manifest_bytes), "embedded manifest size mismatch")
                if path.startswith("bin/"):
                    need(item.mode & 0o111, f"packaged tool is not executable: {path}")
                with ExitStack() as stack:
                    source = stack.enter_context(archive.extractfile(item))
                    target = stack.enter_context(selected[path].open("xb")) if path in selected else None
                    if target:
                        os.fchmod(target.fileno(), 0o600)
                    result, count = hashlib.sha256(), 0
                    while data := source.read(CHUNK):
                        if path == "manifest.json":
                            need(data == manifest_bytes[count:count + len(data)], "embedded manifest differs from sidecar")
                        count += len(data)
                        result.update(data)
                        if target:
                            target.write(data)
                    need(count == item.size, f"short archive member: {path}")
                    observed = {"sha256": result.hexdigest(), "bytes": count}
                    if expected:
                        need(observed == {key: expected[key] for key in observed}, f"payload digest mismatch: {path}")
                        receipt["files_checked"][path] = observed
                    else:
                        receipt["unlisted_exceptions"][path] = observed
            need(seen == files.keys() | EXTRAS, f"missing archive members: {sorted((files.keys() | EXTRAS) - seen)}")
            # tarfile stops at its first end marker; do not silently accept a
            # second tar stream or hidden nonzero payload after that marker.
            while padding := archive.fileobj.read(CHUNK):
                need(not any(padding), "nonzero bytes follow the tar end marker")
        receipt["expanded_tar_bytes"] = bounded.count
    receipt["extracted"] = {key: str(value) for key, value in selected.items()}
    return selected


def child_limits():
    os.nice(19)
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_LOG, MAX_LOG))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def invoke(argv, label, expected, output, receipt):
    log = output / f"{label}.log"
    record = {"argv": [str(arg) for arg in argv], "cwd": str(output), "expected_exit": expected,
              "timeout_seconds": 20, "output_limit_bytes": MAX_LOG, "log": str(log)}
    receipt["tool_invocations"].append(record)
    with log.open("xb") as stream:
        try:
            result = subprocess.run(record["argv"], cwd=output, stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=20,
                                    preexec_fn=child_limits)
            record["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            record["timed_out"] = True
            raise ValueError(f"{label} exceeded 20 seconds") from None
    data = read_small(log, MAX_LOG)
    record.update({"log_sha256": sha(data), "log_bytes": len(data)})
    need(result.returncode == expected, f"{label}: expected exit {expected}, got {result.returncode}")
    return data.decode("utf-8")


def smoke(selected, manifest, output, receipt):
    # No executable is enabled or invoked until every archive member and the
    # complete artifact digest have passed verification.
    for path, destination in selected.items():
        if path.startswith("bin/"):
            destination.chmod(0o700)
    for tool in TOOLS:
        if f"bin/{tool}" not in selected:
            continue
        binary = selected[f"bin/{tool}"]
        help_text = invoke([binary, "--help"], f"{tool}-help", 0, output, receipt)
        canonical_name = "bnav-recast" if tool == "bnav-recast64" else tool
        need(canonical_name in help_text, f"{tool} help lacks its tool name")
        version = invoke([binary, "--version"], f"{tool}-version", 0, output, receipt).strip()
        expected = f"{canonical_name} {manifest['version']}"
        need(version == expected or (canonical_name == "bnav-recast" and version.startswith(expected + " ")),
             f"{tool} version differs from manifest")
        if canonical_name == "bnav-recast":
            bits = re.search(r"\breference_bits=(32|64)\b", version)
            need(bits is not None, f"{tool} does not declare its ABI")
            if tool == "bnav-recast64":
                need(bits.group(1) == "64", "explicit 64-bit helper has a different ABI")
            declared = manifest.get("native_backends", {}).get(f"bin/{tool}")
            if declared is not None:
                need(declared.get("reference_bits") == int(bits.group(1))
                     and declared.get("sha256") == manifest["files"][f"bin/{tool}"]["sha256"],
                     f"{tool} identity differs from native-backend manifest entry")
    soak = invoke([selected["bin/bot-soak"], "replay", selected[FIXTURE], "--zone", "100"],
                  "synthetic-soak", 3, output, receipt)
    fields = dict(line.split("=", 1) for line in soak.splitlines() if "=" in line)
    need(fields.get("verdict") == "INCOMPLETE" and fields.get("source") == "synthetic"
         and fields.get("live_game_qa") == "NOT_RUN", "soak fixture lost its synthetic/incomplete status")
    receipt["synthetic_soak"] = {"exit_code": 3, "verdict": "INCOMPLETE", "source": "synthetic"}

    # These are fixed repository-owned entry points, never commands supplied by
    # the manifest. Keep the optional shared module beside the scripts so an
    # import cannot accidentally succeed from the current source checkout.
    python_tools = [path for path in PYTHON_TOOLS if path in selected]
    shared_module = PYTHON_MODULE in selected
    receipt["python_startup"] = {"status": "RUNNING" if python_tools else "NOT_PRESENT",
                                 "tools": python_tools, "shared_module_present": shared_module,
                                 "invocations": 0}
    for path in python_tools:
        label = Path(path).stem
        # Ignore Python environment overrides and user-site modules; suppress
        # bytecode creation while retaining sibling imports from the archive.
        argv = [sys.executable, "-E", "-s", "-B", selected[path]]
        help_text = invoke([*argv, "--help"], f"{label}-help", 0, output, receipt)
        need("usage:" in help_text and Path(path).name in help_text, f"{label} help lacks its tool name")
        receipt["python_startup"]["invocations"] += 1
        if path == PYTHON_PROBE_TOOL:
            need("--probes" in help_text and "--manifest" in help_text, "probe help lacks explicit inputs")
        elif shared_module:
            help_text = invoke([*argv, "query", "--help"], f"{label}-query-help", 0, output, receipt)
            need("--max-projection-distance" in help_text, f"{label} query help lacks projection policy")
            receipt["python_startup"]["invocations"] += 1
    if python_tools:
        receipt["python_startup"]["status"] = "PASS"


def external_output(value):
    output = value.expanduser().absolute()
    need(not output.exists() and not output.is_symlink(), "evidence destination already exists")
    parent = output.parent.resolve(strict=True)
    for ancestor in (parent, *parent.parents):
        need(not (ancestor / ".git").exists(), "evidence must be outside a git worktree")
    return parent / output.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--expected-bytes", type=int, required=True,
                        help="Archive bytes from package_build.py JSON or recorded publisher intake")
    parser.add_argument("--manifest", type=Path, help="Default: manifest.json beside artifact")
    parser.add_argument("--sha256-file", type=Path, help="Default: SHA256SUMS beside artifact")
    parser.add_argument("--evidence", type=Path, required=True, help="New external directory; parent must exist")
    args = parser.parse_args()
    output, receipt = None, None
    try:
        artifact = args.artifact.expanduser().absolute()
        manifest_path = (args.manifest or artifact.parent / "manifest.json").expanduser().absolute()
        sums_path = (args.sha256_file or artifact.parent / "SHA256SUMS").expanduser().absolute()
        integer(args.expected_bytes, MAX_ARCHIVE, "expected archive bytes (max 256 MiB)")
        need(args.expected_bytes > 0, "expected archive bytes must be positive")
        output = external_output(args.evidence)
        output.mkdir(mode=0o700, exist_ok=False)
        receipt = {"format": "banshee-build-readback-v1", "verdict": "FAIL",
                   "created_cst": datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M:%S %Z"),
                   "checker": str(Path(__file__).resolve()), "checker_sha256": sha(Path(__file__).read_bytes()),
                   "artifact": str(artifact), "manifest": str(manifest_path), "sha256_file": str(sums_path),
                   "expected_bytes": args.expected_bytes, "expected_size_source": "--expected-bytes",
                   "files_checked": {}, "unlisted_exceptions": {}, "tool_invocations": [],
                   "game_qa": "NOT_RUN", "native_ffxi_p0": "NOT_RUN", "nav_smoke": "NOT_RUN",
                   "publication": "NOT_PERFORMED", "live_deployment": "NOT_PERFORMED"}
        manifest_bytes = read_small(manifest_path, MAX_MANIFEST)
        manifest = validate_manifest(manifest_bytes, artifact)
        sums = read_small(sums_path, 64 * 1024)
        match = re.fullmatch(rb"([0-9a-f]{64})  ([^\r\n]+)\n?", sums)
        need(match is not None and match[2].decode("utf-8") == artifact.name,
             "SHA256SUMS must contain exactly this archive's SHA-256 and filename")
        expected_sha = match[1].decode("ascii")
        receipt.update({"manifest_sha256": sha(manifest_bytes), "sha256_file_sha256": sha(sums),
                        "expected_sha256": expected_sha, "source_commit": manifest["source_commit"],
                        "build": manifest.get("build"), "version": manifest["version"]})
        with open_regular(artifact) as raw:
            need(os.fstat(raw.fileno()).st_size == args.expected_bytes, "archive byte size mismatch")
            observed, size = file_digest(raw, MAX_ARCHIVE)
            receipt.update({"sha256": observed, "bytes": size})
            need(observed == expected_sha and size == args.expected_bytes, "archive checksum/size mismatch")
            raw.seek(0)
            selected = verify_archive(raw, manifest, manifest_bytes, output, receipt)
            raw.seek(0)
            need(file_digest(raw, MAX_ARCHIVE) == (observed, size), "artifact changed during readback")
        need(read_small(manifest_path, MAX_MANIFEST) == manifest_bytes
             and read_small(sums_path, 64 * 1024) == sums, "sidecars changed during readback")
        smoke(selected, manifest, output, receipt)
        receipt["verified_files"] = len(receipt["files_checked"])
        receipt["verdict"] = "PASS"
    except (OSError, ValueError, KeyError, tarfile.TarError, EOFError) as error:
        if receipt is not None:
            receipt["error"] = str(error)
            if receipt.get("python_startup", {}).get("status") == "RUNNING":
                receipt["python_startup"]["status"] = "FAIL"
        else:
            print(f"readback failed: {error}", file=sys.stderr)
            return 1
    if receipt is not None:
        destination = output / "result.json"
        with destination.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"verdict": receipt["verdict"], "receipt": str(destination),
                          "verified_files": receipt.get("verified_files", 0),
                          **({"error": receipt["error"]} if "error" in receipt else {})}, indent=2))
        return 0 if receipt["verdict"] == "PASS" else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
