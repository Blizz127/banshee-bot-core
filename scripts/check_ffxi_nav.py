#!/usr/bin/env python3
"""Exercise an explicitly selected pinned FFXI wrapper on recorded outputs.

Builds only an immutable snapshot of detour_mset.rs in an external Cargo project.
Optional --native-case consumes one pinned owned tile with the owner's exact
detour-sys library. No FFXI checkout/build target, asset reader or server is used.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile

SOURCE = "server/crates/forever-audit/src/detour_mset.rs"
TEST_SOURCE = "server/crates/forever-audit/src/detour_mset/tests.rs"
PROFILES = {
    "original-a13": {
        "commit": "a13dabcd550e0a777be5077804ba3d51683cfa19",
        "source_sha256": "5bf2638184ec007fde180a41f24646687572bb94185684056a7b39ec59c1fd5f",
        "tests_sha256": "a6fe406580023fc1ed084afd54209de1524877dba226123e4165a5f50fc5b0bd",
    },
    "detail-boundary-5c73": {
        "commit": "5c73a8751940ba767c7b86a50bb96b38b5d1e4f6",
        "source_sha256": "1cd9c8d9d540c704b84fd9f3c1d7c6006185fd96ea8e7f54cb3c2996456517ad",
        "tests_sha256": "52ac48f6be9b3796faeb60f57808b5aa0d55dde34e12a4dcaeb28942c17e84c2",
        "packet_sha256": "9f56d53b0053e59a87f1d75186e24d81a1e9fb2cdac2c8bb27cbcf1b7906876d",
        "native_tree": "f60ac5be2549c158730514f004218a168c76f907",
        "wrapper_test_count": 7,
    },
}
BACKEND_SHA256 = "d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c"
OWNED_TILE_SHA256 = "4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4"
EXCLUDED_NATIVE_TEST = "detour_mset::tests::synthetic_mset_loads_exactly_one_tile_and_queries_original_corridor"
MAX_BYTES = 64 * 1024 * 1024

HARNESS = r'''#![allow(dead_code)]
mod detour_mset;
use detour_mset::{wrap_raw32, Producer, Provenance};
use sha2::{Digest, Sha256};
use serde_json::{json, Value};
use std::{fs, io::Write, path::Path};

fn hash(bytes: &[u8]) -> [u8; 32] { Sha256::digest(bytes).into() }
fn hex(bytes: &[u8; 32]) -> String { bytes.iter().map(|b| format!("{b:02x}")).collect() }
fn unhex(s: &str) -> [u8; 32] {
    assert_eq!(s.len(), 64);
    std::array::from_fn(|i| u8::from_str_radix(&s[2*i..2*i+2], 16).unwrap())
}
fn create(path: &Path, bytes: &[u8]) {
    let mut out=fs::OpenOptions::new().write(true).create_new(true).open(path).unwrap();
    out.write_all(bytes).unwrap(); out.sync_all().unwrap();
}
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let plan: Value = serde_json::from_slice(&fs::read(&args[1]).unwrap()).unwrap();
    let output = Path::new(&args[2]);
    let mut outcomes = Vec::new();
    let mut failures = 0;
    for case in plan["cases"].as_array().unwrap() {
        let name=case["name"].as_str().unwrap();
        let raw=fs::read(case["path"].as_str().unwrap()).unwrap();
        let raw_sha=hash(&raw);
        assert_eq!(hex(&raw_sha), case["sha256"].as_str().unwrap());
        let mut declared_sha=raw_sha;
        if case["wrong_hash"].as_bool().unwrap_or(false) { declared_sha[0] ^= 1; }
        let producer=if case["mode"] == "pinned" {
            let evidence=if case["producer"].is_object() { &case["producer"] } else { &plan };
            Producer::BansheeAe73Raw32 {
                backend_sha256: unhex(evidence["backend_sha256"].as_str().unwrap()),
                build_receipt_sha256: unhex(evidence["build_receipt_sha256"].as_str().unwrap()),
                geometry_manifest_sha256: unhex(evidence["geometry_manifest_sha256"].as_str().unwrap()),
                obj_sha256: unhex(case["obj_sha256"].as_str().unwrap()),
            }
        } else {
            assert_eq!(case["mode"], "synthetic");
            Producer::Synthetic { description: format!("Actual native helper output from synthetic geometry: {name}; no game-coordinate or coverage assertion") }
        };
        let result=wrap_raw32(&raw, Provenance { producer, raw_sha256: declared_sha });
        let expected=case["expect"].as_str().unwrap();
        let mut outcome=json!({"name":name,"input_sha256":hex(&raw_sha),"expected":expected});
        match result {
            Ok(adapted) => {
                let preserved=adapted.mset.len()==raw.len()+48 && adapted.mset[48..]==raw;
                let header=adapted.mset[..12]==[0x54,0x45,0x53,0x4d,1,0,0,0,1,0,0,0];
                let q=adapted.checked_query_range([2.0,0.0,10.0],[2.0,4.0,2.0]);
                let bad_q=adapted.checked_query_range([2.0,0.0,10.0],[31.0,60.0,30.0]);
                let manifest=adapted.manifest.to_json();
                let limits=manifest["native_load_or_query_executed"]==false
                    && manifest["coverage_complete"]==false && manifest["agent_calibration_verified"]==false;
                let pass=expected=="accept" && preserved && header && q.is_ok() && bad_q.is_err() && limits;
                outcome["accepted"]=json!(true); outcome["pass"]=json!(pass);
                outcome["payload_unchanged"]=json!(preserved); outcome["mset_header_valid"]=json!(header);
                outcome["query_preflight"]=json!(format!("{q:?}"));
                outcome["outside_envelope_refusal"]=json!(format!("{bad_q:?}"));
                outcome["manifest"]=manifest;
                if pass { create(&output.join(format!("{name}.mset")), &adapted.mset); }
                if !pass { failures += 1; }
            }
            Err(error) => {
                let reason=error.to_string();
                let pass=expected=="reject" && reason.contains(case["reason_contains"].as_str().unwrap());
                outcome["accepted"]=json!(false); outcome["pass"]=json!(pass); outcome["reason"]=json!(reason);
                if !pass { failures += 1; }
            }
        }
        outcomes.push(outcome);
    }
    let result=json!({"verdict":if failures==0 {"PASS"} else {"FAIL"},"failures":failures,
        "cases":outcomes,"native_load_or_query_executed":false,"game_qa":"NOT_RUN",
        "scope":"Pinned FFXI pure-byte wrapper; source limitations retained separately; no native loader or game QA"});
    create(&output.join("wrapper-results.json"), serde_json::to_string_pretty(&result).unwrap().as_bytes());
    println!("{}", serde_json::to_string(&result).unwrap());
    if failures != 0 { std::process::exit(1); }
}
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_bytes(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError(f"expected ordinary file at most 64 MiB: {path}")
    return path.read_bytes()


def git_bytes(repo, commit, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"])


def check_packet(path, profile, original, tests):
    data = file_bytes(path)
    if digest(data) != profile["packet_sha256"]:
        raise ValueError("owner source/test packet hash mismatch")
    with tarfile.open(path, "r:gz") as archive:
        names = [m.name for m in archive.getmembers()]
        for member, expected in (("source/" + SOURCE, original), ("source/" + TEST_SOURCE, tests)):
            if names.count(member) != 1:
                raise ValueError(f"packet member missing or duplicated: {member}")
            info = archive.getmember(member)
            if not info.isfile() or info.size > MAX_BYTES or archive.extractfile(info).read() != expected:
                raise ValueError(f"packet source differs from pinned git object: {member}")
    return digest(data)


def snapshot_native(repo, profile, destination):
    prefix = "server/crates/detour-sys"
    tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse",
                                    f"{profile['commit']}:{prefix}"], text=True).strip()
    if tree != profile["native_tree"]:
        raise ValueError("owning native binding source tree differs from pin")
    files = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
                                     profile["commit"], "--", prefix], text=True).splitlines()
    hashes = {}
    for filename in files:
        relative = Path(filename).relative_to(prefix)
        if relative.parts[0] == "oracle":
            continue
        data = git_bytes(repo, profile["commit"], filename)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[str(relative)] = digest(data)
    return {"git_tree": tree, "files_sha256": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-profile", choices=PROFILES, required=True,
                        help="explicit historical or corrected wrapper source pin")
    parser.add_argument("--source-packet", type=Path,
                        help="owner source/test packet; required for detail-boundary-5c73")
    parser.add_argument("--native-case", help="accepted owned case to load/query using exact owning detour-sys")
    parser.add_argument("--reference-repo", type=Path, default=Path("/home/blizz/dev/ffxi-platform"))
    parser.add_argument("--single-dir", type=Path, required=True)
    parser.add_argument("--tiled-dir", type=Path, required=True)
    parser.add_argument("--native64-mmtile", type=Path, required=True)
    parser.add_argument("--backend-manifest", type=Path, required=True)
    parser.add_argument("--owned-case", type=Path, action="append", default=[],
                        help="JSON with name, raw_tile, raw_receipt, geometry_manifest, backend, backend_manifest, expect, and rejection reason_contains")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    profile = PROFILES[args.reference_profile]
    if args.reference_profile == "detail-boundary-5c73" and not args.source_packet:
        parser.error("corrected source requires its explicitly supplied pinned owner packet")
    if args.native_case and args.reference_profile != "detail-boundary-5c73":
        parser.error("owned native smoke requires the corrected owner source profile")
    if args.source_packet and "packet_sha256" not in profile:
        parser.error("the historical profile has no pinned source/test packet")
    repo = Path(__file__).resolve().parents[1]
    source_repo = args.reference_repo.resolve(strict=True)
    output = args.evidence.resolve()
    if output.is_relative_to(repo) or output.is_relative_to(source_repo):
        parser.error("evidence must be outside both source repositories")
    if output.exists():
        parser.error("choose a new evidence directory; earlier receipts are retained")
    original = git_bytes(source_repo, profile["commit"], SOURCE)
    tests = git_bytes(source_repo, profile["commit"], TEST_SOURCE)
    if digest(original) != profile["source_sha256"] or digest(tests) != profile["tests_sha256"]:
        parser.error("reference source hash does not match the audited git object")
    packet_sha = None
    if args.source_packet:
        try:
            packet_sha = check_packet(args.source_packet.resolve(strict=True), profile, original, tests)
        except (OSError, ValueError, tarfile.TarError) as error:
            parser.error(str(error))
    build_bytes = file_bytes(args.backend_manifest.resolve(strict=True))
    build_record = json.loads(build_bytes)
    if build_record["backend_sha256"] != BACKEND_SHA256:
        parser.error("pinned producer checks require the build0001 backend manifest")
    single = args.single_dir.resolve(strict=True)
    tiled = args.tiled_dir.resolve(strict=True)
    source_files = {str(args.backend_manifest.resolve()): digest(build_bytes)}
    if packet_sha:
        source_files[str(args.source_packet.resolve())] = packet_sha
    raw_inputs = {}
    objects = {}
    for name in ("floor", "wall", "disconnected"):
        path = single / f"{name}.navtile"
        raw_inputs[name] = file_bytes(path)
        source_files[str(path)] = digest(raw_inputs[name])
        obj = single / f"{name}.obj"
        objects[name] = digest(file_bytes(obj))
        source_files[str(obj)] = objects[name]
    for name in ("floor-0", "floor-1"):
        path = tiled / f"{name}.navtile"
        raw_inputs[name] = file_bytes(path)
        source_files[str(path)] = digest(raw_inputs[name])
    native64_path = args.native64_mmtile.resolve(strict=True)
    native64 = file_bytes(native64_path)
    source_files[str(native64_path)] = digest(native64)
    # The v20 profile was independently checked in nav-preflight. Strip only its
    # known wrapper; no 64-bit tile data or reference layout is rewritten.
    if len(native64) < 156 or struct.unpack_from("<III", native64) != (0x4D4D4150, 7, 20):
        parser.error("expected the explicit Acore v20 native fixture")
    if struct.unpack_from("<I", native64, 12)[0] != len(native64) - 56:
        parser.error("v20 fixture declared payload length differs")
    raw_inputs["native64"] = native64[56:]

    output.mkdir(parents=True)
    project = output / "harness"
    (project / "src").mkdir(parents=True)
    (output / "inputs").mkdir()
    (output / "outputs").mkdir()
    (project / "src/detour_mset.rs").write_bytes(original)
    (project / "src/main.rs").write_text(HARNESS)
    cargo_text = '[package]\nname="ffxi-nav-compat"\nversion="0.0.0"\nedition="2021"\npublish=false\n\n[dependencies]\nsha2="=0.10.9"\nserde_json="=1.0.154"\n'
    native_sources = None
    native_driver = None
    if args.native_case:
        native_sources = snapshot_native(source_repo, profile, project / "native/detour-sys")
        native_driver = Path(__file__).with_name("ffxi_native_driver.rs").read_bytes()
        (project / "src/native_smoke.rs").write_bytes(native_driver)
        (project / "src/detour_mset").mkdir()
        (project / "src/detour_mset/tests.rs").write_bytes(tests)
        cargo_text += ('detour-sys={path="native/detour-sys"}\n\n'
                       '[workspace]\nmembers=["native/detour-sys"]\nresolver="2"\n'
                       '[workspace.package]\nedition="2021"\npublish=false\n\n'
                       '[[bin]]\nname="ffxi-native-smoke"\npath="src/native_smoke.rs"\n')
    (project / "Cargo.toml").write_text(cargo_text)
    geometry_manifest = {"kind": "synthetic-fixture-source-manifest", "actual_game_geometry": False,
                         "source_files_sha256": source_files, "coordinate_calibration": "UNVERIFIED"}
    geometry_bytes = (json.dumps(geometry_manifest, indent=2) + "\n").encode()
    (output / "synthetic-geometry-manifest.json").write_bytes(geometry_bytes)
    cases = []
    for name, data in raw_inputs.items():
        (output / "inputs" / f"{name}.navtile").write_bytes(data)
    for name in ("floor", "wall", "disconnected"):
        for mode in ("synthetic", "pinned"):
            cases.append({"name": f"{name}-{mode}", "path": str(output / "inputs" / f"{name}.navtile"),
                          "sha256": digest(raw_inputs[name]), "obj_sha256": objects[name],
                          "mode": mode, "expect": "accept"})
    for name, reason in (("floor-0", "external/self/out-of-range polygon neighbor"), ("floor-1", "zero tile"), ("native64", "reference ABI")):
        cases.append({"name": f"refuse-{name}", "path": str(output / "inputs" / f"{name}.navtile"),
                      "sha256": digest(raw_inputs[name]), "mode": "synthetic", "expect": "reject", "reason_contains": reason})
    cases.append({"name": "refuse-wrong-hash", "path": str(output / "inputs/floor.navtile"),
                  "sha256": digest(raw_inputs["floor"]), "mode": "synthetic", "expect": "reject",
                  "reason_contains": "provenance hash mismatch", "wrong_hash": True})
    for config_path in args.owned_case:
        config_bytes = file_bytes(config_path.resolve(strict=True))
        config = json.loads(config_bytes)
        name = config["name"]
        if not name.isascii() or not name.replace("-", "").isalnum() or any(c["name"] == name for c in cases):
            parser.error("owned case name must be unique ASCII letters/digits/hyphens")
        source_files[str(config_path.resolve())] = digest(config_bytes)

        def record(field):
            path = Path(config[field]).resolve(strict=True)
            data = file_bytes(path)
            source_files[str(path)] = digest(data)
            return data

        raw = record("raw_tile")
        raw_receipt = json.loads(record("raw_receipt"))
        recorded_hashes = [raw_receipt[k] for k in ("single_tile_sha256", "tile_sha256") if k in raw_receipt]
        if not recorded_hashes or any(value != digest(raw) for value in recorded_hashes):
            parser.error("owned tile does not match its recorded bake")
        sidecar_bytes = record("geometry_manifest")
        sidecar = json.loads(sidecar_bytes)
        if sidecar["provenance"]["classification"] != "owner_asset" or sidecar["coverage"]["collision_complete"] is not False:
            parser.error("owned case requires explicit owner source and incomplete coverage")
        obj_path = Path(sidecar["geometry"]["path"]).resolve(strict=True)
        obj_sha = digest(file_bytes(obj_path))
        if obj_sha != sidecar["geometry"]["sha256"]:
            parser.error("owned OBJ differs from geometry manifest")
        source_files[str(obj_path)] = obj_sha
        backend_sha = digest(record("backend"))
        manifest_bytes = record("backend_manifest")
        if json.loads(manifest_bytes)["backend_sha256"] != backend_sha:
            parser.error("owned backend differs from build manifest")
        input_path = output / "inputs" / f"{name}.navtile"
        input_path.write_bytes(raw)
        cases.append({"name": name, "path": str(input_path), "sha256": digest(raw),
                      "obj_sha256": obj_sha, "mode": "pinned", "expect": config["expect"],
                      "reason_contains": config.get("reason_contains", ""),
                      "producer": {"backend_sha256": backend_sha,
                                   "build_receipt_sha256": digest(manifest_bytes),
                                   "geometry_manifest_sha256": digest(sidecar_bytes)}})
    if args.native_case:
        selected = [case for case in cases if case["name"] == args.native_case]
        if len(selected) != 1 or selected[0]["expect"] != "accept" or selected[0]["mode"] != "pinned":
            parser.error("native case must explicitly select one accepted owned case")
        if selected[0]["sha256"] != OWNED_TILE_SHA256 or selected[0]["producer"]["backend_sha256"] != BACKEND_SHA256:
            parser.error("native case must use the exact recorded owned tile and retained build0001 backend")
    plan = {"backend_sha256": BACKEND_SHA256, "build_receipt_sha256": digest(build_bytes),
            "geometry_manifest_sha256": digest(geometry_bytes), "cases": cases}
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    report = {"verdict": "RUNNING", "scope": __doc__, "reference_profile": args.reference_profile,
              "reference_commit": profile["commit"], "reference_source_sha256": profile["source_sha256"],
              "reference_tests_sha256": profile["tests_sha256"], "owner_packet_sha256": packet_sha,
              "reference_licence": "Private project; no explicit licence found in bounded prior audit",
              "harness_source_sha256": digest(HARNESS.encode()), "script_sha256": digest(Path(__file__).read_bytes()),
              "source_files_sha256": source_files, "commands": [], "native_load_or_query_executed": False,
              "native_sources": native_sources, "native_driver_sha256": digest(native_driver) if native_driver else None,
              "owned_native_load_or_query_executed": False,
              "excluded_owner_test": {"name": EXCLUDED_NATIVE_TEST,
                  "reason": "Owner test supplies capacity16 to native path APIs whose shim uses512; source retained unchanged, test not executed"} if args.native_case else None,
              "game_qa": "NOT_RUN", "started_cst": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).isoformat()}

    def save_report():
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(label, argv):
        log = output / f"{label}.log"
        command = ["nice", "-n", "19", *map(str, argv)]
        record = {"label": label, "argv": command, "exit_code": None}
        report["commands"].append(record)
        save_report()
        with log.open("xb") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, cwd=project)
        record.update({"exit_code": result.returncode, "log_sha256": digest(log.read_bytes())})
        save_report()
        if result.returncode:
            raise RuntimeError(f"{label} failed ({result.returncode}); see {log}")

    try:
        run("lock", ["cargo", "generate-lockfile", "--offline", "--manifest-path", project / "Cargo.toml"])
        run("build", ["cargo", "build", "--offline", "--locked", "-j2", "--manifest-path", project / "Cargo.toml", "--target-dir", output / "target"])
        run("compatibility", [output / "target/debug/ffxi-nav-compat", output / "plan.json", output / "outputs"])
        if args.native_case:
            run("wrapper-tests", ["cargo", "test", "--offline", "--locked", "-j2", "--manifest-path", project / "Cargo.toml",
                                  "--target-dir", output / "target", "-p", "ffxi-nav-compat", "--bin", "ffxi-nav-compat",
                                  "detour_mset::tests::", "--", "--test-threads=1", "--skip", EXCLUDED_NATIVE_TEST])
            if f"{profile['wrapper_test_count'] - 1} passed; 0 failed; 0 ignored" not in (output / "wrapper-tests.log").read_text():
                raise RuntimeError("wrapper test count differs from expected focused owner tests")
            report["native_load_or_query_executed"] = True  # Owner tests use synthetic native meshes.
            run("owned-native", [output / "target/debug/ffxi-native-smoke", output / "plan.json", args.native_case,
                                 output / "outputs", output / "owned-native-result.json"])
        for path, expected in source_files.items():
            if digest(file_bytes(Path(path))) != expected:
                raise RuntimeError(f"input changed during check: {path}")
        report["verdict"] = "PASS"
    except (OSError, ValueError, RuntimeError) as error:
        report["verdict"] = "FAIL"
        report["error"] = str(error)
    report["finished_cst"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6))).isoformat()
    report["cargo_lock_sha256"] = digest((project / "Cargo.lock").read_bytes()) if (project / "Cargo.lock").is_file() else None
    binary = output / "target/debug/ffxi-nav-compat"
    report["harness_binary_sha256"] = digest(binary.read_bytes()) if binary.is_file() else None
    native_binary = output / "target/debug/ffxi-native-smoke"
    report["native_harness_binary_sha256"] = digest(native_binary.read_bytes()) if native_binary.is_file() else None
    results = output / "outputs/wrapper-results.json"
    if results.is_file():
        report["results"] = json.loads(results.read_text())
        report["results_sha256"] = digest(results.read_bytes())
    native_result = output / "owned-native-result.json"
    if native_result.is_file():
        report["owned_native"] = json.loads(native_result.read_text())
        report["owned_native_result_sha256"] = digest(native_result.read_bytes())
        report["owned_native_load_or_query_executed"] = report["owned_native"]["native_load_or_query_executed"]
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "receipt": str(output / "result.json"), "error": report.get("error")}))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
