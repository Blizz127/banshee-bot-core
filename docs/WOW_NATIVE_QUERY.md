# Selected WoW tile native query diagnostic

`bnav-recast query-map` loads an explicitly selected set of trusted owner
navigation tiles using the original map parameters. It is an offline diagnostic
with explicit producer profile, reference ABI and terrain flags. A successful
route covers its snapped endpoints within the selected tiles; it does not prove
whole-map coverage, player walkability or native game-server compatibility.

```text
bnav-recast query-map PROFILE MAP_PARAMS INCLUDE_FLAGS EXCLUDE_FLAGS sx sy sz ex ey ez RAW_TILE...
```

`PROFILE` is `cmangos-v8`, `cmangos-v8-ref64` or `acore-v20`. The first requires
a 32-bit helper; the other two require a 64-bit helper. The raw tile inputs must
first be extracted under the same explicit wrapper profile with
`bnav-extract extract-mmtile PROFILE INPUT OUTPUT`. This native command cannot
authenticate a raw tile's producer because its game wrapper is absent. Pair it
with the source/output hash receipts from the import wrapper.

`MAP_PARAMS` is the original 28-byte little-endian `dtNavMeshParams` file.
Its origin, tile dimensions and capacity fields are used unchanged. Only the
explicit cMaNGOS ref64 profile permits the observed `maxPolys=0x80000000`
encoding documented in [the artifact preflight](WOW_NAV_PREFLIGHT.md).
Native Detour uses fixed 64-bit reference fields in that configuration; the
diagnostic does not turn that serialized field into a huge allocation.

The existing `query` and `query-tiles` modes retain their generated-geometry
contracts. In particular, `query-tiles` still requires common vertical bounds
and agent settings. Imported tiles may have different vertical extents;
`query-map` checks their horizontal grid against the original map parameters.
No coordinate, polygon, area, terrain flag or off-mesh record is repaired or
rewritten on disk. Detour reconstructs runtime links and performs its usual
endpoint projection in memory.

## Terrain policy and source pins

The cMaNGOS source defines ground, steep ground, water and magma/slime as flag
bits `1`, `2`, `4` and `8`, respectively. Its ground/water path-finder branch
includes `5` and excludes `10`; other native branches select flags according
to movement capability. This diagnostic has no character movement model, so
callers must provide both masks explicitly.

`INCLUDE_FLAGS` is a decimal integer in `1..65535`; `EXCLUDE_FLAGS` is in
`0..65535`. A policy that excludes every included bit is refused. The original
polygon flag values are passed to `dtQueryFilter`; areas are retained and keep
Detour's default costs. This does not adopt FFXI flag semantics or change any
FFXI adapter guard.

Read-only source references in the owner's cMaNGOS checkout:

- `src/game/MotionGenerators/MoveMapSharedDefines.h`: terrain areas/flag bits.
- `src/game/MotionGenerators/PathFinder.cpp`: native filter selection.
- `src/game/MotionGenerators/MoveMap.cpp`: reads original map parameters,
  then passes raw payloads to `dtNavMesh::addTile`.
- `dep/recastnavigation/Detour/Include/DetourNavMesh.h`: native sections and
  fixed 64-bit reference fields.
- `dep/recastnavigation/Detour/Source/DetourNavMesh.cpp`: pointer/index use,
  native link construction and nearest-polygon behavior.

Exact revisions, hashes and line evidence are retained externally beside the
query receipts. Native source is zlib licensed; cMaNGOS motion-generator
sources carry GPL-2.0-or-later notices. These files were studied read-only;
the validation and orchestration code here is original.

Both helpers can be built from the same owner dependency tree with explicit
`scripts/build_bnav_backend.py --reference-bits 32` or `--reference-bits 64`.
The 64-bit option defines `DT_POLYREF64`, matching the owning cMaNGOS CMake
configuration. The build script pins source hashes and checks the binary's
reported ABI before writing the manifest. The 32-bit default is retained for
existing generated-tile consumers, including the separate FFXI intake.

## Bounds and failure behavior

The imported diagnostic is limited to:

- 1–1024 selected raw tiles, at most 64 MiB each and 256 MiB total.
- Original map capacity of 1–4096 tiles; a larger map is refused without
  silently shrinking or rewriting its parameter file.
- Map tile dimensions of 1–10,000,000 world units, finite coordinates within
  ±10,000,000, tile indices from −4095 to 4095 and layer zero.
- 2,048 query nodes, a 256-polygon corridor and 256 straight-path points.
  Endpoint search extents are `[2, 4, 2]` in the original Y-up Detour units.

Tile bounds must agree with the original horizontal map grid within the larger
of `0.00001` world units or `0.00001` of a tile dimension. This is a comparison
tolerance for stored floating-point values, not a geometry correction. Requested
endpoint grid cells must be in the selected set before projection is attempted.

Before loading, the bridge checks complete section sizes against its own ABI,
positive link storage, finite coordinates/settings, polygon type/vertex counts,
polygon vertex and neighbor indices, portal side encodings, detail ranges and
triangle-local indices, BV leaf/escape indices and off-mesh polygon/side/radius
fields. Serialized runtime links are not trusted or followed; native Detour
rebuilds them. These checks do not constitute a complete geometric/topological
validator or an untrusted-input server loader.

Duplicates, missing requested endpoint tiles, structural failures, ABI/policy
mismatches and incomplete/budget-exhausted paths return exit 2 with an error on
stderr. They do not print a successful route. All source files remain unchanged.

Successful JSON includes `scope="selected-tiles"`, `whole_map_coverage=false`,
profile/reference width, include/exclude masks, loaded/traversed tile counts,
requested and snapped endpoints, corridor size and path points. `complete=true`
refers only to the bounded route between snapped endpoints. The direct-ray
diagnostic is separate from corridor completion and does not certify height or
game collision behavior.

## Focused retained-sample verification

The two retained map-509 samples identified in the external receipts share a
ground portal and have different vertical bounds. Route anchors are derived
from original ground polygon interiors and their detail triangles. A separate
ground component without external portals supplies the disconnected case.
Both samples contain no off-mesh connections, so successful traversal of such a
connection remains untested by this sample.

Raw coordinates, extracted payloads, negative-control copies and source-anchor
evidence remain under:

```text
~/.local/share/banshee-bot-core/evidence/wow-query-20261115/
```

The focused smoke uses an explicitly selected Rust CLI, 64-bit native helper
and data root. It derives anchors from pinned original polygons/detail triangles
and writes their coordinates only to the external receipt. It checks a route across the real shared
boundary, reversed travel, missing and disconnected cases, terrain-policy
refusals, structural negative controls, and source/binary hash readback. It can
also take the 32-bit helper to check the explicit ABI refusal. No server/client
is launched and no game data enters Git.

```sh
python3 crates/bnav-extract/tests/smoke_wow_query.py \
  --bnav /path/to/bnav-extract \
  --backend /path/to/bnav-recast-ref64 \
  --backend32 /path/to/bnav-recast-ref32 \
  --data-root /home/blizz/scratch/cmangos/release-20261109c/smoke/data/mmaps \
  --evidence-dir /home/blizz/.local/share/banshee-bot-core/evidence/new-wow-query
```

**VERIFIED, 2026-11-15 02:34 CST — PASS:** the 64-bit helper passes all 19
focused smoke outcomes, including exact payload extraction, forward/reverse
routes traversing two tiles and two polygons, and expected refusal reasons for
the missing, disconnected, flag and malformed cases. The three source inputs,
extracted payloads and binaries retain their original hashes after execution.
The sample has ground and steep-ground flags; water-only selection correctly
finds no eligible starting polygon.

Evidence: `smoke64-v2/query-receipt.json` under the directory above, SHA256
`e297499cd8fcd3b554aae74291d82d91ce65228d775378fe9ff9cfbbeae237fd`.
The separate import wrapper's nine-command receipt at
`~/.local/share/banshee-bot-core/evidence/wow-import-20261115-0234/result.json`
also passes its actual selected-set import/check/query and refusal checks.

The native bridge source SHA256 is
`82a3313a50637579ad31602ccde9936f17d9411cb680157031c444d2d1218a47`.
The 64-bit helper SHA256 is
`87282847e04e34d06503e9286809826c87fdb5bb16724ab01c269c8a89ae6a3a`;
its source/ABI/compiler manifest and retained licence are in `backend64-v1/`.

**VERIFIED, 02:35 CST:** the matching 32-bit helper builds and refuses the
explicit ref64 import before loading. Because `query_mesh` is shared, one
existing single-tile query and one existing tiled query were rerun with the new
32-bit helper; both JSON results match their previous receipts exactly. No
geometry bake or broad suite was repeated. The helper SHA256 is
`5e985f81e4f1656cca47c072671e6148a134af0d8c750db82c9d6da091805815`;
its manifest/licence are in `backend32-v1/`, and the three-command receipt is
`ref32-compatibility.json`.

These outcomes are native offline diagnostics only. Game QA, whole-region
coverage, historical extraction provenance and any C0 score change remain
outside this increment.
