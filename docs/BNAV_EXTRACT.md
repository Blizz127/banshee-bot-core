# bnav-extract groundwork — 2026-11-15 (CST)

This first increment is a read-only input preflight, **not yet a navmesh builder**.
It establishes explicit WoW format profiles and a canonical triangle input for
the future Recast backend. It has no external Rust dependencies and does not
contact a server or read external materials referenced by OBJ files.

```sh
cargo run -p bnav-extract -- --help
cargo run -p bnav-extract -- inspect-mmap /path/to/000.mmap
cargo run -p bnav-extract -- inspect-mmtile cmangos-v8 /path/to/tile.mmtile
cargo run -p bnav-extract -- inspect-mmtile acore-v20 /path/to/tile.mmtile
cargo run -p bnav-extract -- check-obj /path/to/triangulated.obj
```

Inputs are capped at 64 MiB by the CLI. Files are opened read-only; all output is
on stdout/stderr. Errors return status 2. Do not put game inputs in this repo.

## Supported evidence

| Input | What is checked | What a success does not establish |
|---|---|---|
| `.mmap` | Exact 28-byte little-endian `dtNavMeshParams`, finite origin and positive dimensions/counts | Producer identity: this format has no magic/version; tile coverage or path validity |
| `cmangos-v8` `.mmtile` | 20-byte v8 wrapper, Detour v7 header, 32-bit reference ABI, declared payload and section lengths, finite ordered bounds/counts | Polygon indices, adjacency, off-mesh links, connectivity, walkability or loaded-server compatibility |
| `acore-v20` `.mmtile` | 56-byte v20 wrapper, Detour v7 header, 64-bit reference ABI, declared payload and section lengths, finite recorded config/bounds/counts | Same limitations; matching the intended Recast generation settings is also not checked |
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

## Next implementation seam

`TriangleMesh` is the input boundary: a per-game reader returns validated
vertices/triangles in a declared common coordinate system. An original native
bridge can pass that mesh through Recast rasterization, walkability filters,
compact heightfield, erosion, region/contour/polygon/detail construction and
`dtCreateNavMeshData`. The backend must then reload its result through Detour
and query across obstacles before claiming a usable map.

Recast/Detour sources already present locally, available for a standalone build
without editing their owning repositories:

- `/home/blizz/dev/cmangos-classic/mangos-classic/dep/recastnavigation/` —
  `Recast/Source`, `Recast/Include`, `Detour/Source`, `Detour/Include`.
  Default Detour polygon references are 32-bit.
- `/home/blizz/dev/wow/ref/azerothcore-playerbot/deps/recastnavigation/` — same
  directories, with 64-bit Detour polygon references enabled in the header.

Those sources are third-party zlib-licensed dependencies, not original Banshee
code. They are not vendored into this repository. Their parent CMake files are
integrated into the game builds; a Banshee backend should use a separate output
directory, an explicit dependency revision and its own narrow build recipe.

FFXI DAT and FFXIV sqpack readers and geometry-to-Recast generation are pending.
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
- **Not run:** real game geometry extraction, a live-world map query, Game QA,
  stairs/obstacles/zone transitions or deployment. Existing live WoW coverage
  reports are useful readiness evidence, but were not a local map test here.
