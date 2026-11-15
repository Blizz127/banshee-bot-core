# Native navigation ABI verification — 2026-11-15

**VERIFIED: both selected 32-bit and 64-bit Detour reference builds pass the
synthetic single-tile and fixed-grid tile bake/reload/query checks.** This is
offline tool evidence, not live-world compatibility, per-zone map coverage or
Game QA. Selecting the wrong reference width remains an error even though both
formats advertise Detour version 7.

| Reference ABI | External dependency | Original helper SHA-256 | Evidence |
| --- | --- | --- | --- |
| 32-bit | cMaNGOS `dep/recastnavigation`, parent `8a40e8411877051d3b940a8284d6e4792339de0d` | `e2d9f815d5354fc3612f4498ae424c76ef4ff461af3ad8fe293eb9ffb5c85818` | `~/.local/share/banshee-bot-core/evidence/tiled-nav-20261115/` |
| 64-bit | AzerothCore playerbot `deps/recastnavigation`, parent `47960183bb03b83e8943eb2f0f39c16df9710c9d`, header defines `DT_POLYREF64` | `b32097eb8e9205ee51b1738129a15e4ffe8cad211d2ad61a4576ee76a725fcfb` | `~/.local/share/banshee-bot-core/evidence/nav-abi64-20261115/` |

The 64-bit helper was built by the integrated root's
`scripts/build_bnav_backend.py` with two low-priority compiler jobs. The original
bridge source at root and the isolated tool-check worktree matched SHA-256
`007eddf4fc345561b8076cc9246e74d5659aed2db441f88343d7d1108dde6fbf`.
The shared Rust CLI and both smoke scripts also matched; `source-match.json`
records their hashes. No external repository or runtime was modified.

The `backend-acore/` directory contains `bnav-recast`, `manifest.json`, compiler
and linker records, and `RECAST-LICENSE.txt`. The manifest pins every external
source/header plus the original bridge and records source stability throughout
compilation. Recast/Detour is the external zlib-licensed dependency; it was not
copied into this repository.

## Focused results

The 64-bit `single-smoke/result.json` and `tiled-smoke/result.json`, together
with their `commands.json` files, record successful floor bake and Detour reload,
complete obstacle-avoiding paths, disconnected-route rejection, wrong-ABI
rejection, invalid configuration/grid checks, explicit empty cells and output
overwrite refusal. The tiled floor route traversed two tiles. A wall across
the seam forced a route through `[20, 0.2, 16]`; its direct ray was blocked.
Missing endpoint tiles, duplicate tile coordinates and mismatched grid origins
were refused. No test invokes a game server.

The earlier 32-bit results were reused without rerunning them for this ABI
task. Their `single-tile-compatibility.json` proves the original build 0001
floor, wall and disconnected raw tile outputs remained byte-identical after
adding tiled support. Tile byte hashes differ between reference ABIs; they are
not interchangeable files or adapter capabilities.

The FFXI owner adapter intake `a13dabcd` remains explicitly single-tile and
32-bit. This broader shared tool check neither modifies that contract nor
authorizes its use of 64-bit references or multi-tile portal topology.

## Configured versus serialized vertical bounds

The builder's initial heightfield interval is:

```text
MIN_Y - CELL_HEIGHT
MAX_Y + HEIGHT + CLIMB + CELL_HEIGHT
```

Both selected Recast versions then add `walkableHeight * CELL_HEIGHT` to the
compact heightfield's upper Y bound, where
`walkableHeight = ceil(HEIGHT / CELL_HEIGHT)` is evaluated from float32 values.
That enlarged bound propagates into the saved Detour header. Manifest validators
must distinguish this serialized bound from the initial configured interval.

Source observations: cMaNGOS `Recast/Source/Recast.cpp:423`; AzerothCore
`Recast/Source/Recast.cpp:435`. `vertical-bounds.json` records the exact float32
calculation against an already produced 32-bit tile. With `MIN_Y=0`, `MAX_Y=3`,
`HEIGHT=2`, `CLIMB=0.9`, `CELL_HEIGHT=0.2`, configured upper Y is
`6.099999904632568` and serialized upper Y is `8.100000381469727`.
This metadata clarification requires no native behavior change.

Real game geometry correctness, coordinate calibration, collection completeness,
native adapter compatibility and actual-client QA remain separate requirements.
