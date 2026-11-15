# FFXI navigation wrapper compatibility

**Successor update:** the original-a13 failure documented below is retained
historically. The owner's `5c73a875` correction now passes our exact owned-tile
compatibility and offline native-library checks; see
[corrected consumption](FFXI_NATIVE_CONSUMPTION.md). The accepted producer pin
is unchanged and no server/P0/Game QA result follows.

**Producer identity update, 03:25 CST:** the newer backend's saved build chain
is separate from the retained d999 producer. The exact `f64f0648…` debug
extractor used in the newer comparison crop lacks an immutable
source/lock/build/toolchain association in the inspected records. No adoption
is proposed for that pair. [The existing intake's reconciliation](FFXI_OFFLINE_INTAKE.md#e-producer-identity-reconciliation--no-adoption-proposed)
records the evidence and an ordinary 32-bit single-tile draft profile. One equal
crop does not establish general equivalence; the allowlist remains unchanged.

2026-11-15 CST. This checks the existing FFXI source wrapper against shared
backend outputs. It does not install navigation files, invoke the FFXI native
loader, run `/fb` P0, or establish Game QA. C1 behavior adoption remains a
separate owning-lane task.

## Exact source and scope

The check builds `server/crates/forever-audit/src/detour_mset.rs` from the
read-only FFXI git object
`a13dabcd550e0a777be5077804ba3d51683cfa19`. Source SHA-256:
`5bf2638184ec007fde180a41f24646687572bb94185684056a7b39ec59c1fd5f`.
The exact module is copied outside git and compiled unchanged with an original
small caller. Neither the FFXI checkout nor its Cargo target is modified.

The wrapper accepts one little-endian Detour 7 tile with 32-bit references,
zero tile x/y/layer/userId, ordinary ground polygons and no external portals
or off-mesh links. It validates the raw sections before prepending 40 bytes of
MSET header and an 8-byte tile header. It performs no coordinate transform.
Accepted output must retain the entire raw payload unchanged at byte 48.

`Producer::BansheeAe73Raw32` accepts only backend SHA-256
`d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`,
and requires nonzero hashes for the build receipt, geometry manifest and OBJ.
Those hashes are caller declarations; the wrapper does not authenticate their
contents. The helper checks the retained files and hashes separately.
`Producer::Synthetic` is used only for synthetic geometry/fixtures.

**Metadata limitation:** the wrapper emits producer commit
`ae73d7f0d0a883e5336acf3ef8dc7696f219058e` as a hardcoded contract label.
It does not accept or verify a caller-supplied source commit. Build0001's
actual package manifest records source
`5e4ba6d6bd961a6915154e6d3f0ad3f6c3b60281`; that retained manifest is
authoritative for the build source. The wrapper label is not proof of a
different build revision.

## Synthetic seam — VERIFIED PASS

The actual build0001 native Recast outputs from synthetic floor, wall and
disconnected-island OBJs were each passed through both the synthetic and
pinned producer variants. All six cases preserve raw bytes and emit MSET1.
Their per-input hashes match the earlier build0001 smoke receipt.

| Input | Raw SHA-256 | Wrapper result |
| --- | --- | --- |
| `floor.navtile` (592 bytes) | `d23f4e543a924c7bebdce7129acb0212bb77450c08838c1c95042197fdf8e1cd` | Accept both declarations |
| `wall.navtile` (1,292 bytes) | `fd2297097d95c6c683fb52b417daa87399a25cf622b92dbd1fa6e70f5a28106d` | Accept both declarations |
| `disconnected.navtile` (772 bytes) | `0a410ab20660729fcd875ac1348d0d28cbbe56d9819f71327c9540998c74013c` | Accept both declarations |
| Native tiled floor `(0,0)` | `00c0f3c32aab737f036cf93311c06f0ac77ed0626f7f14e721f9383a42f8126b` | Refuse external polygon neighbor |
| Native tiled floor `(1,0)` | `990dd3545579123703c7e596b31c8a08e2501fe052f12ddb6088c793ac241334` | Refuse nonzero tile coordinate |
| Native 64-bit raw fixture | `94b5b38cbdba76428d12092731398884757fc0a9c4a38e4343c4596aa1533b49` | Refuse reference ABI/section size |
| Floor with incorrect declared hash | Original floor bytes | Refuse provenance hash mismatch |

The `(0,0)` tile has zero coordinate fields and a native external neighbor
`0x8000` on polygon 2, edge 3; its failure tests the portal boundary separately
from the coordinate boundary. The 64-bit fixture is native
`dtCreateNavMeshData` output with its known 56-byte Acore v20 wrapper removed,
not an end-to-end 64-bit Recast bake. No tile data was rewritten.

Every accepted case also passes the wrapper's pure query-range preflight for
center `[2,0,10]`, half-extents `[2,4,2]`, and refuses `[31,60,30]` extents.
This does not execute a native path query. All emitted manifests retain
`coverage_complete=false`, `agent_calibration_verified=false` and
`native_load_or_query_executed=false`.

Initial complete synthetic receipt:
`~/.local/share/banshee-bot-core/evidence/ffxi-nav-compat-20261115-final/result.json`,
SHA-256 `159d5f1365799e6f99c4373f6bea5c902093fd4699200593d3480ee2cff51901`.
The earlier `ffxi-nav-compat-20261115-attempt1/result.json` is retained as FAIL:
the harness initially expected the word `portal`, whereas the source correctly
returned `external/self/out-of-range polygon neighbor`. The corrected run used
the same compiled source and binary; no wrapper behavior changed.

## Bounded owned FFXI geometry — VERIFIED FAIL

The geometry lane exported 1,821 triangles for a bounded Southern San d'Oria
region using existing pinned FFXI source. OBJ SHA-256:
`df8acf8bbb3f16386d07e4ad5d595dce12f432d220ca4b0e20d5b0d87fa1685a`.
Its sidecar remains external at
`~/.local/share/banshee-bot-core/evidence/ffxi-sandoria230-export-20261115-02/geometry.json`,
SHA-256 `2d666d9698de1755be8b751e4fac8f5f98072a58062aacd1b2ec2d0a8fcf6396`.
The sidecar links the detailed export manifest and owned-source evidence.

The exporter applied `(x,-y,-z)` once and aligned winding with stored normals.
Collision coverage is incomplete: doors, lifts, moving platforms and other
dynamic behavior are omitted. Physical scale and agent dimensions remain
uncalibrated. The bake uses experimental source-unit settings
`0.25 0.2 2 0.5 0.5 45`. These limitations remain attached to the geometry
manifest hash; wrapper acceptance cannot upgrade them.

Both retained build0001 and build0002 produced identical single-tile bytes:
7,856 bytes, 46 polygons, 101 vertices, SHA-256
`4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4`.
Build0002's backend SHA-256 is
`e2d9f815d5354fc3612f4498ae424c76ef4ff461af3ad8fe293eb9ffb5c85818`.
Its honest producer declaration lies outside the wrapper's backend pin.
The same bytes produced by the exact retained build0001 backend can be
evaluated under the pinned declaration with their real geometry evidence.
Neither owned input is relabelled synthetic.

The focused combined run preserves a real compatibility failure:

| Producer declaration for the same raw bytes | Actual result |
| --- | --- |
| Retained build0001 binary and actual geometry/build hashes | Refuse: `detail vertex outside convex polygon` |
| Actual build0002 binary and actual geometry/build hashes | Refuse: `unrecognized producer backend` |

The first case was expected to accept, so the receipt remains **FAIL**, not
converted into a passing negative test. The synthetic cases still pass; the
overall interoperability milestone is **PARTIAL**. No owned-geometry MSET is
produced. The narrowed next correction belongs to the FFXI owning lead:
investigate the detail-mesh predicate against this retained producer output,
then review the newer producer pin and hardcoded metadata separately.

Combined receipt (12 cases, 11 expected outcomes, 1 real compatibility failure):
`~/.local/share/banshee-bot-core/evidence/ffxi-nav-compat-20261115-owned/result.json`,
SHA-256 `a563ffdf1278b4caeaad3f0dc1271a45d6e8f75d2265eeabd2698e81473898c1`.
The exact plans, original source, generated caller, Cargo lock, compiler logs,
input copies and output manifests are retained beside it. All 21 recorded
source inputs were checked unchanged after the failed run in
`post-run-input-check.json`, SHA-256
`2a25400c6f9ade75bb14340cf0d2929642f6e6d29903057c4da586d6f7a30534`.
This separate check was needed because the helper stopped at its nonzero
compatibility exit.

### Exact refused detail vertex — OBSERVED

The first failing polygon is index 20. Its six coarse polygon vertices are
indices `[26,40,44,45,47,3]`; the offending local vertex index 6 is the first
extra detail vertex for that polygon, global detail vertex index 3. It is
absent from the coarse polygon vertex list but participates in boundary-marked
detail segments `0→6` and `6→1` in triangles 42 and 43.

The owning wrapper's `details` routine at source lines 450–495 checks every
coarse and extra detail point against each convex polygon edge. Exact extracted
coordinates for edge 0 and the failing point remain in the external diagnostic
receipt, outside git. The wrapper promotes stored float coordinates to f64 and computes signed XZ
cross product `1.71661376953125e-5`, exceeding its absolute `EPS=1e-6`.
The corresponding perpendicular XZ distance is
`1.1557003118292749e-6` source units. This is a distance in uncalibrated source
units, not metres. The observer found one violation of this particular
predicate across the tile; it did not bypass the refusal or evaluate later
wrapper checks as passed.

Pinned native source provides relevant context: `RecastMeshDetail.cpp`
`buildPolyDetail` samples polygon edges using float interpolation at lines
667–713, then `rcBuildPolyMeshDetail` translates the detail vertices into world
space at lines 1311–1325. `getEdgeFlags` at lines 1141–1157 classifies a detail
edge as boundary using a squared XZ-distance threshold of `0.001²`.
`DetourNavMeshBuilder.cpp` lines 571–594 store additional detail vertices
separately from the polygon vertices. The native boundary flagging
tolerance and the wrapper's signed-cross-product threshold measure different
quantities and cannot be substituted directly.

**INFERRED:** float interpolation/translation at a detail boundary is a useful
candidate cause for investigation. Successful native reload/query of the same
raw tile, reported separately by the root bake receipts, is not proof that
the wrapper is wrong or that relaxing its validation is safe. No tolerance,
source or geometry change was made here. Native FFXI load/query and Game QA
remain **NOT RUN**.

Two additional external receipts retain the exact observation and pinned
source copies:

- `ffxi-nav-compat-20261115-owned/detail-predicate-observation.json`, SHA-256
  `d7918501d1c01a4a18ea2b475ece56911aa2aadc9c1ebd9ee7fc45c4d2c80eab`.
- `ffxi-nav-compat-20261115-owned/native-detail-source-observation.json`, SHA-256
  `73fb63d8e68d729e50b58f40335c5521c0596023fe1751298be5d76b8f9e48a8`.

The latter pins `RecastMeshDetail.cpp` SHA-256
`b1fe99540334134a6307ab3c013dcc5c6b5f9ed41309137b7a8635ebcea1ed20`
and `DetourNavMeshBuilder.cpp` SHA-256
`bbe5adf461cae282291e498db50550eb3a12706e352dd83021165d38950119f3`.
Both match build0001's recorded dependency inputs exactly. Copies and the
zlib licence are retained under the same external evidence directory's
`native-source/`. Build0001 package manifest SHA-256 is
`3c96a31139f4438291085aa2d061e70f09085feba6c4e734b4425ca75bd17c82`.

## Reproduce and provenance

Run `python3 scripts/check_ffxi_nav.py --help` for the explicit input paths.
Select `--reference-profile original-a13` to replay this historical boundary,
or the explicitly pinned corrected profile and packet documented in the
successor check. Source revisions are never selected implicitly.
The tool creates a new evidence directory, snapshots only the exact pinned
module, resolves cached `sha2=0.10.9` and `serde_json=1.0.154` offline, and builds
with `nice -n 19 cargo build --offline --locked -j2` using an external target.
Existing evidence is never overwritten. It records source/input/compiler
identities, command exits, output manifests and before/after input hashes.

An optional repeatable `--owned-case PATH` takes JSON fields `name`,
`raw_tile`, `raw_receipt`, `geometry_manifest`, `backend`, `backend_manifest`,
`expect` and (for expected rejection) `reason_contains`. The helper checks
the bake receipt's exact `single_tile_sha256` or `tile_sha256`, sidecar OBJ
hash, explicit incomplete owner-source coverage, and binary/build-manifest
hash match before constructing a pinned producer declaration. It preserves
the caller's expected result; it does not loosen the owning wrapper.

The original harness and helper are the only code added to this repository.
The private FFXI module snapshot stays outside git. No project licence file
was found in the bounded pinned FFXI tree/package audit; permission here is
the owner's private project delegation, not a redistribution licence.
The two cached Cargo dependencies declare `MIT OR Apache-2.0`; their dependency
closure remains in the external lock/build records. Recast/Detour provenance
and licence are recorded in [PROVENANCE.md](PROVENANCE.md) and the retained
backend manifests. No game asset, decoded geometry, external implementation
or compiled harness enters this git repository.

The FFXI owning lead must review any producer whitelist/metadata update,
tiled loader support and native query integration in its own lane. Current
source-level results do not remove C1/P0, calibration, coverage or Game QA
gates and do not block independent shared-core work.
