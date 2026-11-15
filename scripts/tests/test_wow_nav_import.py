"""Focused WoW import checks using retained, synthetic structural fixtures.

These fixtures exercise format and receipt validation only. They are not a
navigable mesh and must never be passed to native Detour path queries.
"""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest


SCRIPT = Path(os.environ.get(
    "BNAV_WOW_IMPORT_SCRIPT", Path(__file__).resolve().parents[1] / "import_wow_nav.py"
))
sys.path.insert(0, str(SCRIPT.resolve().parent))
SPEC = importlib.util.spec_from_file_location("wow_nav_import", SCRIPT)
nav = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nav)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def map_bytes(bits=64):
    # Nonzero origin makes accidental placement relative to world zero visible.
    return struct.pack("<5fII", 10.0, -2.0, -30.0, 20.0, 20.0, 16,
                       0x80000000 if bits == 64 else 32768)


def wrapped_tile(bits=64, x=2, z=1, flags=0x41, area=3):
    link_size = 16 if bits == 64 else 12
    data = bytearray(100 + 36 + 32 + link_size + 12 + 4)
    struct.pack_into("<IIiii", data, 0, 0x444E4156, 7, x, z, 0)
    struct.pack_into("<9i", data, 24, 1, 3, 1, 1, 0, 1, 0, 0, 1)
    struct.pack_into("<3f", data, 60, 2.0, 0.6, 0.9)
    low_x, low_z = 10.0 + x * 20.0, -30.0 + z * 20.0
    struct.pack_into("<3f", data, 72, low_x, -2.0, low_z)
    struct.pack_into("<3f", data, 84, low_x + 20.0, 4.0, low_z + 20.0)
    struct.pack_into("<f", data, 96, 1.0)
    struct.pack_into("<9f", data, 100, low_x, 0.0, low_z,
                     low_x + 10.0, 0.0, low_z, low_x, 0.0, low_z + 10.0)
    struct.pack_into("<I6H6HHBB", data, 136, 0xFFFFFFFF, 0, 1, 2, 0, 0, 0,
                     0, 0, 0, 0, 0, 0, flags, 3, area)
    struct.pack_into("<IIBBxx", data, 168 + link_size, 0, 0, 0, 1)
    data[-4:] = bytes((0, 1, 2, 0))
    return struct.pack("<5I", 0x4D4D4150, 7, 8, len(data), 1) + data


class WowImportIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path.home() / ".local/share/banshee-bot-core/evidence/wow-import-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.evidence = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        print(f"synthetic_test_evidence={cls.evidence}", flush=True)

    def directory(self, label):
        return Path(tempfile.mkdtemp(prefix=label + "-", dir=self.evidence))

    def write_json(self, path, obj):
        path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")

    def file_record(self, name, data):
        return {"path": str(name), "bytes": len(data), "sha256": digest(data)}

    def selection(self, label, tile_x=(2, 3)):
        root = self.directory(label)
        for name in ("source", "tiles", "receipts"):
            (root / name).mkdir()
        profile = "cmangos-v8-ref64"
        tools = {name: self.file_record(f"/synthetic/{name}", name.encode())
                 for name in ("extractor", "backend")}
        data = map_bytes()
        (root / "map.mmap").write_bytes(data)
        source_map = self.file_record("/synthetic/input/map.mmap", data)
        map_receipt = {"argv": [tools["extractor"]["path"], "inspect-mmap", profile,
                                 str(root / "map.mmap")], "exit_code": 0}
        self.write_json(root / "receipts/map.json", map_receipt)
        map_record = {"source": source_map, "retained": self.file_record("map.mmap", data),
                      "parameters": nav.inspect_map(data, profile),
                      "receipt": self.file_record("receipts/map.json", (root / "receipts/map.json").read_bytes())}
        tiles = []
        for index, x in enumerate(tile_x):
            data = wrapped_tile(x=x)
            inspection, payload = nav.inspect_wrapper(data, profile, map_record["parameters"])
            source_name = f"source/{index:03}.mmtile"
            raw_name = f"tiles/{index:03}.navtile"
            receipt_name = f"receipts/{index:03}.json"
            (root / source_name).write_bytes(data)
            (root / raw_name).write_bytes(payload)
            receipt = {"argv": [tools["extractor"]["path"], "extract-mmtile", profile,
                                 str(root / source_name), str(root / raw_name)], "exit_code": 0}
            self.write_json(root / receipt_name, receipt)
            tiles.append({"source": self.file_record(f"/synthetic/input/noncoordinate-{index}.mmtile", data),
                          "status": "imported", "retained": self.file_record(source_name, data),
                          "raw": self.file_record(raw_name, payload), "inspection": inspection,
                          "receipt": self.file_record(receipt_name, (root / receipt_name).read_bytes())})
        request = {"format": "bnav-wow-request-v1", "profile": profile, "map_id": "synthetic-map",
                   "map": source_map, "tiles": [item["source"] for item in tiles], "tools": tools}
        self.write_json(root / "requested.json", request)
        manifest = {"format": "bnav-wow-selection-v1", "status": "SELECTED_REGION", "game": "wow",
                    "map_id": "synthetic-map", "profile": profile, "reference_bits": 64,
                    "scope": {"kind": "explicit-selected-tiles", "whole_map_coverage": False,
                              "unselected_tiles": "unknown; neither empty nor evaluated"},
                    "tools": tools, "request_sha256": digest((root / "requested.json").read_bytes()),
                    "map": map_record, "tiles": tiles, "errors": [],
                    "counts": {"imported": len(tiles), "missing": 0}, "game_qa": "NOT_RUN",
                    "producer_identity": "UNVERIFIED"}
        self.write_json(root / "manifest.json", manifest)
        return root, request, manifest

    def test_explicit_profile_abi_and_map_grid_control_tile_placement(self):
        for bits, profile in ((32, "cmangos-v8"), (64, "cmangos-v8-ref64")):
            params = nav.inspect_map(map_bytes(bits), profile)
            inspection, payload = nav.inspect_wrapper(wrapped_tile(bits), profile, params)
            self.assertEqual(params["origin"], [10.0, -2.0, -30.0])
            self.assertEqual(inspection["coordinates"], [2, 1, 0])
            self.assertEqual(inspection["bounds_min"], [50.0, -2.0, -10.0])
            with self.subTest(bits=bits), self.assertRaises(nav.Invalid):
                nav.inspect_raw(payload, 96 - bits, params)
            shifted = copy.deepcopy(params)
            shifted["origin"][0] = 0.0
            with self.assertRaises(nav.Invalid):
                nav.inspect_raw(payload, bits, shifted)
        for profile in (None, "automatic", "cmangos-v8", "acore-v20"):
            with self.subTest(profile=profile), self.assertRaises(nav.Invalid):
                nav.inspect_map(map_bytes(), profile)
        data = bytearray(map_bytes())
        for offset, value in ((0, float("nan")), (12, 0.0)):
            corrupt = bytearray(data)
            struct.pack_into("<f", corrupt, offset, value)
            with self.subTest(offset=offset), self.assertRaises(nav.Invalid):
                nav.inspect_map(corrupt, "cmangos-v8-ref64")

    def test_polygon_flags_areas_liquids_and_exact_payload_are_preserved(self):
        data = wrapped_tile()
        params = nav.inspect_map(map_bytes(), "cmangos-v8-ref64")
        inspection, payload = nav.inspect_wrapper(data, "cmangos-v8-ref64", params)
        self.assertEqual(payload, data[20:])
        self.assertEqual(inspection["polygon_flags"], {"65": 1})
        self.assertEqual(inspection["polygon_areas"], {"3": 1})
        self.assertEqual(inspection["polygon_types"], {"0": 1})
        self.assertEqual(inspection["off_mesh_connections"], 0)
        self.assertIs(inspection["uses_liquids"], True)
        for corrupt in (data[:-1], data + b"x", wrapped_tile(area=67)):
            with self.subTest(length=len(corrupt)), self.assertRaises(nav.Invalid):
                nav.inspect_wrapper(corrupt, "cmangos-v8-ref64", params)
        with self.assertRaises(nav.Invalid):
            nav.inspect_wrapper(data, "acore-v20", params)

    def test_query_flag_policy_requires_nonempty_effective_include_mask(self):
        nav.flags_policy(0x41, 0x40)
        nav.flags_policy(65535, 0)
        for include, exclude in ((0, 0), (True, 0), (65536, 0), (1, -1),
                                 (1, 65536), (0x41, 0x41), (1, 65535)):
            with self.subTest(include=include, exclude=exclude), self.assertRaises(nav.Invalid):
                nav.flags_policy(include, exclude)

    def test_selection_inventory_and_scope_cannot_claim_unselected_tiles(self):
        root, _, manifest = self.selection("inventory")
        valid, map_path, paths = nav.validate_selection(root / "manifest.json")
        self.assertEqual(map_path, root / "map.mmap")
        self.assertEqual(len(paths), 2)
        self.assertEqual(valid["status"], "SELECTED_REGION")
        self.assertIs(valid["scope"]["whole_map_coverage"], False)
        self.assertIn("unknown", valid["scope"]["unselected_tiles"])
        for index, mutate in enumerate((
            lambda m: m["tiles"].pop(),
            lambda m: m["tiles"][0].update(status="missing"),
            lambda m: m.update(status="COMPLETE"),
            lambda m: m["scope"].update(whole_map_coverage=True),
            lambda m: m.update(reference_bits=32),
            lambda m: m["map"]["parameters"].update(tile_width=40.0),
            lambda m: m["tiles"][0]["inspection"].update(polygon_flags={"1": 1}),
        )):
            changed = copy.deepcopy(manifest)
            mutate(changed)
            path = root / f"invalid-{index}.json"
            self.write_json(path, changed)
            with self.subTest(index=index), self.assertRaises(nav.Invalid):
                nav.validate_selection(path)
        duplicate_root, _, _ = self.selection("duplicate-coordinates", tile_x=(2, 2))
        with self.assertRaises(nav.Invalid):
            nav.validate_selection(duplicate_root / "manifest.json")

    def test_retained_map_wrapper_and_payload_hashes_cannot_be_substituted(self):
        for name in ("map.mmap", "source/000.mmtile", "tiles/000.navtile"):
            root, _, _ = self.selection("hash")
            data = bytearray((root / name).read_bytes())
            data[-1] ^= 1
            (root / name).write_bytes(data)
            with self.subTest(name=name), self.assertRaises(nav.Invalid):
                nav.validate_selection(root / "manifest.json")
        root, _, manifest = self.selection("payload-substitution")
        data = bytearray((root / "tiles/000.navtile").read_bytes())
        struct.pack_into("<H", data, 164, 1)
        (root / "tiles/000.navtile").write_bytes(data)
        manifest["tiles"][0]["raw"] = self.file_record("tiles/000.navtile", data)
        self.write_json(root / "manifest.json", manifest)
        with self.assertRaises(nav.Invalid):
            nav.validate_selection(root / "manifest.json")
        root, request, manifest = self.selection("source-substitution")
        request["tiles"][0]["sha256"] = "0" * 64
        self.write_json(root / "requested.json", request)
        manifest["request_sha256"] = digest((root / "requested.json").read_bytes())
        self.write_json(root / "manifest.json", manifest)
        with self.assertRaises(nav.Invalid):
            nav.validate_selection(root / "manifest.json")

    def test_request_and_extraction_receipts_bind_exact_selection(self):
        for change in ("request", "receipt-hash", "receipt-command", "source-path"):
            root, request, manifest = self.selection(change)
            if change == "request":
                request["tiles"].reverse()
                self.write_json(root / "requested.json", request)
            elif change == "receipt-hash":
                self.write_json(root / "receipts/000.json", {"exit_code": 1})
            elif change == "receipt-command":
                path = root / "receipts/000.json"
                receipt = json.loads(path.read_text())
                receipt["argv"][2] = "cmangos-v8"
                self.write_json(path, receipt)
                manifest["tiles"][0]["receipt"] = self.file_record("receipts/000.json", path.read_bytes())
                self.write_json(root / "manifest.json", manifest)
            else:
                request["tiles"][1]["path"] = request["tiles"][0]["path"]
                self.write_json(root / "requested.json", request)
                manifest["request_sha256"] = digest((root / "requested.json").read_bytes())
                self.write_json(root / "manifest.json", manifest)
            with self.subTest(change=change), self.assertRaises(nav.Invalid):
                nav.validate_selection(root / "manifest.json")


if __name__ == "__main__":
    unittest.main()
