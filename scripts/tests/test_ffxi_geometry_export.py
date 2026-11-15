"""Focused integrity tests; synthetic retained builds are never executed."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "export_ffxi_geometry.py"
SPEC = importlib.util.spec_from_file_location("ffxi_geometry_export", SCRIPT)
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ReuseIntegrity(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="bnav-ffxi-reuse-test-"))
        self.driver = b"synthetic original driver; never compiled"
        self.licence = b"synthetic MIT fixture; not an upstream licence assertion"
        self.binary = b"synthetic executable bytes; never executed"
        self.source_data = b"synthetic external reader"
        self.lock = b"synthetic retained reduced lock"
        self.expected = {"revision": EXPORT.SOURCE_REVISION, "archive_sha256": "a" * 64, "files": [
            {"path": "server/Cargo.lock", "bytes": 16, "sha256": "b" * 64},
            {"path": "server/crates/forever-audit/src/vana.rs", "bytes": len(self.source_data), "sha256": EXPORT.sha(self.source_data)},
        ]}
        source = copy.deepcopy(self.expected)
        source["reader_upstream"] = {"revision": EXPORT.UPSTREAM_REVISION, "licence": "MIT", "licence_sha256": EXPORT.sha(self.licence)}
        self.put("source-identity.json", json.dumps(source).encode())
        self.build = {"status": "VERIFIED", "source_revision": EXPORT.SOURCE_REVISION,
            "offline": True, "external_source_edited": False,
            "original_driver_sha256": EXPORT.sha(self.driver), "original_source_lock_sha256": "b" * 64,
            "locked_resolution_sha256": EXPORT.sha(self.lock),
            "binary": str(self.root / "cargo-target/debug/bnav-ffxi-export-driver"), "binary_sha256": EXPORT.sha(self.binary)}
        self.put("build-manifest.json", json.dumps(self.build).encode())
        self.put("external-source/server/Cargo.lock", self.lock)
        self.put("external-source/server/crates/forever-audit/src/vana.rs", self.source_data)
        self.put("external-source/server/crates/bnav-ffxi-export-driver/src/main.rs", self.driver)
        self.put("FOREVER-CLIENT-MIT-LICENSE.txt", self.licence)
        self.put("cargo-target/debug/bnav-ffxi-export-driver", self.binary)

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def verify(self):
        return EXPORT.verify_retained_build(self.root, self.expected, self.driver, self.licence)

    def test_valid_retained_bytes_and_source_reference(self):
        binary, record = self.verify()
        self.assertEqual(binary, self.binary)
        self.assertFalse(record["source_snapshots_copied"])
        self.assertEqual(record["retained_build_manifest"]["sha256"], EXPORT.sha((self.root / "build-manifest.json").read_bytes()))

    def test_changed_binary_refused(self):
        self.put("cargo-target/debug/bnav-ffxi-export-driver", self.binary + b"changed")
        with self.assertRaisesRegex(ValueError, "executable digest"):
            self.verify()

    def test_changed_staged_driver_refused(self):
        self.put("external-source/server/crates/bnav-ffxi-export-driver/src/main.rs", self.driver + b"changed")
        with self.assertRaisesRegex(ValueError, "staged driver"):
            self.verify()

    def test_current_driver_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, "current original driver"):
            EXPORT.verify_retained_build(self.root, self.expected, self.driver + b"new version", self.licence)

    def test_changed_external_source_refused(self):
        self.put("external-source/server/crates/forever-audit/src/vana.rs", b"changed")
        with self.assertRaisesRegex(ValueError, "staged source"):
            self.verify()

    def test_missing_source_manifest_entry_refused(self):
        source = json.loads((self.root / "source-identity.json").read_text())
        source["files"].pop()
        self.put("source-identity.json", json.dumps(source).encode())
        with self.assertRaisesRegex(ValueError, "pinned objects: files"):
            self.verify()

    def test_changed_lock_refused(self):
        self.put("external-source/server/Cargo.lock", b"changed")
        with self.assertRaisesRegex(ValueError, "staged source or lock"):
            self.verify()

    def test_changed_revision_refused(self):
        self.build["source_revision"] = "0" * 40
        self.put("build-manifest.json", json.dumps(self.build).encode())
        with self.assertRaisesRegex(ValueError, "pinned source"):
            self.verify()


class ExplicitSelection(unittest.TestCase):
    def test_source_backed_paths_preserved(self):
        for value in ("ROM/0/121.DAT", "ROM/1/31.DAT"):
            self.assertEqual(EXPORT.asset_relative(value), value)

    def test_path_escape_or_normalization_refused(self):
        for value in ("../ROM/0/121.DAT", "/ROM/0/121.DAT", "ROM//0/121.DAT", "ROM/./0/121.DAT", "ROM\\0\\121.DAT", "ROM/0/121", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                EXPORT.asset_relative(value)


if __name__ == "__main__":
    unittest.main()
