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
  --evidence /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-owned-native-FRESH
```

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
