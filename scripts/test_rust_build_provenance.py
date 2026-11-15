"""Focused producer-association tests with synthetic files and fake commands.

No compiler, Cargo, native helper or game process is executed. Retain synthetic
fixtures beneath BANSHEE_TEST_EVIDENCE or the usual external evidence root;
an integrator may select the module with
RUST_BUILD_PROVENANCE_SCRIPT before merging this test-only change.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SCRIPT = Path(os.environ.get(
    "RUST_BUILD_PROVENANCE_SCRIPT", Path(__file__).resolve().parent / "rust_build_provenance.py"
)).resolve()
SPEC = importlib.util.spec_from_file_location("rust_build_provenance", SCRIPT)
PROVENANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROVENANCE)

HOST = "x86_64-unknown-linux-gnu"
COMMIT = "1" * 40
TREE = "2" * 40
BUILD_LOG = b"synthetic Cargo invocation completed; no process executed\n"
OUTPUTS = {
    "bnav-extract": b"synthetic extractor bytes, not an executable\n",
    "bot-soak": b"synthetic soak bytes, not an executable\n",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FakeBuild:
    def __init__(self, directory):
        self.directory = directory
        self.root = directory / "source"
        self.destination = directory / "candidate"
        self.sysroot = directory / "toolchain"
        self.launcher = directory / "launcher-rustc"
        self.compiler = self.sysroot / "bin/rustc"
        self.cargo = self.sysroot / "bin/cargo"
        self.root.mkdir()
        self.destination.mkdir()
        self.compiler.parent.mkdir(parents=True)
        self.launcher.write_bytes(b"synthetic launcher, never executed\n")
        self.compiler.write_bytes(b"synthetic rustc identity, never executed\n")
        self.cargo.write_bytes(b"synthetic cargo identity, never executed\n")
        self.sources = {
            "Cargo.toml": b'[workspace]\nmembers = []\n',
            "Cargo.lock": b'version = 4\n',
            "src/main.rs": b'fn main() {}\n',
        }
        for relative, data in self.sources.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.versions = {
            str(self.compiler): f"rustc synthetic\nhost: {HOST}\nrelease: synthetic\n".encode(),
            str(self.cargo): b"cargo synthetic\nrelease: synthetic\n",
        }
        self.calls = []
        self.build_calls = []
        self.on_build = None
        self.environment = {
            "PATH": "/synthetic-path-never-searched",
            "CARGO_BUILD_TARGET": "wasm32-unknown-unknown",
            "CARGO_TARGET_DIR": str(directory / "ambient-target"),
            "CARGO_BUILD_BUILD_DIR": str(directory / "ambient-intermediates"),
            "RUSTC": "/synthetic-ambient-rustc",
            "RUSTC_WRAPPER": "/synthetic-ambient-wrapper",
            "RUSTC_WORKSPACE_WRAPPER": "/synthetic-ambient-workspace-wrapper",
            "UNRELATED_TEST_ENVIRONMENT": "synthetic-value-that-must-not-enter-the-receipt",
        }

    def command(self, argv, env=None):
        argv = list(map(str, argv))
        # The environment is kept in memory for assertions, never in evidence.
        self.calls.append({"argv": argv, "env": None if env is None else dict(env)})
        if argv == [str(self.launcher), "--print", "sysroot"]:
            return (str(self.sysroot) + "\n").encode()
        if argv == ["git", "ls-files", "-z"]:
            return b"\0".join(path.encode() for path in sorted(self.sources)) + b"\0"
        if len(argv) == 3 and argv[1:] == ["--version", "--verbose"]:
            return self.versions[argv[0]]
        if argv[:5] == ["nice", "-n", "19", str(self.cargo), "build"]:
            self.build_calls.append({"argv": argv, "env": dict(env)})
            # Model Cargo's target precedence, so omitting either explicit flag
            # produces the wrong fixture location and fails the actual helper.
            target = argv[argv.index("--target") + 1] if "--target" in argv else env["CARGO_BUILD_TARGET"]
            target_dir = Path(argv[argv.index("--target-dir") + 1]) if "--target-dir" in argv else Path(env["CARGO_TARGET_DIR"])
            output = target_dir / target / "release"
            output.mkdir(parents=True)
            intermediates = Path(env["CARGO_BUILD_BUILD_DIR"])
            intermediates.mkdir(parents=True, exist_ok=True)
            (intermediates / "synthetic-intermediate").write_bytes(b"not a compiled object\n")
            for name, data in OUTPUTS.items():
                (output / name).write_bytes(data)
            if self.on_build:
                self.on_build()
            return BUILD_LOG
        raise AssertionError(f"unexpected command; no real execution is permitted: {argv!r}")

    def invoke(self, **kwargs):
        with mock.patch.object(PROVENANCE.shutil, "which", return_value=str(self.launcher)) as which:
            with mock.patch.dict(os.environ, self.environment, clear=True):
                result = PROVENANCE.build_rust_tools(
                    self.root, self.destination, COMMIT, TREE, self.command, **kwargs
                )
            which.assert_called_once_with("rustc")
        return result


class RustProducerAssociation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path(os.environ.get(
            "BANSHEE_TEST_EVIDENCE",
            Path.home() / ".local/share/banshee-bot-core/evidence/rust-producer-tests",
        )).expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        cls.evidence = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        print(f"synthetic_test_evidence={cls.evidence}", flush=True)
        (cls.evidence / "scope.json").write_text(json.dumps({
            "scope": "synthetic source/toolchain files and fake commands only",
            "module": str(SCRIPT), "module_sha256": sha(SCRIPT.read_bytes()),
            "real_compiler_or_cargo_executed": False,
            "native_or_game_actions": False,
        }, indent=2) + "\n")

    def fixture(self, label):
        directory = Path(tempfile.mkdtemp(prefix=label + "-", dir=self.evidence))
        return FakeBuild(directory)

    def test_success_associates_source_lock_tools_outputs_command_and_log(self):
        build = self.fixture("association")
        log, binaries, receipt = build.invoke()
        self.assertEqual(log, BUILD_LOG)
        self.assertEqual(binaries, OUTPUTS)
        self.assertEqual(receipt["format"], "banshee-rust-producer-v1")
        self.assertEqual(receipt["source_commit"], COMMIT)
        self.assertEqual(receipt["source_tree"], TREE)
        expected_source = {name: sha(data) for name, data in build.sources.items()}
        self.assertEqual(receipt["source_inputs_sha256"], expected_source)
        self.assertEqual(receipt["source_inputs_sha256"]["Cargo.lock"], sha(build.sources["Cargo.lock"]))
        self.assertIs(receipt["source_inputs_stable"], True)
        self.assertIs(receipt["toolchain_stable"], True)
        self.assertEqual(receipt["working_directory"], str(build.root))
        self.assertEqual(receipt["target"], HOST)
        self.assertEqual(receipt["profile"], "release")
        self.assertEqual(receipt["fresh_target_directory"], str(build.destination / "rust-target"))
        self.assertEqual(len(build.build_calls), 1)
        self.assertEqual(receipt["argv"], build.build_calls[0]["argv"])
        for required in ("--release", "--locked", "--offline"):
            self.assertIn(required, receipt["argv"])
        self.assertIn("-j2", receipt["argv"])
        self.assertEqual(receipt["build_log_sha256"], sha(BUILD_LOG))
        for name, path in (("rustc", build.compiler), ("cargo", build.cargo)):
            self.assertEqual(receipt["toolchain"][name], {
                "path": str(path.resolve()), "sha256": sha(path.read_bytes()),
                "verbose_version": build.versions[str(path)].decode().strip(),
            })
        for name, data in OUTPUTS.items():
            self.assertEqual(receipt["outputs"]["bin/" + name], {
                "build_path": str(build.destination / "rust-target" / HOST / "release" / name),
                "sha256": sha(data), "bytes": len(data),
            })
        self.assertIs(receipt["hermetic_or_reproducible_build_claimed"], False)
        self.assertIs(receipt["system_linker_and_dynamic_libraries_pinned"], False)
        (build.directory / "synthetic-association.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def test_explicit_target_and_compiler_override_ambient_values_without_environment_dump(self):
        build = self.fixture("overrides")
        _, _, receipt = build.invoke(jobs=1)
        invocation = build.build_calls[0]
        argv, env = invocation["argv"], invocation["env"]
        self.assertEqual(argv[argv.index("--target") + 1], HOST)
        self.assertEqual(argv[argv.index("--target-dir") + 1], str(build.destination / "rust-target"))
        self.assertEqual(env["CARGO_BUILD_TARGET"], "wasm32-unknown-unknown")
        self.assertFalse(Path(build.environment["CARGO_TARGET_DIR"]).exists())
        self.assertFalse(Path(build.environment["CARGO_BUILD_BUILD_DIR"]).exists())
        self.assertIn("-j1", argv)
        overrides = {
            "RUSTC": str(build.compiler.resolve()),
            "RUSTC_WRAPPER": "", "RUSTC_WORKSPACE_WRAPPER": "",
            "CARGO_BUILD_BUILD_DIR": str(build.destination / "rust-target"),
        }
        self.assertEqual(receipt["build_environment_overrides"], overrides)
        for key, value in overrides.items():
            self.assertEqual(env[key], value)
        self.assertEqual(argv[3], str(build.cargo.resolve()))
        self.assertEqual(env["UNRELATED_TEST_ENVIRONMENT"], build.environment["UNRELATED_TEST_ENVIRONMENT"])
        self.assertIs(receipt["ambient_environment_recorded"], False)
        encoded = json.dumps(receipt)
        self.assertNotIn("UNRELATED_TEST_ENVIRONMENT", encoded)
        self.assertNotIn(build.environment["UNRELATED_TEST_ENVIRONMENT"], encoded)

    def test_changed_tracked_source_or_lock_refuses_association(self):
        for relative in ("src/main.rs", "Cargo.lock"):
            with self.subTest(relative=relative):
                build = self.fixture("source-change")
                path = build.root / relative
                build.on_build = lambda: path.write_bytes(path.read_bytes() + b"changed\n")
                with self.assertRaisesRegex(RuntimeError, "tracked source changed during build"):
                    build.invoke()
                self.assertEqual(len(build.build_calls), 1)

    def test_changed_tool_bytes_or_verbose_identity_refuses_association(self):
        for change in ("rustc-bytes", "cargo-bytes", "verbose-version"):
            with self.subTest(change=change):
                build = self.fixture("tool-change")
                if change == "verbose-version":
                    def mutate_version():
                        build.versions[str(build.compiler)] += b"identity changed\n"
                    build.on_build = mutate_version
                else:
                    tool = build.compiler if change == "rustc-bytes" else build.cargo
                    build.on_build = lambda: tool.write_bytes(tool.read_bytes() + b"changed\n")
                with self.assertRaisesRegex(RuntimeError, "Rust toolchain changed during build"):
                    build.invoke()
                self.assertEqual(len(build.build_calls), 1)

    def test_preexisting_target_refuses_reuse_and_preserves_existing_data(self):
        build = self.fixture("target-exists")
        target = build.destination / "rust-target"
        target.mkdir()
        sentinel = target / "previous-artifact"
        original = b"retained synthetic artifact\n"
        sentinel.write_bytes(original)
        with self.assertRaises(FileExistsError):
            build.invoke()
        self.assertEqual(build.build_calls, [])
        self.assertEqual(sentinel.read_bytes(), original)
        self.assertEqual(list(target.iterdir()), [sentinel])

    def test_invalid_job_limits_are_refused_before_tools_or_build_directories(self):
        for jobs in (True, False, 0, -1, 17, 1.0, "1", None):
            with self.subTest(jobs=jobs):
                build = self.fixture("invalid-jobs")
                with self.assertRaisesRegex(ValueError, "jobs must be an integer"):
                    build.invoke(jobs=jobs)
                self.assertEqual(build.calls, [])
                self.assertFalse((build.destination / "rust-target").exists())


if __name__ == "__main__":
    unittest.main()
