# bnav-extract groundwork — 2026-11-15 (CST)

This increment provides input preflight and an offline **single-tile
Recast/Detour builder** for already extracted, triangulated OBJ geometry. It
establishes explicit WoW format profiles and a canonical triangle input. It has
no external Rust dependencies. The optional native backend links explicitly
selected external Recast/Detour sources; it does not contact a server or read
external materials referenced by OBJ files.

```sh
cargo run -p bnav-extract -- --help
cargo run -p bnav-extract -- inspect-mmap /path/to/000.mmap
cargo run -p bnav-extract -- inspect-mmtile cmangos-v8 /path/to/tile.mmtile
cargo run -p bnav-extract -- inspect-mmap cmangos-v8-ref64 /path/to/000.mmap
cargo run -p bnav-extract -- inspect-mmtile cmangos-v8-ref64 /path/to/tile.mmtile
cargo run -p bnav-extract -- inspect-mmtile acore-v20 /path/to/tile.mmtile
cargo run -p bnav-extract -- check-obj /path/to/triangulated.obj
cargo run -p bnav-extract -- inspect-detour 32 /path/to/generated.navtile
```

Inputs are capped at 64 MiB by the CLI. Inspection is read-only. `build-obj`
creates a new file and refuses to overwrite any existing output. Errors return
status 2. Do not put game inputs in this repo.

## Supported evidence

| Input | What is checked | What a success does not establish |
|---|---|---|
| `.mmap` | Exact 28-byte little-endian `dtNavMeshParams`, finite origin and positive dimensions/counts | Producer identity: this format has no magic/version; tile coverage or path validity |
| `cmangos-v8` `.mmtile` | 20-byte v8 wrapper, Detour v7 header, 32-bit reference ABI, declared payload and section lengths, finite ordered bounds/counts | Polygon indices, adjacency, off-mesh links, connectivity, walkability or loaded-server compatibility |
| `cmangos-v8-ref64` `.mmtile` | Same 20-byte v8 wrapper with explicitly selected 64-bit reference ABI | Same limitations; a v8 wrapper alone does not identify its reference width |
| Explicit `cmangos-v8-ref64` `.mmap` | Ordinary strict map fields, plus the pinned producer's exact `maxPolys=0x80000000` fixed 31-bit capacity encoding and 21-bit tile capacity | Producer identity, extraction provenance or native load/path validity; no arbitrary negative count acceptance |
| `acore-v20` `.mmtile` | 56-byte v20 wrapper, Detour v7 header, 64-bit reference ABI, declared payload and section lengths, finite recorded config/bounds/counts | Same limitations; matching the intended Recast generation settings is also not checked |
| Raw Detour tile | Detour v7 header and section lengths for explicitly selected 32/64-bit references | Polygon adjacency, walkability or loaded-server compatibility |
| Triangulated OBJ | Finite vertices, in-range face indices, nondegenerate triangles, bounds | Units, handedness, up-axis, winding correctness, collision completeness or walkability |

OBJ accepts `v x y z` and triangular `f` records, including negative indices and
vertex/texture/normal face notation. Only the vertex indices are consumed.
Object/group/smoothing/material/normal/texture records are ignored; materials
are never loaded. Quads, general polygons, free-form surfaces, forward vertex
references and homogeneous vertices fail explicitly. Coordinates remain
unchanged. The game geometry extractor must supply a declared coordinate
convention before anything is passed to Recast.

An unknown mmap version is not assumed equivalent to these versions, even if
its file length looks familiar. Other architectures, endian layouts, modified
Detour structures and reference-width combinations need separate profiles.
No source assets or extracted meshes are bundled with this increment.

Actual owner cMaNGOS v8 samples use 64-bit references because the owning build
enables `DT_POLYREF64` through CMake. Their map parameters also use the fixed
31-bit polygon-capacity encoding accepted only by the explicit new profile.
See [the WoW artifact preflight](WOW_NAV_PREFLIGHT.md) for the original packaged
failures, source pins and focused correction checks. The standalone Banshee
cMaNGOS helper remains 32-bit; its direct compile does not inherit those CMake
flags.

## Build and query extracted geometry

Compile the native dependency and the original Banshee bridge in a new external
output directory. The script defaults to two low-priority compiler jobs, hashes
all dependency sources/headers and the bridge, checks that those sources remain
unchanged through compilation, and retains `manifest.json` plus the external
dependency's `RECAST-LICENSE.txt` alongside the binary.

```sh
python3 scripts/build_bnav_backend.py \
  --recast-root /home/blizz/dev/cmangos-classic/mangos-classic/dep/recastnavigation \
  --output-dir /home/blizz/.local/share/banshee-bot-core/builds/recast-example \
  --jobs 2

cargo run -p bnav-extract -- build-obj \
  /home/blizz/.local/share/banshee-bot-core/builds/recast-example/bnav-recast \
  /path/to/triangulated.obj /path/to/new-output.navtile

/home/blizz/.local/share/banshee-bot-core/builds/recast-example/bnav-recast \
  query /path/to/new-output.navtile 2 0 10 18 0 10
```

`build-obj` requires Y-up geometry with upward-facing floor triangles; it performs
no coordinate or unit conversion. Agent dimensions and voxel sizes are in the
same world units as the geometry. The six optional positional settings are
`CELL_SIZE CELL_HEIGHT AGENT_HEIGHT AGENT_RADIUS AGENT_CLIMB MAX_SLOPE_DEGREES`;
defaults are `0.3 0.2 2.0 0.6 0.9 45`. These are synthetic demo settings, **not
per-game calibrated values**. All six must be supplied together when changing
them. Height must cover at least three vertical voxels. Finite positive cell
sizes/height and nonnegative radius/climb are required; slope is below 90 degrees.

The backend rasterizes triangles, filters low clearance/ledges, builds and
erodes a compact heightfield, constructs regions/contours/polygons/detail meshes,
and serializes using `dtCreateNavMeshData`. It reloads the result through Detour
before returning it. Rust validates the returned header/section sizes and strips
the private IPC envelope before saving. The saved `.navtile` is actual raw
Detour v7 data, with **no custom navmesh container and no WoW mmap wrapper**.
The matching dependency reference ABI (32 or 64 bits) must accompany the tile.

Only query tiles produced by this helper with the matching backend ABI. The
query command is a local diagnostic, not a loader for arbitrary untrusted tiles.
It projects endpoints to nearby polygons using extents `[2,4,2]`, rejects an
incomplete path or exhausted query budget, and reports the resulting straight
path plus whether the direct ray was obstructed. A success describes the
**projected endpoints**; it does not prove reachability at the exact input height.

Limits are deliberate: at most one million vertices and triangles, dimensions
below 4,096 cells per horizontal axis and four million horizontal cells, 8,191
vertical cells, fewer than 65,535 polygon vertices, and 64 MiB serialized output.
Smaller disconnected regions may be removed by the fixed region thresholds
(minimum area 64 cells, merge area 400). Large maps need tiling; off-mesh
connections, area costs, doors, water rules and cross-tile stitching are pending.
Native memory depends on vertical geometry complexity as well as grid size.

## Geometry adapter seam

`TriangleMesh` is the input boundary: a per-game reader must return validated
vertices/triangles in a declared common coordinate system before entering this
pipeline. The synthetic floor/obstacle tests establish this backend seam, not
the correctness or completeness of any game's geometry extractor.

Recast/Detour sources already present locally, available for a standalone build
without editing their owning repositories:

- `/home/blizz/dev/cmangos-classic/mangos-classic/dep/recastnavigation/` —
  `Recast/Source`, `Recast/Include`, `Detour/Source`, `Detour/Include`.
  Default Detour polygon references are 32-bit.
- `/home/blizz/dev/wow/ref/azerothcore-playerbot/deps/recastnavigation/` — same
  directories, with 64-bit Detour polygon references enabled in the header.

Those sources are third-party zlib-licensed dependencies, not original Banshee
code. They are not vendored into this repository. Their parent CMake files are
integrated into the game builds; the standalone Banshee script uses a separate
output directory and source manifest without changing those projects.

Bounded FFXI export uses a separate [pinned-source offline wrapper](FFXI_EXPORT.md).
An in-process FFXI DAT reader, FFXIV sqpack reader and game walking-map QA remain
pending.
No unknown geometry format was interpreted in this increment. Unknown format
investigation must use REA under the governing instructions and retain evidence
under `~/.local/share/banshee-bot-core/evidence/`. FF14 client files are still not
an input or dependency for this phase.

## Source provenance

Format facts were inspected, and all Rust/parser/fixture code was written here.
No upstream implementation code was copied. These entries should also be listed
in the integrator's `docs/PROVENANCE.md`.

| Reference | Licence | Observed source identity |
|---|---|---|
| [cMaNGOS wrapper declarations](https://github.com/cmangos/mangos-classic/blob/master/src/game/MotionGenerators/MoveMapSharedDefines.h) | GPL-2.0-or-later | Local repo HEAD `8a40e8411877051d3b940a8284d6e4792339de0d`; `MoveMapSharedDefines.h` SHA256 `7994c9cbb53c81bc30b92b71201e17081040e5988c0e54d9425e0746dec7fd16` |
| [AzerothCore wrapper declarations](https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/common/Collision/Maps/MapDefines.h) | GPL-2.0-or-later | Local playerbot checkout HEAD `47960183bb03b83e8943eb2f0f39c16df9710c9d`; `MapDefines.h` SHA256 `ce27c387563bfc942c4434705f4a97da5e7e214df4c2bce41765b32f4e9d5608` |
| [Detour structures](https://github.com/recastnavigation/recastnavigation/blob/main/Detour/Include/DetourNavMesh.h) and `DetourNavMeshBuilder.cpp` allocation layout | zlib | cMaNGOS `DetourNavMesh.h` SHA256 `26c4268830b800659798a3e652b3a5f89b0c7eaffc141306dec4fec960bec481`; AzerothCore header SHA256 `201732481a638843164065b8fde938621c3e9d44fe1e067dc1cc5f602c4fbf18` |

The web references establish upstream provenance; the local hashes above pin
the layouts actually inspected. Local headers are not a claim about the exact
version deployed on any server.

## Focused verification

- **VERIFIED:** four Rust tests cover version/ABI/length disagreement, truncated
  and malformed headers, non-finite fields, invalid OBJ indices and degenerate
  geometry. `nice -n 19 cargo test -j2 --manifest-path
  crates/bnav-extract/Cargo.toml` passed on 2026-11-15, 01:07 CST.
- **OBSERVED:** startup help and geometry smoke results, plus native Detour
  synthetic fixture compatibility, are retained in
  `~/.local/share/banshee-bot-core/evidence/nav-preflight-20261115/`.
- `crates/bnav-extract/tests/native_fixture.cpp` is an original optional manual
  fixture generator, compiled against each external source tree. It creates a
  synthetic square using upstream `dtCreateNavMeshData`; it contains no game
  data and is not a geometry-to-Recast builder. Generated fixtures stay outside
  git. It checks the chosen profile's actual `sizeof(dtPolyRef)` before writing.
- **VERIFIED (2026-11-15, 01:14 CST):** the native backend built against the
  cMaNGOS dependency and passed synthetic floor bake/reload/direct path, wall
  avoidance with a complete five-point detour, and disconnected-floor rejection.
  Oversized grids, zero cell size, non-finite height, negative radius, wrong
  reference ABI and output overwrite attempts were rejected. The overwrite
  check also verified the original tile's SHA256 remained unchanged. The focused
  smoke is reproducible with `crates/bnav-extract/tests/smoke_backend.py`.
  Retained evidence:
  `~/.local/share/banshee-bot-core/evidence/nav-backend-20261115/smoke-final/result.json`
  and `commands.json`. Native helper SHA256:
  `d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`.
  Build manifest and third-party licence are in
  `~/.local/share/banshee-bot-core/evidence/nav-backend-20261115/build-cmangos-final/`.
  Only this 32-bit-reference backend was exercised through the full Recast
  pipeline; the earlier fixture compatibility check covered both wrapper ABIs.
- **Not run:** real game geometry extraction, a live-world map query, Game QA,
  game stairs/obstacles/zone transitions or deployment. Existing live WoW coverage
  reports are useful readiness evidence, but were not a local map test here.
