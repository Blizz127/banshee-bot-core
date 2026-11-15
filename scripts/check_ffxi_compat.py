#!/usr/bin/env python3
"""Compare original core contracts with a pinned, read-only FFXI source snapshot.

Example:
  python3 scripts/check_ffxi_compat.py --source /path/to/xi-map/src/fb \
      --evidence ~/.local/share/banshee-bot-core/evidence/compat-build-0001

Evidence must be a NEW directory outside both repositories. This is an offline
pure-contract check, not native adapter/P0, server startup, or game QA.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


PINS = {
    "control.rs": "6db0a98b3b14ebaff78354192400b2d92591cfa7fef50c39617c2eb16020835e",
    "command.rs": "34480a234e86b7a28731ebd56d1135bd42771cfba513a8f1bf81ef81ce2939be",
    "orders.rs": "b236c09b5c9f88b102560106ccfe4de3bf979d8d045c31fdf4157ad8c10db469",
    "authority.rs": "cfaca0c0e4019ddbdeecdcdb47896d3ea105fadf7704efaa0d7e1bb6a4e8e46b",
    "selection.rs": "840f9dd8f3261d5ef014909fe55a88451ae16b14929ab2b269d1bde926c7ffc9",
}
PINNED_CANDIDATE = "36b90715b29728ecbccd2fee95493bbc7c14db29"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_sources(source):
    files = {}
    for name, expected in PINS.items():
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"reference must be an ordinary file: {path}")
        data = path.read_bytes()
        actual = sha(data)
        if actual != expected:
            raise ValueError(f"reference hash mismatch: {name}: {actual}, expected {expected}")
        files[name] = data
    return files


def core_identity(core):
    paths = [core / "Cargo.toml", core / "Cargo.lock"]
    crate = core / "crates/banshee-bot-core"
    paths += [crate / "Cargo.toml", *sorted((crate / "src").rglob("*.rs"))]
    if not (crate / "src/lib.rs").is_file():
        raise ValueError(f"--core must name the workspace root: {core}")
    result = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"core source must be an ordinary file: {path}")
        result[str(path.relative_to(core))] = sha(path.read_bytes())
    return result


def git_info(root):
    def query(*args):
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else None
    return {"root": query("rev-parse", "--show-toplevel"),
            "head": query("rev-parse", "HEAD"),
            "tracked_changes": query("diff", "--name-only", "HEAD")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="explicit native fb directory")
    parser.add_argument("--core", type=Path, default=Path(__file__).resolve().parents[1],
                        help="core workspace root (default: script repository)")
    parser.add_argument("--evidence", required=True, type=Path, help="fresh external evidence directory")
    args = parser.parse_args()
    source, core, evidence = (p.expanduser().resolve() for p in (args.source, args.core, args.evidence))
    source_git = git_info(source)
    forbidden = [source, core]
    if source_git["root"]:
        forbidden.append(Path(source_git["root"]))
    if any(evidence == root or root in evidence.parents for root in forbidden):
        parser.error("evidence must be outside reference and core repositories")
    if evidence.exists():
        parser.error("evidence directory already exists; choose a fresh path to preserve previous receipts")
    # Validate everything before making any evidence artifact or invoking a compiler.
    try:
        references = read_sources(source)
        core_before = core_identity(core)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    evidence.mkdir(parents=True)
    reference_dir = evidence / "reference"
    reference_dir.mkdir()
    for name, data in references.items():
        (reference_dir / name).write_bytes(data)
    (reference_dir / "mod.rs").write_text(
        "#![allow(dead_code)]\n" + "".join(f"pub mod {Path(name).stem};\n" for name in PINS),
        encoding="utf-8",
    )
    harness = Path(__file__).with_name("ffxi_compat.rs").read_bytes()
    (evidence / "ffxi_compat.rs").write_bytes(harness)
    orders_harness = Path(__file__).with_name("ffxi_orders_compat.rs").read_bytes()
    (evidence / "ffxi_orders_compat.rs").write_bytes(orders_harness)
    report = {
        "status": "RUNNING",
        "started_cst": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).isoformat(),
        "scope": "Offline pure grammar, cancellation, authority, selection and order planning contracts; no native adapter/P0 or Game QA claim.",
        "source": str(source), "source_git": source_git,
        "reference_candidate": PINNED_CANDIDATE, "reference_sha256": PINS,
        "core": str(core), "core_git": git_info(core), "core_files_before": core_before,
        "harness_sha256": sha(harness), "script_sha256": sha(Path(__file__).read_bytes()),
        "orders_harness_sha256": sha(orders_harness),
        "commands": [],
        "limitations": ["Finite deterministic corpus is not exhaustive proof.",
                        "Reference runtime deployment identity is not verified.",
                        "Overflow is checked by focused private-state tests, not seeded public traces."]
    }

    def save():
        (evidence / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def run(label, command):
        log = evidence / f"{label}.log"
        full_command = ["nice", "-n", "19", *map(str, command)]
        record = {"label": label, "argv": full_command, "log": log.name}
        report["commands"].append(record)
        save()
        with log.open("xb") as output:
            result = subprocess.run(full_command, cwd=core, stdout=output, stderr=subprocess.STDOUT,
                                    env={**os.environ, "CARGO_TERM_COLOR": "never"})
        record["exit_code"] = result.returncode
        record["log_sha256"] = sha(log.read_bytes())
        save()
        if result.returncode:
            raise RuntimeError(f"{label} failed ({result.returncode}); see {log}")
        return log

    try:
        save()
        run("rustc-version", ["rustc", "--version", "--verbose"])
        run("cargo-version", ["cargo", "--version"])
        target = evidence / "target"
        cargo = ["cargo", "--offline"]
        common = ["--manifest-path", core / "Cargo.toml", "--locked", "-j2",
                  "--target-dir", target, "-p", "banshee-bot-core"]
        run("core-build", [*cargo, "build", *common])
        rlib = target / "debug/libbanshee_bot_core.rlib"
        if not rlib.is_file():
            raise RuntimeError(f"expected library missing: {rlib}")
        report["rlib_sha256"] = sha(rlib.read_bytes())
        run("compile-differential", ["rustc", "--edition=2021", evidence / "ffxi_compat.rs",
                                     "--extern", f"banshee_bot_core={rlib}",
                                     "-L", f"dependency={target / 'debug/deps'}",
                                     "-o", evidence / "ffxi-compat"])
        differential_log = run("differential", [evidence / "ffxi-compat"])
        report["differential"] = json.loads(differential_log.read_text())
        run("compile-orders-differential", ["rustc", "--edition=2021", evidence / "ffxi_orders_compat.rs",
                                            "--extern", f"banshee_bot_core={rlib}",
                                            "-L", f"dependency={target / 'debug/deps'}",
                                            "-o", evidence / "ffxi-orders-compat"])
        orders_log = run("orders-differential", [evidence / "ffxi-orders-compat"])
        report["orders_differential"] = json.loads(orders_log.read_text())
        for module in ("control", "command"):
            binary = evidence / f"reference-{module}-tests"
            run(f"compile-reference-{module}", ["rustc", "--edition=2021", "--test",
                                                reference_dir / f"{module}.rs", "-o", binary])
            log = run(f"reference-{module}-tests", [binary, "--test-threads=1"])
            expected_count = 6 if module == "control" else 5
            if f"{expected_count} passed; 0 failed; 0 ignored" not in log.read_text():
                raise RuntimeError(f"reference {module} did not execute all {expected_count} expected tests")
        run("core-overflow-test", [*cargo, "test", *common,
                                   "sched::control::tests::overflow_preflight_does_not_mutate_and_transition_permanently_closes",
                                   "--", "--exact", "--test-threads=1"])
        if "1 passed; 0 failed" not in (evidence / "core-overflow-test.log").read_text():
            raise RuntimeError("core overflow filter did not execute its one expected test")
        read_sources(source)
        report["core_files_after"] = core_identity(core)
        if report["core_files_after"] != core_before:
            raise RuntimeError("core source changed during verification; this receipt cannot establish a stable candidate")
        report["status"] = "PASS"
    except (OSError, ValueError, RuntimeError) as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
    finally:
        report["finished_cst"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).isoformat()
        report["artifacts_sha256"] = {str(p.relative_to(evidence)): sha(p.read_bytes())
                                     for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "result.json"}
        save()
    print(json.dumps({"status": report["status"], "evidence": str(evidence / "result.json"),
                      "differential": report.get("differential"),
                      "orders_differential": report.get("orders_differential"), "error": report.get("error")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
