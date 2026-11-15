# Private QA candidate 0.1.0-build0002

Created **2026-11-15 02:09:25 CST**. **QA_CANDIDATE, not released.**
Native FFXI P0 and Game QA: **NOT_RUN**. New feature defaults: **OFF**.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0002/banshee-bot-core-0.1.0-build0002.tar.gz` |
| SHA-256 | `903efc88d4d5dc71a0cb73082e37577be39b340b45a3007f8d09247f1180c9c8` |
| Bytes | `736760` |
| Source commit | `b3b8ffd88eec4199aeca9e54204da96d9a6df918` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

The candidate adds pure ownership, selection and order preparation/revalidation
contracts to the C1 source library. Tiled Recast baking, cross-tile queries and
the bounded collection script extend the developer tools. It contains 64
manifest-listed files, including original source and selected check receipts.
No game assets, accounts or extracted geometry are packaged.

The executables are Linux x86-64 developer tools, not a playable game client.
The bundled native backend uses **32-bit** Detour references. A separate
[64-bit pipeline check](NAV_ABI_VERIFICATION.md) passed; that helper is not in
this archive. FFXI's current single-tile loader still requires its owning lead
to implement collection support before using tiled output.

## Validation

- VERIFIED: clean release build and CLI startup checks pass; synthetic soak
  retains exit 3 / INCOMPLETE.
- VERIFIED: expanded pinned-source compatibility compares 47,524 additional
  authority/selection/order outcomes, plus the existing parser/clock corpus.
  See [the C1 intake](C1_ADAPTER_HANDOFF.md) for exact scope and receipt.
- VERIFIED: source-development tiled and collection checks pass, including
  seam routing, wall avoidance, explicit empty cells and rejected corruption.
  Existing single-tile raw outputs remain byte-identical to build0001.
- Archive readback and packaged tiled smoke: pending at this document revision.

No native FFXI integration, server P0, hour-long bot soak, actual-client QA or
private launcher publication is claimed. C2 and later rollout phases remain
behind C1 acceptance.

## Superseding publisher intake

This candidate **supersedes build0001 as the proposed developer-tool package**;
retain build0001 for rollback. Route one intake through Devbox task
`dcc9a63a40ab` to existing publisher project/session `claude-banshee-realm-client`,
standing task `3f9392ca5d00`. Publisher ownership and readback requirements are
unchanged from [build0001](BUILD_0001.md). No new worker or public channel is
authorized by this intake.

Entry points from the archive's top-level directory:

```text
bin/bnav-extract --help
bin/bnav-recast --help
bin/bot-soak --help
python3 source/scripts/bake_nav_collection.py --help
```

Geometry build/query commands require explicit private input and backend paths.
`bot-soak replay` consumes recorded telemetry and does not spawn bots. The core
library is source for the owning server to integrate. There is no daemon or
server restart in the tool launch contract.

Publication remains with Banshee Client Bot; this repo has no bot-core private
feed contract or publisher readback receipt. The package is retained locally
for that actionable intake, not labeled released.
