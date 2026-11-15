#!/usr/bin/env python3
"""Compare only pinned FFXI role-election functions with the shared pure kernel.

Uses direct rustc builds of the core rlib and an original bounded driver. No
Cargo command, native server build, World/setter/state/epoch or P0 test is run.
All generated files belong to a fresh external evidence directory.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

# Reuse only fingerprint helpers; importing must not create repository outputs.
sys.dont_write_bytecode = True
from check_ffxi_compat import core_identity, git_info


PROFILE = "ffxi-role-election-f7c9662"
SOURCE_COMMIT = "f7c9662fc5bcfc3f37ce00db82e1fc2c00ccee74"
SOURCE_SHA256 = "63c7a2001f063d9620e1719928433bd98f887fec296f33ff51b46d8bea370ed5"
START = b"fn tank_priority(job: u8) -> Option<u8> {"
END = b"\n#[cfg(test)]"
REFERENCE_PREFIX = b"""// Original minimal data shim; no native World or state implementation.
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role { Tank, Healer, Dps, Puller }

#[derive(Clone, Copy, Debug)]
struct OwnerBinding { owner: u32 }

#[derive(Clone, Copy, Debug)]
struct Assignment {
    binding: OwnerBinding,
    job: Option<u8>,
    manual: Option<Role>,
    role: Option<Role>,
}

#[derive(Clone, Copy, Debug)]
pub struct Input {
    pub actor: u32,
    pub owner: u32,
    pub job: Option<u8>,
    pub manual: Option<Role>,
}

// Byte-exact pinned native functions follow.
"""
REFERENCE_SUFFIX = b"""
// Original projection wrapper. This does not authenticate or mutate bindings.
pub fn run(input: &[Input]) -> BTreeMap<u32, Option<Role>> {
    let mut assignments: BTreeMap<u32, Assignment> = input.iter().map(|row| {
        (row.actor, Assignment {
            binding: OwnerBinding { owner: row.owner },
            job: row.job,
            manual: row.manual,
            role: None,
        })
    }).collect();
    elect(&mut assignments);
    assignments.into_iter().map(|(actor, row)| (actor, row.role)).collect()
}
"""


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ordinary(path):
    need(not path.is_symlink() and path.is_file(), f"expected ordinary file: {path}")
    return path.read_bytes()


def extract(source):
    data = ordinary(source)
    need(sha(data) == SOURCE_SHA256, "unsupported native source SHA-256; no compiler was invoked")
    need(data.count(START) == 1, "expected one pinned election start marker")
    start = data.index(START)
    stop = data.index(END, start)
    fragment = data[start:stop]
    need(fragment.endswith(b"}\n"), "unexpected pinned election end boundary")
    return data, fragment, start, stop


def new_evidence(path, core):
    path = path.expanduser().absolute()
    need(not path.exists() and not path.is_symlink(), "evidence directory already exists")
    parent = path.parent.resolve(strict=True)
    need(parent != core and core not in parent.parents, "evidence must be outside the core workspace")
    for ancestor in (parent, *parent.parents):
        need(not (ancestor / ".git").exists(), "evidence must be outside git worktrees")
    return parent / path.name


def write_new(path, data):
    with path.open("xb") as output:
        output.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="exact pinned bot_roles.rs snapshot")
    parser.add_argument("--core", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--evidence", type=Path, required=True, help="fresh external directory; parent exists")
    args = parser.parse_args()
    source = args.source.expanduser().absolute()
    checker = Path(__file__).resolve()
    driver = checker.with_name("ffxi_role_election_compat.rs")
    helper = checker.with_name("check_ffxi_compat.py")
    try:
        core = args.core.expanduser().resolve(strict=True)
        # An unsupported pin fails before creating evidence or invoking rustc.
        native_bytes, fragment, start, stop = extract(source)
        core_before = core_identity(core)
        inputs = {str(path): ordinary(path) for path in (source, checker, driver, helper)}
        need(inputs[str(source)] == native_bytes, "native source changed during initial fingerprinting")
        evidence = new_evidence(args.evidence, core)
        launcher = shutil.which("rustc")
        need(launcher is not None, "rustc is unavailable")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    evidence.mkdir(mode=0o700, exist_ok=False)
    reference = REFERENCE_PREFIX + fragment + REFERENCE_SUFFIX
    write_new(evidence / "reference-functions.rs", fragment)
    write_new(evidence / "reference-prefix.rs", REFERENCE_PREFIX)
    write_new(evidence / "reference-suffix.rs", REFERENCE_SUFFIX)
    write_new(evidence / "reference.rs", reference)
    write_new(evidence / "ffxi_role_election_compat.rs", inputs[str(driver)])
    report = {
        "status": "RUNNING",
        "profile": PROFILE,
        "started_cst": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
        "scope": "Pure role election only: native job/manual projection versus generic role preferences.",
        "limitations": ["Bounded deterministic cases are not a general equivalence proof.",
                        "World, role setters/storage, authority, binding mutations and control epochs are excluded.",
                        "The source pin identifies a snapshot; native runtime adoption is not established.",
                        "No native server build, P0, Game QA or deployment was performed."],
        "source": str(source), "source_commit": SOURCE_COMMIT,
        "source_sha256": sha(native_bytes),
        "fragment": {"source_start_byte": start, "source_end_byte_exclusive": stop,
                     "bytes": len(fragment), "sha256": sha(fragment),
                     "path": str(evidence / "reference-functions.rs")},
        "shim": {"prefix_bytes": len(REFERENCE_PREFIX), "prefix_sha256": sha(REFERENCE_PREFIX),
                 "suffix_bytes": len(REFERENCE_SUFFIX), "suffix_sha256": sha(REFERENCE_SUFFIX)},
        "reference_sha256": sha(reference),
        "core": str(core), "core_git": git_info(core), "core_files_before": core_before,
        "input_files_before": {path: sha(data) for path, data in inputs.items()},
        "checker_sha256": sha(inputs[str(checker)]), "driver_sha256": sha(inputs[str(driver)]),
        "helper_sha256": sha(inputs[str(helper)]),
        "reference_environment": {"FFXI_ROLE_ELECTION_REFERENCE": str(evidence / "reference.rs")},
        "commands": [],
        "game_qa": "NOT_RUN", "native_ffxi_p0": "NOT_RUN", "deployment": "NOT_PERFORMED",
    }

    def run(label, argv):
        log = evidence / f"{label}.log"
        command = ["nice", "-n", "19", *map(str, argv)]
        record = {"label": label, "argv": command, "cwd": str(evidence), "log": str(log)}
        report["commands"].append(record)
        with log.open("xb") as output:
            result = subprocess.run(command, cwd=evidence, stdin=subprocess.DEVNULL,
                                    stdout=output, stderr=subprocess.STDOUT,
                                    env={**os.environ, **report["reference_environment"]})
        record["exit_code"] = result.returncode
        data = ordinary(log)
        record["log_sha256"] = sha(data)
        need(result.returncode == 0, f"{label} failed with exit {result.returncode}; see {log}")
        return data

    compiler = None
    try:
        sysroot = run("rustc-sysroot", [launcher, "--print", "sysroot"]).decode().strip()
        compiler = (Path(sysroot) / "bin/rustc").resolve(strict=True)
        compiler_hash = sha(ordinary(compiler))
        version = run("rustc-version", [compiler, "--version", "--verbose"]).decode()
        report["compiler"] = {"launcher": launcher, "path": str(compiler), "sha256": compiler_hash,
                              "version_verbose": version, "sysroot": sysroot}
        rlib = evidence / "libbanshee_bot_core.rlib"
        run("compile-core", [compiler, "--edition=2021", "--crate-name", "banshee_bot_core",
                             "--crate-type", "rlib", "-C", "codegen-units=1",
                             core / "crates/banshee-bot-core/src/lib.rs", "-o", rlib])
        binary = evidence / "ffxi-role-election-compat"
        run("compile-driver", [compiler, "--edition=2021", "--crate-name", "ffxi_role_election_compat",
                               "-C", "codegen-units=1", evidence / "ffxi_role_election_compat.rs",
                               "--extern", f"banshee_bot_core={rlib}", "-o", binary])
        report["differential"] = json.loads(run("role-election-differential", [binary]))
        need(report["differential"].get("status") == "PASS", "driver did not report PASS")
        report["status"] = "PASS"
    except (OSError, ValueError) as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
    finally:
        if report["status"] == "RUNNING":
            report["status"] = "INTERRUPTED"
        errors = []
        try:
            report["input_files_after"] = {path: sha(ordinary(Path(path))) for path in inputs}
            report["core_files_after"] = core_identity(core)
            if report["input_files_after"] != report["input_files_before"]:
                errors.append("source/checker/driver/helper changed during the run")
            if report["core_files_after"] != core_before:
                errors.append("core inputs changed during the run")
            if compiler is not None and "compiler" in report:
                report["compiler_sha256_after"] = sha(ordinary(compiler))
                if report["compiler_sha256_after"] != report["compiler"]["sha256"]:
                    errors.append("compiler changed during the run")
        except (OSError, ValueError) as error:
            errors.append(str(error))
        if errors:
            report["status"] = "FAIL"
            report["stability_errors"] = errors
        report["finished_cst"] = datetime.now(ZoneInfo("America/Chicago")).isoformat()
        report["artifacts_sha256"] = {path.name: sha(ordinary(path))
                                     for path in sorted(evidence.iterdir()) if path.is_file()}
        write_new(evidence / "result.json", (json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"status": report["status"], "profile": PROFILE,
                      "receipt": str(evidence / "result.json"),
                      "differential": report.get("differential"), "error": report.get("error")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
