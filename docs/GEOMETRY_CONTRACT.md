# Geometry intake v1

This is the common input contract for the shared builder. Reusable per-game
extraction tooling belongs here; native adapter changes and deployment belong
to each server lead. No game geometry is included here. A source
inventory or successfully parsed OBJ is not a walkable map or a QA pass.

## Export

Export one bounded zone region as triangulated UTF-8 OBJ. Use finite `v x y z`
positions and triangular `f` faces with valid vertex indices. Faces may use
positive or negative OBJ vertex indices; export vertices before their faces.
Material files are not loaded. Choose winding so walkable top surfaces have
upward normals. Supply collision geometry, not merely render meshes or a list
of object placements. Include transforms of placed instances and any relevant
terrain, interiors, walls, ramps and ceilings.

Before using the backend, transform the source into **Y-up** coordinates and
declare the physical length represented by one unit. Cell size/height, agent
height/radius, climb and all query coordinates must use that same unit. A
coordinate-axis flip may reverse winding; the extractor must correct it.
The core never guesses a game's axis, scale or handedness from its filename.

Keep the OBJ and a sidecar manifest together under the private data/evidence
root. At minimum the sidecar records:

| Field | Required evidence |
| --- | --- |
| Game / server lane / zone / region | Owning lead and stable zone identity; distinguish different instances and floors. |
| Source identity | Owner-supplied asset path and SHA-256; source build/version if known. No credentials or account data. |
| Extraction | Tool revision, invocation, source format/version and output SHA-256. |
| Coordinates | Source axes/units, applied transform, output Y-up units, bounds and winding convention. |
| Coverage | Included and missing terrain/collision/interiors; list omissions explicitly. |
| Navigation policy | Agent dimensions, climb/slope, cell settings, water policy and intended game adapter. |
| Format confidence | OBSERVED declarations or REA evidence IDs; label inferences and unresolved fields. |

Unknown DAT/sqpack/archive/collision structures require the REA workflow, with
evidence retained outside git. Existing documented source readers should be
reused with pinned provenance rather than guessed from file extensions. Proprietary
inputs remain private; this contract does not authorize a new asset download.

## Bake and acceptance

The backend targets bounded ground geometry, with single-tile and explicit
fixed-grid tiled modes. Synthetic cross-tile routes pass, but this does not
establish complete game-world coverage, doors/lifts, dynamic
obstacles, liquid traversal, off-mesh links or free-space flight. Preserve
Earth & Beyond's owning decision: its 02:26 CST report now requires per-tile
Recast output, with obstacle/gate graphs supplemental. Ground polygons alone
still do not establish calibrated 3D ship movement or native-game acceptance.

A tile candidate needs both a reproducible build and a matching native Detour
reload/query. Record dependency revision, reference width/ABI, tool and output
hashes, build settings and region bounds. Use named path pairs demonstrating
walkable areas and blocked/disconnected areas. A partial path must never be
reported as complete arrival.

The [named offline probe runner](NAV_ROUTE_PROBES.md) can bind a bounded set of
route expectations to an exact collection or selected-map manifest, with
explicit projection limits and retained command receipts. Native query errors
remain errors; the runner does not infer that a failed query proves a blocked
route. Wall-ray observations and projection refusals retain their narrower
offline meaning.

Record both requested and projected endpoint coordinates, their 3D separation,
and the returned path length. Collection/import queries provide these as
[`route_metrics`](NAV_ROUTE_METRICS.md), with an optional caller-selected
projection limit. A complete projected path alone does not establish arrival at
the requested point; source-unit tolerances still require owning-game calibration.

The owning game adapter then maps these queries to its existing in-process
movement validation. Game QA checks walls, floors, ramps/stairs, narrow passages,
zone transitions and representative failure cases on the real server/client.
Only that evidence can upgrade a zone's walking-map coverage or enable a bot
feature. Missing or unavailable pathing must fail closed; it does not authorize
straight-line movement through obstacles.

## Current missing extractors

- FFXI: a [pinned-source bounded export](FFXI_EXPORT.md) and
  [zone230 offline bake](FFXI_REGION_BAKE.md) now succeed. Physical calibration,
  complete collision coverage and native/Game QA remain pending; cached safety
  tables are not substitutes for those checks.
- FF14: client files are not available yet. Lumina-documented sqpack formats are
  a future source, not a prerequisite for C1 or the common builder.
- WoW: existing mmaps can be inspected under explicit profiles. Rebuilding or
  deploying them requires the owning lead's source/ABI and geometry evidence.
- Other games: route the maps-first intakes already listed in
  [BOT-READINESS.md](BOT-READINESS.md); preserve each lane's existing holds.
