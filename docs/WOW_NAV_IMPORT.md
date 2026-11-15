# Explicit WoW navigation selections

`scripts/import_wow_nav.py` imports an explicitly selected `.mmap` and one or
more `.mmtile` files into a fresh private directory. It retains the original
files and extracts each exact raw Detour payload through
`bnav-extract extract-mmtile`. It does not rebake, rewrite polygon flags, discover
neighboring files, infer empty cells or declare whole-map coverage.

The successful import status is always `SELECTED_REGION`. Unselected tiles are
unknown. Even a selection containing many files makes no completeness claim.
`game_qa` remains `NOT_RUN`; importer and native diagnostic results do not
establish that bots can safely walk a game map.

## Explicit inputs and profiles

The Python 3.9+ script requires an explicit source profile, map identifier,
map-parameter file, repeated tile filenames, extractor and native backend.
It accepts these existing structural profiles:

| Profile | Wrapper bytes/version | Detour reference width |
|---|---|---|
| `cmangos-v8` | 20 / 8 | 32 |
| `cmangos-v8-ref64` | 20 / 8 | 64 |
| `acore-v20` | 56 / 20 | 64 |

No profile is inferred or retried. Only `cmangos-v8-ref64` permits the exact
`maxPolys=0x80000000` encoding described in [the preflight](WOW_NAV_PREFLIGHT.md).
The native backend must match the selected reference width. The map identifier
is a caller declaration: the binary formats do not authenticate map names or
producer identity. Filename digits are not used to place tiles; the stored
Detour coordinates and bounds must match the supplied map origin and grid.

The retained owner samples documented in the preflight use
`cmangos-v8-ref64`. AzerothCore support here is structural; no actual AzerothCore
artifact has been verified. No download or server startup is needed.

## Import and verify

Choose a new output directory outside every Git checkout. Existing destinations
and outputs inside Git are refused. This example selects only one documented
tile; replace the tool paths with the private binaries being tested:

```sh
python3 scripts/import_wow_nav.py import \
  --profile cmangos-v8-ref64 --map-id 000 \
  --map /home/blizz/scratch/cmangos/release-20261109c/smoke/data/mmaps/000.mmap \
  --tile /home/blizz/scratch/cmangos/release-20261109c/smoke/data/mmaps/0002239.mmtile \
  --extractor /absolute/private/bnav-extract \
  --backend /absolute/private/bnav-recast-ref64 \
  --output-dir /absolute/private/new-wow-selection

python3 scripts/import_wow_nav.py check \
  /absolute/private/new-wow-selection/manifest.json
```

Repeat `--tile` for each file intentionally selected. Bounds are 1–256 selected
tiles, at most 64 MiB per source tile and 256 MiB total source tile bytes. Native
diagnostic allocation also requires the original map's `maxTiles` to be at most
4096; the script never rewrites this capacity. Tiles must use layer 0 and signed
X/Z indices within `-4095..4095`. Per-tile vertical bounds may differ.

The script retains:

- `requested.json`: exact selected source identities, profile, map declaration
  and tool identities before processing.
- `map.mmap`: unchanged 28-byte map parameters.
- `source/NNN.mmtile`: unchanged selected wrapped source tiles, in input order.
- `tiles/NNN.navtile`: byte-exact raw payloads, without the WoW wrapper.
- `receipts/map.json` and `receipts/NNN.json`: actual inspection/extraction
  commands, exit codes and bounded stdout/stderr.
- `manifest.json`: final `SELECTED_REGION` or `INCOMPLETE` receipt, source/output
  SHA-256 values, inspected parameters and per-tile counts.

The tile metadata includes stored coordinates, bounds, dimensions, liquid
declaration, polygon/vertex/off-mesh counts, and histograms of original polygon
flags, areas and types. These are observations of the retained payload, not a
translation into game movement policy. All payload bytes are preserved.

Input and tool hashes are checked before and after import. Errors retain partial
output, mark unresolved entries missing, leave an incomplete final manifest and
return 3. An interrupted process can leave only the request and partial files;
that is not a valid selection. Invalid arguments or failed checks return 2.
Success returns 0. The script does not overwrite or delete retained files.

`check` needs only the retained directory. It verifies the request inventory,
all file hashes and extraction receipts, exact source-to-payload equality,
profile/ABI, map placement and unique coordinates. A missing selected tile is
an error. It recomputes flag/area/off-mesh counts from the retained bytes.
Manifest and file hashes detect accidental changes, not an author rewriting
every record: these receipts are not signatures.

## Query with explicit flag policy

Queries require the same backend binary hash recorded by the import and explicit
decimal 16-bit include/exclude masks. At least one included bit must remain after
exclusion. The tool supplies these masks unchanged to Detour; it assigns no game
meaning to them. Choose masks with the owning server lead's movement policy.
Positions are already in the source Detour coordinate system, in X/Y/Z order.

```sh
python3 scripts/import_wow_nav.py query \
  /absolute/private/new-wow-selection/manifest.json \
  --backend /absolute/private/bnav-recast-ref64 \
  --include-flags 1 --exclude-flags 0 \
  --start START_X START_Y START_Z --end END_X END_Y END_Z
```

Every retained file is checked before invoking native `query-map`; the selection
and backend are checked again afterward. The native query loads only the
selected raw tiles against the unchanged map parameters. It rejects endpoints
whose X/Z cell is not selected, mismatched placement or ABI, duplicates, and
incomplete paths. It does not substitute missing neighboring tiles.

`SELECTED_REGION_PROJECTED_PATH` reports a path between the native projected
endpoints, which may differ from requested positions. The diagnostic uses
nearest-polygon extents `[2, 4, 2]`, at most 2048 search nodes and at most 256
corridor polygons/straight-path points. Returned native data includes requested
and projected endpoints, flags, loaded/traversed tile counts and
`whole_map_coverage: false`. The result remains an offline diagnostic, not a
server movement command or a real-client QA result.

The wrapper also returns `route_metrics` for the serialized polyline. Add
`--max-projection-distance DISTANCE` to bound the larger of the two 3D endpoint
projection distances. Exceeding the limit returns `PROJECTION_LIMIT_EXCEEDED`
with exit 3 while retaining the native result and measurements. Omission leaves
the policy unassessed and preserves the existing success status. Invalid limits
fail before invoking the backend. See [projection policy](NAV_ROUTE_METRICS.md).

Use the tool with the owner's retained sources and matching private backend.
Structural wrapper checks are not a general hostile-binary validator; the
native loader adds polygon/index/link checks before query allocation and use.
All map files, tiles, receipts and extracted data stay outside Git. The format
provenance and source licences are recorded in [PROVENANCE.md](PROVENANCE.md)
and the preflight; the importer implementation is original.

## Focused verification

VERIFIED, 2026-11-15 02:33 CST: retained map `509.mmap` and explicitly selected
`5094627.mmtile` / `5094628.mmtile` imported without changing the source files'
hashes or modification times. `check` passed, and a native ref64 query with
include mask 1 / exclude mask 0 traversed both tiles across their shared portal.
The query loaded two tiles and returned a two-polygon corridor between projected
endpoints. Different per-tile Y minima were preserved.

The same focused run rejected a different backend, an entirely excluded flag
policy, an endpoint in an unselected cell, an altered retained payload, and a
tile paired with another map's origin/grid. The mismatched import retained an
incomplete manifest, which `check` rejected. Six stdlib tests additionally cover
explicit ABI selection, nonzero-origin placement, metadata/receipt integrity,
duplicate coordinates and preserved area/flag/type/liquid observations.

Evidence is external:

```text
~/.local/share/banshee-bot-core/evidence/wow-import-20261115-0234/result.json
~/.local/share/banshee-bot-core/evidence/wow-import-20261115-0234/selected-509/
~/.local/share/banshee-bot-core/evidence/wow-query-20261115/source-anchors.json
```

The receipt pins the script, extractor, native backend, source hashes and actual
commands. Source anchors came from the selected tiles' polygon/detail data;
they are not gameplay observations. Whole-map coverage, live server loading and
real-client movement remain unverified. No feature was enabled or deployed.
