#!/usr/bin/env python3
"""Focused non-executing guards for retained harness reuse and owned crops."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("nav_check", Path(__file__).with_name("check_ffxi_nav.py"))
nav = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav)


class ReuseGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banshee-nav-reuse-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.driver = b"synthetic driver source; never compiled"
        self.profile = dict(nav.PROFILES["detail-boundary-5c73"])
        self.profile.update(source_sha256=nav.digest(b"wrapper"), tests_sha256=nav.digest(b"tests"))
        self.files = {
            "harness/src/detour_mset.rs": b"wrapper", "harness/src/detour_mset/tests.rs": b"tests",
            "harness/src/main.rs": nav.HARNESS.encode(), "harness/src/native_smoke.rs": self.driver,
            "harness/Cargo.toml": nav.cargo_manifest(True), "harness/Cargo.lock": b"synthetic lock",
            "harness/native/detour-sys/src/lib.rs": b"synthetic native source",
            "target/debug/ffxi-nav-compat": b"not an executable: wrapper fixture",
            "target/debug/ffxi-native-smoke": b"not an executable: native fixture",
        }
        for name, data in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.receipt = {
            "verdict": "PASS", "reference_profile": "detail-boundary-5c73",
            "reference_commit": self.profile["commit"], "reference_source_sha256": self.profile["source_sha256"],
            "reference_tests_sha256": self.profile["tests_sha256"], "owner_packet_sha256": self.profile["packet_sha256"],
            "harness_source_sha256": nav.digest(nav.HARNESS.encode()), "native_driver_sha256": nav.digest(self.driver),
            "cargo_lock_sha256": nav.digest(self.files["harness/Cargo.lock"]),
            "harness_binary_sha256": nav.digest(self.files["target/debug/ffxi-nav-compat"]),
            "native_harness_binary_sha256": nav.digest(self.files["target/debug/ffxi-native-smoke"]),
            "native_sources": {"git_tree": self.profile["native_tree"],
                               "files_sha256": {"src/lib.rs": nav.digest(self.files["harness/native/detour-sys/src/lib.rs"])}}
        }
        self.receipt_path = self.root / "result.json"
        self.receipt_path.write_text(json.dumps(self.receipt))
        # Only the test substitutes its synthetic receipt pin. Production has
        # no caller option to waive or replace the authentic retained pin.
        self.pin = patch.object(nav, "RETAINED_HARNESS_RECEIPT_SHA256", nav.digest(self.receipt_path.read_bytes()))
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def verify(self):
        return nav.verify_reuse(self.receipt_path, self.profile, self.driver)

    def test_verified_bytes_are_returned_without_execution_or_new_build_claim(self):
        with patch.object(nav.subprocess, "run", side_effect=AssertionError("must not execute")):
            info, binaries, inputs = self.verify()
        self.assertEqual(set(binaries), {"ffxi-nav-compat", "ffxi-native-smoke"})
        self.assertFalse(info["build_run_this_invocation"])
        self.assertFalse(info["owner_tests_run_this_invocation"])
        self.assertIn(str(self.receipt_path), inputs)

    def test_modified_receipt_cannot_authorize_replacement_binary(self):
        self.receipt["native_harness_binary_sha256"] = "0" * 64
        self.receipt_path.write_text(json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError, "receipt pin"):
            self.verify()

    def test_changed_binary_source_and_lock_each_refuse(self):
        for relative in ["target/debug/ffxi-native-smoke", "harness/src/detour_mset.rs", "harness/Cargo.lock"]:
            with self.subTest(relative=relative):
                path = self.root / relative
                path.write_bytes(self.files[relative] + b"changed")
                with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                    self.verify()
                path.write_bytes(self.files[relative])

    def test_changed_current_driver_requires_a_new_build(self):
        with self.assertRaisesRegex(ValueError, "driver identity"):
            nav.verify_reuse(self.receipt_path, self.profile, self.driver + b"changed")

    def test_symlink_to_matching_bytes_is_refused(self):
        path = self.root / "target/debug/ffxi-native-smoke"
        held = path.with_name("held-native-smoke")
        path.rename(held)
        path.symlink_to(held)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.verify()

    def test_retained_path_cannot_escape_receipt_tree(self):
        with self.assertRaisesRegex(ValueError, "artifact path"):
            nav.retained_file(self.root, "../outside")


class CropGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="banshee-nav-crop-test-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.backend, self.obj, self.provenance = [root / name for name in ("backend", "mesh.obj", "source.json")]
        for path in (self.backend, self.obj, self.provenance):
            path.write_bytes(b"synthetic metadata fixture; never executed")
        self.config = {"backend": str(self.backend)}
        self.tile = "1" * 64
        self.obj_sha = nav.digest(self.obj.read_bytes())
        self.receipt = {"exit_code": 0, "inputs": {str(self.obj): self.obj_sha, str(self.backend): nav.BACKEND_SHA256}}
        self.sidecar = {"format": "bnav-geometry-v1", "game": "FFXI",
            "coordinates": {"up_axis": "Y", "transform": "(x,-y,-z), applied once by owning exporter; winding aligned to transformed stored normals"},
            "provenance": {"artifacts": [{"path": str(self.provenance), "sha256": nav.digest(self.provenance.read_bytes())}]}}

    def check(self, receipt=None, sidecar=None, backend=None, expected=None):
        return nav.validate_native_crop(self.config, receipt or self.receipt, sidecar or self.sidecar,
                                        self.tile, self.obj, self.obj_sha, backend or nav.BACKEND_SHA256, expected or self.tile)

    def test_explicit_matching_crop_retains_concrete_provenance(self):
        self.assertEqual(self.check(), {str(self.provenance): nav.digest(self.provenance.read_bytes())})

    def test_different_native_tile_or_backend_is_refused(self):
        for kwargs in ({"expected": "2" * 64}, {"backend": "3" * 64}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "tile hash or retained"):
                self.check(**kwargs)

    def test_unrelated_or_failed_bake_cannot_prove_the_crop(self):
        for receipt in ({"exit_code": 1, "inputs": self.receipt["inputs"]},
                        {"exit_code": 0, "inputs": {str(self.obj): "0" * 64, str(self.backend): nav.BACKEND_SHA256}}):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                self.check(receipt=receipt)

    def test_altered_provenance_or_transform_is_refused(self):
        altered = copy.deepcopy(self.sidecar)
        altered["provenance"]["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "provenance artifact"):
            self.check(sidecar=altered)
        altered = copy.deepcopy(self.sidecar)
        altered["coordinates"]["transform"] = "identity; no transform applied"
        with self.assertRaisesRegex(ValueError, "transform applied exactly once"):
            self.check(sidecar=altered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
