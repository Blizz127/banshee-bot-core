# Private QA candidate 0.1.0-build0007

Created **2026-11-15 03:14:21 CST**. **QA_CANDIDATE, not released.**
Release/startup and archive/source readback: **PASS**. Private publication has
no receipt; native FFXI P0 and Game QA remain **NOT_RUN**. New features stay OFF.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0007/banshee-bot-core-0.1.0-build0007.tar.gz` |
| SHA-256 | `cc2e1ebba007aa2ffe8e252ecca302ffab4cd4ed63cf636ce32782f2d7101193` |
| Bytes | `1004821` |
| Source commit | `2e396109f92354a90bbc92e3b0657de6ed155056` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

This increment adds [endpoint projection measurements and an optional distance
limit](NAV_ROUTE_METRICS.md) to collection and selected-WoW queries. A complete
native path that projects too far can now return an explicit policy failure.
The original native result is preserved. No shared Rust or native backend code
changed; existing core source adoption guidance and FFXI producer pins stand.

## Verification

- VERIFIED: all 100 archived payloads and nine packaged binary invocations pass.
  Four packaged Python help invocations verify module imports and the new flag.
- VERIFIED: all 18 core/workspace files match the completed current-source C1
  comparison. Four packaged projection source/test files match the separately
  completed checks. This authenticates those bytes; it does not replay or
  aggregate native platform checks.
- VERIFIED before packaging: ten synthetic query checks across both wrappers
  exercise omitted/passing/failing limits and invalid arguments before backend
  access. Nineteen separate pure metrics checks cover 3D distance, path length,
  boundary/zero limits, malformed results, overflow and bounds.
- Native adapter/P0, physical calibration, full-zone navigation, live bot soak
  and Game QA remain unverified. Source 756eb165's reported 8/8 authority-only
  module adoption is separate evidence, not a full adapter acceptance result.

Receipts beneath `/home/blizz/.local/share/banshee-bot-core/`:

| Receipt | SHA-256 |
| --- | --- |
| `evidence/build0007-readback/result.json` | `510070cc959714def736185d7630cd9fa1ba32f2c1ec7760d5e8392e9c1e0fde` |
| `evidence/build0007-readback/source-readback.json` | `d10faab3b622a0f5c0c5bc9074e197fb9b36ec55c613c9c0787975f3da9dbce9` |
| `evidence/nav-projection-wrappers-20261115/synthetic-smoke-b_ytdxo8/run-dov1bihp/result.json` | `75388d164cf6e8c79b496f77b1ae45ff028fba95ffcc83270f48479917ec2012` |
| `evidence/nav-route-metrics-tests/run-uounrt9s/result.json` | `4e15bf54926eeadf19a1f04e7f2bca5c997f89ac266a51d49dcad9c902a98ac7` |

## Existing private publisher intake

**Supersedes build0006 as the proposed private tool candidate only.** Retain
earlier candidates for rollback. Route one concrete intake through coordinator
task `dcc9a63a40ab` to existing publisher `claude-banshee-realm-client`, standing
task `3f9392ca5d00`. The existing FFXI source/adoption intake remains unchanged;
do not duplicate it or replace its evidence with these synthetic tool checks.

Platform remains Linux x86-64 with dynamic system dependencies and Python 3.11
for the script set. Existing entry points are in [build0004](BUILD_0004.md).
Ship `source/scripts/nav_route_metrics.py` beside both query wrappers: it is
their new standard-library-only dependency. The archive is a developer tool
and source kit; it contains no client assets, game maps or deployed service.
The publisher owns channel identity, uploaded size/SHA readback, launch/update
contract and rollback. No bot-core feed contract or publication receipt is
established here.

**Never restart FFXI**, including at zero players. The manifest retains this
hold and grants no installation/reload authority. No game state changed.
