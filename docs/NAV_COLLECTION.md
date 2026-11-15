# Bounded navmesh collections

`scripts/bake_nav_collection.py` evaluates an explicitly bounded X/Z grid using
`bnav-extract build-tile-obj` and the private Recast backend. The JSON collection
manifest records real raw Detour tiles; it is not a new navigation binary format.
Python 3.9+ and the matching extractor/backend binaries are required.

The collection layer checks input, tool, receipt and output SHA-256 values,
requested tile coverage, tile coordinates, agent dimensions, bounds and Detour
reference ABI. A successful collection means every **requested cell** was baked
or explicitly reported empty. It does not prove the input contains every zone
surface, that a route is safe in the game, or that a game adapter can load it.
Collections remain `game_qa: NOT_RUN` and
`native_adapter_compatibility: NOT_VERIFIED`.

## Geometry sidecar

Supply an external JSON sidecar alongside the external OBJ. No game geometry,
binary tools or generated tiles belong in Git. For example, a synthetic fixture
uses this schema (replace the digest with the actual OBJ SHA-256):

```json
{
  "format": "bnav-geometry-v1",
  "game": "synthetic",
  "zone": "two-tile-wall",
  "geometry": {
    "path": "wall.obj",
    "sha256": "REPLACE_WITH_64_LOWERCASE_HEX_DIGITS"
  },
  "coordinates": {
    "up_axis": "Y",
    "units": "metres",
    "transform": "identity; synthetic Y-up geometry"
  },
  "coverage": {
    "scope": "40 by 20 metre synthetic floor with a seam wall",
    "limitations": ["No game data or gameplay verification"]
  },
  "provenance": {
    "classification": "synthetic",
    "description": "Original smoke fixture generated outside Git",
    "artifacts": []
  }
}
```

`geometry.path` can be absolute or relative to the sidecar. The OBJ hash is
verified before baking and again afterward. `game`, `zone`, units, transform,
coverage scope and limitations are required declarations. Geometry must already
be transformed to Y-up; this tool does not transform it. State uncalibrated units,
missing collision classes, selected regions and other limitations explicitly.

`provenance.classification` accepts `synthetic` or `owner_asset`. Classification
is a caller declaration, not validation of ownership, permission or provenance.
Optional `artifacts` records contain `path` and `sha256` for upstream source
artifacts. They are retained as declarations, without opening those artifacts.

## Bake, check and query

Use fresh paths under `~/.local/share/banshee-bot-core/`; existing output
directories and paths inside any Git checkout are refused. The tool neither
overwrites nor deletes collections. These commands use explicit private tool
paths, with an illustrative source sidecar and fresh destination:

```sh
python3 scripts/bake_nav_collection.py bake \
  --source /absolute/private/source.json \
  --extractor /absolute/private/bnav-extract \
  --backend /absolute/private/bnav-recast \
  --output-dir /absolute/private/new-collection \
  --origin-x 0 --origin-z 0 --min-y 0 --max-y 3 \
  --tile-cells 40 --x-min 0 --x-max 2 --z-min 0 --z-max 0 \
  --settings 0.5 0.2 2 0.6 0.9 45

python3 scripts/bake_nav_collection.py check \
  /absolute/private/new-collection/manifest.json

python3 scripts/bake_nav_collection.py query \
  /absolute/private/new-collection/manifest.json \
  --backend /absolute/private/bnav-recast \
  --start 2 0 10 --end 38 0 10
```

The six settings are cell size, cell height, agent height, radius, climb and
maximum slope in degrees. Defaults are `0.3 0.2 2 0.6 0.9 45`. All dimensions use
the input's declared units. Every tile uses identical origin and settings. Tile
world width is `tile_cells * cell_size`; bounds are inclusive tile indices with
at most 256 requested cells. Tile indices are `0..4095`, tile width is `8..1024`
cells, the OBJ limit is 64 MiB, and total tile bytes cannot exceed 256 MiB.

`min_y` and `max_y` must contain the entire supplied geometry's Y range. Preserve
the actual lower Y bound: native query origin Y is `min_y - cell_height`. Recast
input Y padding runs from that lower value through
`max_y + agent_height + agent_climb + cell_height`. Recast's compact heightfield
also extends its upper Y bound by `ceil(agent_height / cell_height) * cell_height`;
the collection checks the resulting serialized header with float32 tolerance.
This upper padding does not imply extra collision geometry.

## Retained records and failure behavior

- `source.json` is the byte-exact input sidecar.
- `requested.json` records the original incomplete grid before processing.
- `tiles/X_Z.navtile` contains each built raw Detour tile.
- `receipts/X_Z.json` records the actual build command, exit code and bounded
  stdout/stderr for each completed invocation.
- `manifest.json` is the final receipt: `COMPLETE` or `INCOMPLETE`, explicit
  `built`/`empty`/`missing` cells, hashes, settings, declarations and errors.

An empty result requires native exit code 3 and no tile file. It remains an
explicit cell, including its command receipt. Any other failed invocation stops
the bake, retains partial output and writes an incomplete manifest; the wrapper
returns 3. Interrupted processes may leave only `requested.json` and partial
records; these cannot pass `check`. Invalid arguments or verification failures
return 2. A query that exceeds an explicit endpoint projection limit returns 3
with status `PROJECTION_LIMIT_EXCEEDED`. Successful bake/check/query returns 0. An entirely empty collection
can pass `check`, but cannot produce a navigation query.

`check` requires every cell, matching command receipts and hashes, no unexpected
output for empty cells, no file escape from the collection, supported raw header
layout and matching bounds/agent settings/ABI. It does not need the original OBJ
or tools to remain present. Collections can therefore move intact to another
private directory. Hashes detect accidental changes; the manifest is not a
signature or protection against an author rewriting all records.

`query` validates an optional projection limit before any backend invocation,
then performs `check` and requires the explicitly supplied backend's
recorded binary hash and reference width, then queries all built tiles together.
It checks the collection and backend again afterward. Missing or corrupt tiles,
incomplete inventories, mismatched grids and different backends fail closed.
The native loader performs additional tile validation. Use collections generated
by this tool and the matching private backend; header checks are not a general
validator for arbitrary hostile Detour payloads.

`COMPLETE_PROJECTED_PATH` means the native corridor reaches the projected
endpoint. Native nearest-polygon search uses fixed `[2, 4, 2]` extents; returned
points can differ from the requested position and height. This is an offline
navigation diagnostic, not approval to move a character. The current single-tile
FFXI consumer rejects tiled coordinates/portals and needs an owning-lead change
before collection integration.

Every successful native query also includes `route_metrics`: requested and
reported endpoints, both projection distances, path length, endpoint separation
and corridor size. Add `--max-projection-distance DISTANCE` to require both
reported endpoints to fall within that 3D distance of their requested positions.
Omitting the option preserves the previous success status and leaves
`within_projection_limit` null. See [projection policy](NAV_ROUTE_METRICS.md)
for rounding, units, result validation and exit semantics.

## Focused evidence

VERIFIED, 2026-11-15 CST: an original external floor/wall fixture produced two
built tiles and one explicit empty cell. The complete collection passed `check`;
a query crossed two tiles and routed around the wall. Focused stdlib tests cover
malformed metadata, missing/duplicate cells, hashes and receipts, empty outputs,
and raw header grid/settings/ABI mismatches.

Evidence: `~/.local/share/banshee-bot-core/evidence/nav-collection-20261115/`.
The initial failed collection is retained; the corrected `collection-2/` is the
successful smoke. `validation.json` records final script/tool/manifest hashes
and command results. Synthetic fixtures only; real-map completeness, in-game
behavior and game-adapter compatibility have not been verified.
