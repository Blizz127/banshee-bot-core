# Fixed-grid Recast tiles

This tool increment builds separate raw Detour tiles on an explicit common grid
and diagnoses routes across their native portal connections. It does not change
the existing single-tile `build-obj` contract. The current FFXI owning-lead
adapter intake accepts single tiles only; it does **not** accept these nonzero
tile coordinates or portal topology. No game integration is implied.

## One grid cell

```text
bnav-extract build-tile-obj BACKEND INPUT OUTPUT \
  ORIGIN_X ORIGIN_Z MIN_Y MAX_Y TILE_CELLS TILE_X TILE_Z \
  [CELL_SIZE CELL_HEIGHT HEIGHT RADIUS CLIMB SLOPE]
```

The optional six settings retain `build-obj` defaults, `0.3 0.2 2.0 0.6 0.9 45`.
These are demo settings, not calibrated game dimensions. Input must be validated
Y-up triangulated geometry with declared world units. Every tile of a collection
uses the same input/source identity, vertical bounds and settings.

`TILE_CELLS` is an integer from 8 through 1024. `TILE_X` and `TILE_Z` are integers
from 0 through 4095; negative coordinates are represented by a negative world
origin, not a negative tile index. The unpadded tile square is:

```text
world_side = TILE_CELLS * CELL_SIZE
x = ORIGIN_X + TILE_X * world_side .. ORIGIN_X + (TILE_X + 1) * world_side
z = ORIGIN_Z + TILE_Z * world_side .. ORIGIN_Z + (TILE_Z + 1) * world_side
```

The vertical interval must contain the supplied geometry's entire Y bounds.
Recast receives `[MIN_Y - CELL_HEIGHT, MAX_Y + HEIGHT + CLIMB + CELL_HEIGHT]`.
All tiles keep that same vertical interval; different per-tile extrema would
change quantization and prevent a coherent collection.
Recast's compact heightfield extends the serialized upper Y bound by another
`ceil(HEIGHT / CELL_HEIGHT) * CELL_HEIGHT`; the collection validator accounts
for this headroom. It is padding, not an additional collision surface.

Each tile rasterizes a border of `ceil(RADIUS / CELL_SIZE) + 3` cells on every
horizontal side. The border participates in clearance filtering and erosion;
region/contour construction removes it and marks native boundary portals. The
saved tile header records `(TILE_X, TILE_Z, layer 0)` and the unpadded bounds.
Tile coordinates are not inferred from filenames.

This implementation rasterizes the full supplied mesh for each cell. It is a
bounded correctness foundation, not an accelerated whole-world extractor.
Existing one-million vertex/triangle, four-million horizontal cell, vertical
heightfield and 64 MiB output limits still apply to each padded tile. A wide
agent radius can make an otherwise valid tile exceed those limits.

Exit status **0** means a nonempty raw Detour tile was built and reloaded.
Status **3** means no walkable polygons remain in that cell under the chosen
filters; no file is created. It does not mean the source region contains no
collision geometry. Status **2** means failure, including invalid settings or
output already existing. Neither failure nor an absent file can be silently
converted into an empty-cell declaration. All outputs use create-new semantics.

## Native collection query

```text
bnav-recast query-tiles ORIGIN_X ORIGIN_Y ORIGIN_Z TILE_WORLD \
  START_X START_Y START_Z END_X END_Y END_Z TILE_FILE...
```

Use `ORIGIN_Y = MIN_Y - CELL_HEIGHT` and `TILE_WORLD = TILE_CELLS * CELL_SIZE`.
The diagnostic accepts 1 through 1024 loaded tile files, at most 256 MiB total.
It rejects incorrect native reference ABI/section lengths, duplicate tile
coordinates, nonzero layers, grid/bounds disagreements and mixed agent/vertical
settings. It initializes one Detour navmesh and adds the tiles so native portal
connections can form. No custom polygon or link representation is substituted.

The query's input is an explicit list of trusted helper-produced files. It
cannot know whether an omitted tile was never built, lost, or intentionally
empty. A caller must first verify a complete collection manifest, including a
built/empty entry for **every** requested grid cell and hash/size checks for all
built files. Partial/missing/failed collections are not valid map coverage.
The higher-level collection orchestrator owns that evidence and completeness
check; this native diagnostic alone makes no collection-completeness claim.

Endpoints are projected using the existing `[2,4,2]` nearby-polygon extents in
world units. `complete` means the snapped endpoint polygons are connected by a
complete corridor within the bounded query resources. The result also records
`loaded_tiles` and the number of distinct `traversed_tiles`. A truncated path,
disconnected endpoint or exhausted node/path budget fails. The direct ray and
straight path describe navigation geometry, not exact game physics.

## Provenance and validation

The original bridge uses the already documented external Recast/Detour APIs.
The [upstream tiled sample](https://github.com/recastnavigation/recastnavigation/blob/main/RecastDemo/Source/Sample_TileMesh.cpp)
was consulted for border/portal API usage; its zlib licence is recorded with the
dependency. No upstream sample implementation was copied. Local dependency
source hashes and the compiled bridge hash are retained in the backend build
manifest produced by `scripts/build_bnav_backend.py`.

Focused smoke entry point:

```text
python3 crates/bnav-extract/tests/smoke_tiled.py \
  --extractor /absolute/path/to/bnav-extract \
  --backend /absolute/path/to/bnav-recast \
  --output-dir /absolute/private/path/to/fresh-smoke
```

The smoke covers a straight route crossing a seam, a wall intersecting the seam
that forces a detour, disconnected floors, a missing endpoint tile, duplicate
tiles, incorrect grid origin, explicit empty cells, invalid grid/settings,
clipped vertical bounds and overwrite protection. All fixtures are synthetic.
Actual game geometry, per-zone coverage and Game QA remain separate acceptance
work; no live server is touched by these commands.

**VERIFIED, 2026-11-15 02:04 CST:** the 32-bit cMaNGOS dependency build passes
that smoke. The floor corridor traverses two native tiles; the seam-wall route
passes through `[20, 0.2, 16]` instead of crossing the wall. The previous
single-tile smoke also passes, and its floor/wall/disconnected raw tile SHA-256
values are byte-identical to build 0001.

Evidence: `~/.local/share/banshee-bot-core/evidence/tiled-nav-20261115/smoke-v2/`
and `single-compat-v2/`. Backend and input-source manifest are in `backend-v2/`;
backend SHA-256 is
`e2d9f815d5354fc3612f4498ae424c76ef4ff461af3ad8fe293eb9ffb5c85818`.
An initial source-changing compile correctly refused publishable status; its
output was retained and a fresh stable compile supplied this verified backend.
The 64-bit collection pipeline and real-game integration have not been run.
