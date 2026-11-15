# Private QA candidate 0.1.0-build0005

Created **2026-11-15 02:47:15 CST**. **QA_CANDIDATE, not released.**
Release/startup, archive readback and focused offline checks: **PASS**.
Native C1 adoption/P0, Game QA and private publication: **NOT_RUN/NOT_PERFORMED**.
New features stay **OFF**; the standing FFXI no-restart hold remains embedded.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0005/banshee-bot-core-0.1.0-build0005.tar.gz` |
| SHA-256 | `d9fa0f83011ea5c359f86ec5b46974fa60eb0980f700107bddc02fd9ca2d205a` |
| Bytes | `983475` |
| Source commit | `7489a03f1d1745b7c43a08cd756c6b3862a88517` |
| Manifest/checksum | Same directory: `manifest.json`, `SHA256SUMS` |

This increment adds explicit FFXI zone/DAT selection, verified retained decoder
reuse and authenticated reuse of the corrected owning native harness. Fresh
compilation remains available. Source, original drivers, locks and executables
are checked before reuse; receipts distinguish executed checks from historical
build/test results. Unsupported water and path mismatches still refuse output.

VERIFIED: archive readback checks all **94** payloads and **nine** packaged
tool invocations. Both changed Python entrypoints also start from verified
archive bytes. Receipts beneath the private data root:

- `evidence/build0005-readback/result.json`, SHA-256
  `824aabd5800af2b1ae350023ec10c612f86a522c607b7eb62a04720cc5e32bab`.
- `evidence/build0005-readback/changed-script-startup.json`, SHA-256
  `fa646cea36a0f6ec36f343c5197f9fe59900777d49aaca8c279ec844ded37f1b`.

VERIFIED before packaging: ten exporter integrity checks and ten native-harness
integrity checks pass. The original zone230 OBJ reproduces byte for byte using
the generalized selector. The explicit zone101 crop exports 72 triangles,
bakes/reloads to four polygons, and passes 12 corrected wrapper cases plus exact
owning native load/nearest/corridor/straight-path checks without recompilation.
See [export evidence](FFXI_EXPORT.md), [native consumption](FFXI_NATIVE_CONSUMPTION.md)
and the [consolidated FFXI intake](FFXI_OFFLINE_INTAKE.md). These actual-geometry
checks retain their pre-package execution identities; they were not relabelled
as new packaged-tool runs. The native32/64 binary bytes are unchanged from 0004.

The core itself remains the earlier `36b90715` extraction. A new bounded source
audit observed later `5c73a875` control, grammar and formation-order changes;
alignment and differential verification are in progress. **The earlier C1
comparison does not establish equivalence with that newer source.** This
candidate is useful offline tooling, not a current native C1 acceptance result.

Platform, entrypoints and private publisher ownership remain as in
[build0004](BUILD_0004.md): Linux x86-64 tools, Python 3.11 for the complete
script set, separate native32/64 helpers, no daemon/client/server restart.
Preserve all earlier candidates for rollback. A subsequent publisher intake
must name the exact selected candidate and what it supersedes; a task-board
report alone is not private publication.
