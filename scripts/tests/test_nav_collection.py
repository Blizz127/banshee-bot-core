"""Focused collection integrity tests; all fixtures are synthetic and retained."""

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
    "BNAV_COLLECTION_SCRIPT", Path(__file__).resolve().parents[1] / "bake_nav_collection.py"
))
sys.path.insert(0, str(SCRIPT.resolve().parent))
SPEC = importlib.util.spec_from_file_location("nav_collection", SCRIPT)
nav = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nav)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def grid():
    return dict(origin_x=0.0, origin_z=0.0, min_y=0.0, max_y=3.0,
                tile_cells=40, x_min=0, x_max=1, z_min=0, z_max=0,
                cell_size=0.5, cell_height=0.2, agent_height=2.0,
                agent_radius=0.6, agent_climb=0.9, max_slope=45.0)


def header_tile():
    # A structural header/section fixture only. Payload is not a navigable mesh
    # and is never sent to native Detour. Link count makes 32/64-bit ABI distinct.
    data = bytearray(236)
    struct.pack_into("<IIiii", data, 0, 0x444E4156, 7, 0, 0, 0)
    struct.pack_into("<9i", data, 24, 1, 3, 3, 1, 0, 1, 1, 0, 1)
    struct.pack_into("<3f", data, 60, 2.0, 0.6, 0.9)
    struct.pack_into("<3f", data, 72, 0.0, -0.2, 0.0)
    struct.pack_into("<3f", data, 84, 20.0, 8.1, 20.0)
    struct.pack_into("<f", data, 96, 2.0)
    return bytes(data)


class CollectionIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path.home() / ".local/share/banshee-bot-core/evidence/nav-collection-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.evidence = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        print(f"synthetic_test_evidence={cls.evidence}", flush=True)

    def directory(self, label):
        return Path(tempfile.mkdtemp(prefix=label + "-", dir=self.evidence))

    def write_json(self, path, obj):
        path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")

    def source(self, root):
        geometry = b"v 0 0 0\nv 1 0 0\nv 0 0 1\nf 1 3 2\n"
        (root / "input.obj").write_bytes(geometry)
        return {
            "format": "bnav-geometry-v1", "game": "synthetic", "zone": "header-test",
            "geometry": {"path": "input.obj", "sha256": digest(geometry)},
            "coordinates": {"up_axis": "Y", "units": "test-unit", "transform": "identity"},
            "coverage": {"scope": "synthetic fixture", "limitations": ["not game geometry"]},
            "provenance": {"description": "original structural unit fixture", "classification": "synthetic"},
        }

    def collection(self, label):
        root = self.directory(label)
        (root / "tiles").mkdir()
        (root / "receipts").mkdir()
        source = self.source(root)
        self.write_json(root / "source.json", source)
        tile = header_tile()
        (root / "tiles/0_0.navtile").write_bytes(tile)
        for x, exit_code in ((0, 0), (1, 3)):
            argv = ["/synthetic/extractor", "build-tile-obj", "/synthetic/backend",
                    str(root / "input.obj"), str(root / f"tiles/{x}_0.navtile"),
                    "0.0", "0.0", "0.0", "3.0", "40", str(x), "0",
                    "0.5", "0.2", "2.0", "0.6", "0.9", "45.0"]
            self.write_json(root / f"receipts/{x}_0.json", {"exit_code": exit_code, "argv": argv})
        tiles = [
            {"x": 0, "z": 0, "status": "built", "path": "tiles/0_0.navtile", "bytes": len(tile),
             "sha256": digest(tile), "receipt": "receipts/0_0.json",
             "receipt_sha256": digest((root / "receipts/0_0.json").read_bytes())},
            {"x": 1, "z": 0, "status": "empty", "receipt": "receipts/1_0.json",
             "receipt_sha256": digest((root / "receipts/1_0.json").read_bytes())},
        ]
        manifest = {
            "format": "bnav-collection-v1", "status": "COMPLETE", "errors": [],
            "grid": grid(), "reference_bits": 32, "tiles": tiles,
            "counts": {"built": 1, "empty": 1, "missing": 0},
            "source_sidecar_sha256": digest((root / "source.json").read_bytes()),
            "geometry": {"path": str(root / "input.obj"), "sha256": source["geometry"]["sha256"],
                         "bytes": (root / "input.obj").stat().st_size},
            "tools": {name: {"path": f"/synthetic/{name}", "sha256": "0" * 64, "bytes": 1}
                      for name in ("extractor", "backend")},
            **{key: copy.deepcopy(source[key]) for key in ("game", "zone", "coordinates", "coverage", "provenance")},
        }
        self.write_json(root / "manifest.json", manifest)
        return root, source, manifest

    def test_json_rejects_duplicate_keys_nonfinite_values_and_nonobjects(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'[]'):
            with self.subTest(data=data), self.assertRaises(nav.Invalid):
                nav.decode_json(data)

    def test_source_requires_identity_y_up_and_matching_geometry_hash(self):
        root = self.directory("source")
        source = self.source(root)
        self.write_json(root / "valid.json", source)
        self.assertEqual(nav.source_record(root / "valid.json")[2], root / "input.obj")
        for index, mutate in enumerate((
            lambda s: s.pop("game"),
            lambda s: s["coordinates"].update(up_axis="Z"),
            lambda s: s["geometry"].update(sha256="0" * 64),
            lambda s: s["provenance"].update(classification="verified"),
        )):
            invalid = copy.deepcopy(source)
            mutate(invalid)
            path = root / f"invalid-{index}.json"
            self.write_json(path, invalid)
            with self.subTest(index=index), self.assertRaises(nav.Invalid):
                nav.source_record(path)

    def test_grid_rejects_impossible_dimensions_nonfinite_values_and_excessive_coverage(self):
        self.assertEqual(nav.validate_grid(grid()), [(0, 0), (1, 0)])
        for changes in ({"tile_cells": 0}, {"tile_cells": True}, {"cell_size": 0.0},
                        {"min_y": 4.0}, {"origin_x": float("nan")}, {"x_min": -1},
                        {"x_max": 256}, {"z_max": 4096}, {"agent_height": 0.1}):
            with self.subTest(changes=changes), self.assertRaises(nav.Invalid):
                nav.validate_grid({**grid(), **changes})

    def test_complete_inventory_cannot_hide_missing_duplicate_or_unidentified_cells(self):
        root, _, manifest = self.collection("inventory")
        self.assertEqual(len(nav.validate_collection(root / "manifest.json")[1]), 1)
        for index, mutate in enumerate((
            lambda m: m["tiles"].pop(),
            lambda m: m["tiles"].__setitem__(1, copy.deepcopy(m["tiles"][0])),
            lambda m: m["tiles"][1].update(status="missing"),
            lambda m: m.update(status="INCOMPLETE"),
            lambda m: m["counts"].update(empty=0),
            lambda m: m.update(tools=[]),
            lambda m: m.update(geometry=[]),
        )):
            invalid = copy.deepcopy(manifest)
            mutate(invalid)
            path = root / f"invalid-{index}.json"
            self.write_json(path, invalid)
            with self.subTest(index=index), self.assertRaises(nav.Invalid):
                nav.validate_collection(path)
        root, source, invalid = self.collection("identity")
        source.pop("game")
        invalid.pop("game")
        self.write_json(root / "source.json", source)
        invalid["source_sidecar_sha256"] = digest((root / "source.json").read_bytes())
        self.write_json(root / "invalid-identity.json", invalid)
        with self.assertRaises(nav.Invalid):
            nav.validate_collection(root / "invalid-identity.json")

    def test_recorded_hashes_reject_tampering_and_empty_cells_cannot_contain_output(self):
        for change in ("receipt", "tile", "empty-output", "path"):
            root, _, manifest = self.collection(change)
            if change == "receipt":
                (root / "receipts/0_0.json").write_text('{"exit_code":2}\n')
            elif change == "tile":
                data = bytearray((root / "tiles/0_0.navtile").read_bytes())
                data[-1] ^= 1
                (root / "tiles/0_0.navtile").write_bytes(data)
            elif change == "empty-output":
                (root / "tiles/1_0.navtile").write_bytes(header_tile())
            else:
                manifest["tiles"][0]["path"] = "../elsewhere.navtile"
                self.write_json(root / "manifest.json", manifest)
            with self.subTest(change=change), self.assertRaises(nav.Invalid):
                nav.validate_collection(root / "manifest.json")

    def test_raw_header_abi_coordinates_agent_settings_and_grid_must_match(self):
        data = header_tile()
        nav.inspect_tile(data, grid(), 0, 0, 32)
        with self.assertRaises(nav.Invalid):
            nav.inspect_tile(data, grid(), 0, 0, 64)
        for offset, fmt, value in ((8, "<i", 1), (16, "<i", 1), (60, "<f", 4.0),
                                   (72, "<f", 1.0), (84, "<f", 19.0)):
            corrupt = bytearray(data)
            struct.pack_into(fmt, corrupt, offset, value)
            with self.subTest(offset=offset), self.assertRaises(nav.Invalid):
                nav.inspect_tile(corrupt, grid(), 0, 0, 32)


if __name__ == "__main__":
    unittest.main()
