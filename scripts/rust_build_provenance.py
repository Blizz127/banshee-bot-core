"""Observe a fresh host Rust build; this is not a hermetic-build attestation."""
import hashlib
import os
from pathlib import Path
import re
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_inputs(root, command):
    result = {}
    for raw in command(["git", "ls-files", "-z"]).split(b"\0"):
        if not raw:
            continue
        relative = os.fsdecode(raw)
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"build source must be an ordinary file: {relative}")
        result[relative] = digest(path.read_bytes())
    return result


def build_rust_tools(root, destination, commit, tree, command, jobs=2):
    """Return build log, binary bytes and a source/toolchain/output association.

    command runs argument lists in root and accepts an optional env mapping.
    A new target directory prevents reuse of previous Cargo artifacts. Cargo's
    target and compiler are explicit; no compiler wrapper is used. Other build
    settings and system/linker libraries are not claimed to be hermetic.
    """
    if type(jobs) is not int or not 1 <= jobs <= 16:
        raise ValueError("jobs must be an integer from 1 through 16")
    launcher = shutil.which("rustc")
    if not launcher:
        raise RuntimeError("rustc is unavailable")
    sysroot = Path(command([launcher, "--print", "sysroot"]).decode().strip())
    compiler, cargo = sysroot / "bin/rustc", sysroot / "bin/cargo"
    for tool in (compiler, cargo):
        if not tool.is_file():
            raise RuntimeError(f"active Rust sysroot lacks tool: {tool}")
    compiler = compiler.resolve()
    cargo = cargo.resolve()
    target_dir = destination / "rust-target"
    overrides = {"RUSTC": str(compiler), "RUSTC_WRAPPER": "", "RUSTC_WORKSPACE_WRAPPER": "",
                 "CARGO_BUILD_BUILD_DIR": str(target_dir)}
    env = dict(os.environ, **overrides)

    def toolchain():
        return {name: {"path": str(path), "sha256": digest(path.read_bytes()),
                       "verbose_version": command([str(path), "--version", "--verbose"], env=env).decode().strip()}
                for name, path in (("rustc", compiler), ("cargo", cargo))}

    before_tools = toolchain()
    host = re.search(r"^host: ([A-Za-z0-9_-]+)$", before_tools["rustc"]["verbose_version"], re.M)
    if not host:
        raise RuntimeError("rustc did not report an explicit host target")
    target = host.group(1)
    before_source = source_inputs(root, command)
    target_dir.mkdir(exist_ok=False)
    argv = ["nice", "-n", "19", str(cargo), "build", "--release", "--locked", "--offline", f"-j{jobs}",
            "--target", target, "--target-dir", str(target_dir), "--verbose", "--verbose"]
    started = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    log = command(argv, env=env)
    finished = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    after_tools = toolchain()
    after_source = source_inputs(root, command)
    if before_tools != after_tools:
        raise RuntimeError("Rust toolchain changed during build; no producer association issued")
    if before_source != after_source:
        raise RuntimeError("tracked source changed during build; no producer association issued")

    binaries, outputs = {}, {}
    for binary in ("bnav-extract", "bot-soak"):
        path = target_dir / target / "release" / binary
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"expected fresh host binary missing or not regular: {path}")
        data = path.read_bytes()
        binaries[binary] = data
        outputs[f"bin/{binary}"] = {"build_path": str(path), "sha256": digest(data), "bytes": len(data)}
    receipt = {
        "format": "banshee-rust-producer-v1",
        "scope": "observed fresh host Cargo invocation and output association; no historical producer or native adoption claim",
        "source_commit": commit, "source_tree": tree,
        "source_inputs_sha256": after_source,
        "source_inputs_stable": True,
        "working_directory": str(root), "argv": argv,
        "started_cst": started, "finished_cst": finished,
        "build_environment_overrides": overrides,
        "ambient_environment_recorded": False,
        "toolchain": after_tools, "toolchain_stable": True,
        "target": target, "profile": "release", "fresh_target_directory": str(target_dir),
        "build_log_sha256": digest(log), "outputs": outputs,
        "hermetic_or_reproducible_build_claimed": False,
        "system_linker_and_dynamic_libraries_pinned": False,
    }
    return log, binaries, receipt
