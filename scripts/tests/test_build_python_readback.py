"""Focused archive startup checks using original, synthetic Python fixtures.

Retain inputs and receipts outside git. Set CHECK_BUILD_SCRIPT to exercise an
integrator's checker before this test-only branch is merged.
"""

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest


SCRIPT = Path(os.environ.get(
    "CHECK_BUILD_SCRIPT", Path(__file__).resolve().parents[1] / "check_build.py"
)).resolve()
FIXTURE = "source/crates/bot-soak/examples/synthetic-short.csv"
WRAPPERS = ("bake_nav_collection.py", "import_wow_nav.py")
MODULE = "source/scripts/nav_route_metrics.py"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fake_binary(name):
    # Exercise the actual archive/CLI boundary without native executables.
    return (f"#!{sys.executable}\n" + f"NAME = {name!r}\n" + """
import sys
if sys.argv[1:] == ['--help']:
    print(NAME + ' synthetic startup fixture')
elif sys.argv[1:] == ['--version']:
    print(NAME + ' 0.1.0')
elif NAME == 'bot-soak' and sys.argv[1] == 'replay':
    print('verdict=INCOMPLETE\\nsource=synthetic\\nlive_game_qa=NOT_RUN')
    raise SystemExit(3)
else:
    raise SystemExit(9)
""").encode()


def wrapper():
    return b"""import argparse
import json
from pathlib import Path
import sys
import nav_route_metrics

with Path('source-invocations.jsonl').open('a') as log:
    log.write(json.dumps({'wrapper': __file__, 'module': nav_route_metrics.__file__,
                         'identity': nav_route_metrics.IDENTITY,
                         'args': sys.argv[1:]}) + '\\n')
parser = argparse.ArgumentParser(description='synthetic query wrapper')
query = parser.add_subparsers().add_parser('query')
nav_route_metrics.configure(query)
parser.parse_args()
"""


def shared_module(projection_option=True):
    option = "parser.add_argument('--max-projection-distance', type=float)" if projection_option else "pass"
    return ("IDENTITY = 'packaged-sibling'\ndef configure(parser):\n    " + option + "\n").encode()


class PythonArchiveReadback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = Path.home() / ".local/share/banshee-bot-core/evidence/build-python-readback-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.evidence = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        print(f"synthetic_test_evidence={cls.evidence}", flush=True)
        cls.results = []

    @classmethod
    def tearDownClass(cls):
        receipt = {"scope": "synthetic packaged Python startup only", "checker": str(SCRIPT),
                   "checker_sha256": digest(SCRIPT.read_bytes()), "cases": cls.results,
                   "native_ffxi_p0": "NOT_RUN", "game_qa": "NOT_RUN"}
        (cls.evidence / "test-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def build(self, label, python=True, module=True, projection_option=True, corrupt=False):
        root = Path(tempfile.mkdtemp(prefix=label + "-", dir=self.evidence))
        name = "banshee-bot-core-0.1.0-build9999"
        files = {
            "bin/bnav-extract": fake_binary("bnav-extract"),
            "bin/bot-soak": fake_binary("bot-soak"),
            FIXTURE: b"source,zone\nsynthetic,100\n",
        }
        if python:
            files.update({f"source/scripts/{name}": wrapper() for name in WRAPPERS})
            if module:
                files[MODULE] = shared_module(projection_option)
        # This valid, listed source must remain unextracted and unexecuted.
        files["source/scripts/other.py"] = b"raise RuntimeError('not an allowlisted tool')\n"
        files["source/later.txt"] = b"later member after every Python wrapper\n"
        manifest = {
            "format": "banshee-private-build-v1", "name": name, "build": "9999",
            "version": "0.1.0", "source_commit": "a" * 40,
            "files": {path: {"sha256": digest(data), "bytes": len(data)}
                      for path, data in files.items()},
        }
        if corrupt:
            manifest["files"]["source/later.txt"]["sha256"] = "0" * 64
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
        (root / "manifest.json").write_bytes(manifest_bytes)
        artifact = root / f"{name}.tar.gz"
        with artifact.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for path, data in {**files, "manifest.json": manifest_bytes, "build.log": b"synthetic\n"}.items():
                    item = tarfile.TarInfo(f"{name}/{path}")
                    item.size = len(data)
                    item.mode = 0o755 if path.startswith("bin/") else 0o644
                    archive.addfile(item, io.BytesIO(data))
        (root / "SHA256SUMS").write_text(f"{digest(artifact.read_bytes())}  {artifact.name}\n")
        return root, artifact

    def check(self, root, artifact, expected, env=None):
        output = root / "readback"
        argv = [sys.executable, "-E", "-s", "-B", str(SCRIPT), "--artifact", str(artifact),
                "--expected-bytes", str(artifact.stat().st_size), "--evidence", str(output)]
        result = subprocess.run(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (root / "checker.log").write_bytes(result.stdout)
        receipt = json.loads((output / "result.json").read_text())
        self.results.append({"test": self.id(), "argv": argv, "exit_code": result.returncode,
                             "expected_exit": expected, "receipt": str(output / "result.json")})
        self.assertEqual(result.returncode, expected, result.stdout.decode(errors="replace"))
        self.assertEqual(receipt["verdict"], "PASS" if expected == 0 else "FAIL")
        return output, receipt

    def test_allowlisted_wrappers_import_the_packaged_sibling(self):
        root, artifact = self.build("siblings")
        output, receipt = self.check(root, artifact, 0)
        extracted = receipt["extracted"]
        self.assertNotIn("source/scripts/other.py", extracted)
        self.assertNotIn("source/later.txt", extracted)
        module_path = Path(extracted[MODULE])
        self.assertEqual(module_path.read_bytes(), shared_module())
        for name in WRAPPERS:
            path = Path(extracted[f"source/scripts/{name}"])
            self.assertEqual(path.parent, module_path.parent)
            self.assertFalse(stat.S_IMODE(path.stat().st_mode) & 0o111)
        calls = [json.loads(line) for line in (output / "source-invocations.jsonl").read_text().splitlines()]
        self.assertEqual(len(calls), 4)
        self.assertEqual({Path(call["wrapper"]).name for call in calls}, set(WRAPPERS))
        self.assertEqual({tuple(call["args"]) for call in calls}, {("--help",), ("query", "--help")})
        self.assertTrue(all(call["module"] == str(module_path) and call["identity"] == "packaged-sibling"
                            for call in calls))
        python_calls = [call for call in receipt["tool_invocations"] if call["argv"][0] == sys.executable]
        self.assertEqual(len(python_calls), 4)
        self.assertTrue(all(call["argv"][1:4] == ["-E", "-s", "-B"] for call in python_calls))
        self.assertTrue(receipt["python_startup"])
        self.assertFalse(list(output.rglob("__pycache__")))

    def test_missing_imported_module_fails_startup(self):
        root, artifact = self.build("missing-module", module=False)
        output, receipt = self.check(root, artifact, 1)
        self.assertNotIn(MODULE, receipt["extracted"])
        self.assertFalse((output / "source-invocations.jsonl").exists())
        logs = "\n".join(path.read_text() for path in output.glob("*.log"))
        self.assertIn("ModuleNotFoundError", logs)
        self.assertIn("nav_route_metrics", logs)

    def test_corrupt_later_member_prevents_every_tool_invocation(self):
        root, artifact = self.build("late-corruption", corrupt=True)
        output, receipt = self.check(root, artifact, 1)
        self.assertIn("payload digest mismatch: source/later.txt", receipt["error"])
        self.assertEqual(receipt["tool_invocations"], [])
        self.assertFalse((output / "source-invocations.jsonl").exists())
        self.assertTrue(list(output.rglob("bake_nav_collection.py")), "fixture must reach wrapper extraction")

    def test_legacy_archive_without_python_tools_remains_valid(self):
        root, artifact = self.build("legacy", python=False)
        output, receipt = self.check(root, artifact, 0)
        self.assertFalse(any(path.startswith("source/scripts/") for path in receipt["extracted"]))
        self.assertFalse((output / "source-invocations.jsonl").exists())
        self.assertFalse(any(call["argv"][0] == sys.executable for call in receipt["tool_invocations"]))
        self.assertEqual(receipt["synthetic_soak"]["exit_code"], 3)

    def test_pythonpath_cannot_supply_a_missing_packaged_module(self):
        root, artifact = self.build("ignored-pythonpath", module=False)
        poison = root / "injected-module"
        poison.mkdir()
        marker = root / "injection-executed"
        code = f"from pathlib import Path\nPath({str(marker)!r}).write_text('unexpected import')\n"
        (poison / "nav_route_metrics.py").write_bytes(code.encode() + shared_module())
        env = dict(os.environ, PYTHONPATH=str(poison))
        output, receipt = self.check(root, artifact, 1, env=env)
        self.assertFalse(marker.exists())
        self.assertFalse((output / "source-invocations.jsonl").exists())
        python_calls = [call for call in receipt["tool_invocations"] if call["argv"][0] == sys.executable]
        self.assertEqual(len(python_calls), 1)
        self.assertEqual(python_calls[0]["argv"][1:4], ["-E", "-s", "-B"])

    def test_shared_module_without_projection_option_fails_query_smoke(self):
        root, artifact = self.build("missing-projection", projection_option=False)
        output, receipt = self.check(root, artifact, 1)
        calls = [json.loads(line) for line in (output / "source-invocations.jsonl").read_text().splitlines()]
        self.assertTrue(any(call["args"] == ["query", "--help"] for call in calls))
        self.assertIn("projection", receipt["error"])


if __name__ == "__main__":
    unittest.main()
