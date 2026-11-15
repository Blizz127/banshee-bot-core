# FFXI corrected wrapper and native consumption

2026-11-15 CST. Task `dcc9a63a40ab`. This check consumes the FFXI owner's
corrected pure wrapper and exact native library outside both repositories.
It does not start a server/client, install a navmesh, or satisfy native P0 or
Game QA. Game-coordinate values, owner assets, native source snapshots,
compiled binaries and query receipts remain outside git.

## Executed result

**VERIFIED PASS, 2026-11-15 CST:** the corrected wrapper accepted the exact
owned tile without changing its payload. All **12 retained compatibility cases**
passed, including refusal of the newer backend. **Six focused owner tests**
passed, with one explicitly filtered for the capacity contract described below.
The native owning library then loaded **1 declared / 1 added tile**, returned
valid refs for **46 polygon-centroid nearest queries**, and produced a complete
two-polygon corridor plus a two-point straight path with exact `DT_SUCCESS`.

The resulting MSET SHA256 is
`8902b2221eee618849511def6f9c1cc11a4d0ed86ee70fb3947a95e7c0db7cb1`.
The receipt is
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-owned-native-5c73-20261115-attempt2/result.json`,
SHA256 `2aa4dcfe08bc4da907b72c35aa1955488be344a389acecdaf229fe1a88aed367`.
It records wrapper output, native result, source snapshots, binary hashes,
Cargo lock, commands and logs. The detailed native result and all coordinates
are in its sibling `owned-native-result.json`.

This is a successful offline library consumption check. Native server P0 and
Game QA remain **NOT RUN**; no live installation or full-zone claim follows.

## Verified reuse and second owned crop

**VERIFIED PASS, 2026-11-15 CST:** East Ronfaure zone101's bounded static crop
was consumed with the **same retained wrapper and native executables**, without
compilation or rerunning the owner tests. Its raw tile SHA256 is
`cd23a5b744adab700f75c7061dbce4bdcefca4b5fa8a361bba18ba8bcf12541c`;
the resulting MSET SHA256 is
`1675836890a5cf4234f667c5ea2c8a319f8de8b1b1b24456fc55da262f9ef676`.
All 12 compatibility cases passed, including refusal of the newer producer.
The owning native library loaded 1/1 tile, returned four valid nearest picks,
and completed the selected adjacent-polygon corridor and straight path with
exact `DT_SUCCESS`. The native caller still supplies capacity512.

Fresh evidence:
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi101-native-reuse-5c73-20261115-attempt1/result.json`,
SHA256 `49bf15d909c1c44432c2028b26b2994d3c1e2fee6d9ce6f3efff9514082781c7`.
Its command list contains only `compatibility` and `owned-native`.
`build_run_this_invocation` and `owner_tests_run_this_invocation` are false;
historical source/build/test evidence stays under `reused_harness` rather than
being presented as a new build or test result.

`--reuse-harness` accepts only the original successful receipt pinned to
`2aa4dcfe…`, not arbitrary later receipts and their self-declared hashes. It
verifies the selected owner source/profile and packet, both retained binaries,
the wrapper and native-driver source snapshots, native source manifest, exact
harness Cargo manifest and retained lock. The current driver must still match
the compiled snapshot. Every retained artifact stays inside its receipt tree;
symlink paths are refused. Verified executable bytes are copied to a fresh
private evidence directory and checked before and after dispatch. No retained
build tree is modified or reused as a Cargo target.

Every native crop now requires an explicit `--native-tile-sha256`. The selected
tile must match its bake receipt; the bake must record success and bind the
same OBJ and accepted `d999…` backend hashes. The FFXI sidecar must declare the
single owning-exporter transform, Y-up coordinates, owner provenance and
incomplete coverage. Its concrete provenance artifacts are read and checked
against their hashes. These checks preserve supplied evidence; they do not
independently authenticate ownership or prove physical coordinate calibration.

Ten focused, non-executing guard tests cover valid reuse, modified receipt,
binary/source/lock changes, a changed current driver, symlink/traversal refusal,
explicit crop identity, unsupported backend, unrelated/failed bake and altered
provenance/transform. They use synthetic metadata and never execute a fixture
binary. Receipt:
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-nav-reuse-guards-20261115/result.json`.

## Pins and historical evidence

`scripts/check_ffxi_nav.py` requires an explicit source profile:

| Profile | FFXI source commit | Wrapper SHA256 |
| --- | --- | --- |
| `original-a13` | `a13dabcd550e0a777be5077804ba3d51683cfa19` | `5bf2638184ec007fde180a41f24646687572bb94185684056a7b39ec59c1fd5f` |
| `detail-boundary-5c73` | `5c73a8751940ba767c7b86a50bb96b38b5d1e4f6` | `1cd9c8d9d540c704b84fd9f3c1d7c6006185fd96ea8e7f54cb3c2996456517ad` |

The corrected profile also requires the owner's exact source/test packet:
`/home/blizz/scratch-build/ffxi-detour-detail-boundary-5c73a875-source-test-20261115.tar.gz`,
SHA256 `9f56d53b0053e59a87f1d75186e24d81a1e9fb2cdac2c8bb27cbcf1b7906876d`.
The test source SHA256 is
`52ac48f6be9b3796faeb60f57808b5aa0d55dde34e12a4dcaeb28942c17e84c2`.
The script verifies the packet before compilation and checks its two source
members against the selected immutable git objects. It does not extract the
packet into an owning checkout.

**OBSERVED:** the correction narrowly accepts bounded binary32 rounding at
marked extra detail-boundary vertices. Native layout, convexity, winding,
interior vertices, topology, raw hashes, query bounds and producer constraints
remain in the owner's wrapper. The core harness changes none of those checks
and never snaps, rebuilds or rewrites a tile payload.

The only accepted backend remains
`d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`.
The newer `e2d9…` backend still has an explicit refusal case. Contract source
`ae73…`, retained package source `5e4…`, package manifest and backend build
receipt remain distinct metadata; none authenticates physical calibration.

The exact owned tile is
`4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4`,
at external evidence `ffxi-sandoria230-nav-build0001-compat/region.navtile`.
The original failure remains at
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-nav-compat-20261115-owned/result.json`,
SHA256 `a563ffdf1278b4caeaad3f0dc1271a45d6e8f75d2265eeabd2698e81473898c1`.
Its rejection is historical evidence, not silently replaced by the successor.

## Native binding and coordinate contract

**OBSERVED:** the native source subtree
`server/crates/detour-sys` at the corrected owner commit is git tree
`f60ac5be2549c158730514f004218a168c76f907`. Only that crate's build script,
manifest, Rust/C++ binding and vendored Detour are copied to the external
harness project. The unchanged build script selects Detour `1078bfe3`,
32-bit references, no fast math/FMA contraction and the owner's native filter.
Vendored Detour retains its zlib license; private owner binding source has no
separately declared license in the inspected package manifest.

| Native file relative to `detour-sys` | SHA256 |
| --- | --- |
| `src/lib.rs` | `d79f3dcfa28684a1f158a3877abf5fe8a4d75a748acc1d32dc04613982ca0299` |
| `src/shim.cpp` | `d20f34d795677d1f8415c0c96910bfa05e8344b2a83bdc71f5fd1da65f37889c` |
| `build.rs` | `ca31c2fe9f35b7d7ad85450e8f229c1b11c247ad2f17e9a60c1b285959acf576` |

`detour-sys/src/lib.rs:1` accepts positions in Detour's frame. The owner exporter
already applied `(x,-y,-z)`, matching `xi-map/src/navmesh.rs:50`. The wrapper
and new smoke apply no additional coordinate transform or rescaling.

The original helper `scripts/ffxi_native_driver.rs` revalidates the exact raw
tile using the selected wrapper, compares the resulting MSET to the retained
wrapper output and requires the original raw payload at byte48. It then:

1. Loads the MSET through the exact owning `detour_sys::Mesh` and requires one
   declared tile and one actually added tile.
2. Derives coarse-polygon centroids from the validated bytes, checks each query
   against the wrapper envelope, and asks native Detour for nearest polygons.
   It requires exact success, nonzero valid refs and finite output coordinates.
3. Selects the first actual adjacent pair with distinct native refs, asks for
   a complete corridor, then a straight path. Both require exact `DT_SUCCESS`,
   correct endpoints and finite points. Partial, truncated and exhausted-node
   status flags are failures.

These are mesh-derived library queries, not asserted game waypoints or a
gameplay route. All query positions and raw outcomes are retained externally.

## Capacity finding for the owning lead

**OBSERVED source contract:** at the same pinned commit,
`detour-sys/src/lib.rs:163` allocates `max_path` entries and line172 allocates
`max_straight` entries. The corresponding shim functions at
`detour-sys/src/shim.cpp:155` and line161 do not receive those capacities and
always pass `MAX_NAV_POLYS = 512` to native Detour.

The new helper therefore supplies **exactly 512** to both APIs. This makes the
new call sites consistent with the observed binding contract; it does not
establish general safety of an API accepting smaller caller capacities.
**INFERRED:** an undersized call with a sufficiently long native result could
write beyond the Rust allocation. No undersized call, exploit or crash probe
was executed. The owning lead should reconcile the API capacity contract and
existing tests separately; this task changes no native source.

Follow-up source audit confirms all four direct production calls at
`xi-map/src/navmesh.rs:280,284,340,342` pass `MAX_NAV_POLYS=512` (constant at
line42), matching this contract. The only identified smaller direct calls are
the test calls below, whose fixture has only 1–3 polygons. No actual historical
overwrite is established. This is an API-contract follow-up, not evidence that
the current production call sites use undersized buffers. External call-site
receipt: `evidence/ffxi-detour-capacity-callsites-5c73-20261115/result.json`,
SHA256 `b90ed2665b0656a88840ad370860dbd35ef17d60eed82dfd4a998b642dc8290a`.

The owner's test
`synthetic_mset_loads_exactly_one_tile_and_queries_original_corridor` supplies
capacity16 at `forever-audit/src/detour_mset/tests.rs:141` and line144. It is
explicitly filtered from this local run, without editing its source. The other
six focused owner tests remain selected; the owner's previously reported
seven-test receipt is a separate historical result. Our new owned-tile corridor
smoke uses the 512-capacity contract.

An initial local attempt was stopped while still compiling, before any wrapper,
test or native dispatch, after this source-level test constraint was identified.
Its retained record is
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-owned-native-5c73-20261115-attempt1/ABORTED.json`.

## Reproduction

Run from this repository with a new external evidence directory. Existing
directories refuse overwrite. Native sources and dependencies are built offline
with `nice -n 19`, Cargo locked mode and two jobs; no game server is built.

```sh
python3 scripts/check_ffxi_nav.py \
  --reference-profile detail-boundary-5c73 \
  --source-packet /home/blizz/scratch-build/ffxi-detour-detail-boundary-5c73a875-source-test-20261115.tar.gz \
  --single-dir /home/blizz/.local/share/banshee-bot-core/evidence/build0001-readback/nav-smoke \
  --tiled-dir /home/blizz/.local/share/banshee-bot-core/evidence/tiled-nav-20261115/smoke-v2 \
  --native64-mmtile /home/blizz/.local/share/banshee-bot-core/evidence/nav-preflight-20261115/acore-v20.mmtile \
  --backend-manifest /home/blizz/.local/share/banshee-bot-core/evidence/nav-backend-20261115/build-cmangos-final/manifest.json \
  --owned-case /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-nav-compat-20261115-owned-inputs/build0001.json \
  --owned-case /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-nav-compat-20261115-owned-inputs/build0002.json \
  --native-case owned-ffxi-build0001 \
  --native-tile-sha256 4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4 \
  --evidence /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-owned-native-FRESH
```

For verified reuse, add:

```sh
--reuse-harness /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-owned-native-5c73-20261115-attempt2/result.json
```

To reproduce zone101, replace the build0001 owned-case path with
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-east-ronfaure101-native-inputs-20261115/build0001.json`,
set `--native-case owned-ffxi101-build0001`, and supply the zone101 raw hash above.
Keep the newer-backend refusal case and choose a fresh evidence directory.

To replay the historical pure wrapper, select `original-a13` and omit the packet
and native-case options. The old owned-case failure remains expected historical
behavior; that profile does not acquire the owner's correction automatically.

## Limits

Coverage is still a bounded, incomplete static region. Physical source-unit
calibration, navigation-agent calibration, dynamic doors/platforms/water,
complete-zone connectivity, live native integration, native P0 and Game QA are
unverified. The helper's loader/query evidence must not change the pure wrapper
manifest's own `native_load_or_query_executed: false`; the outer receipt records
those separate executed stages explicitly.
