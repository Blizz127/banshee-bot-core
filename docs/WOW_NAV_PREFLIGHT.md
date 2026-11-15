# Owner WoW navigation artifact preflight

**2026-11-15, CST — PARTIAL:** two retained cMaNGOS map/tile pairs exposed a
missing explicit 64-bit v8 profile. Their payloads passed the packaged raw64
inspector. The correction adds that profile while preserving the existing
strict defaults. No AzerothCore artifact was located in the bounded documented
locations. This is header/section-size evidence, not walking-map QA, a native
server load test, an extraction receipt or a C0 score upgrade.

## Sample identity and original result

**OBSERVED:** the owning project's README and
`/home/blizz/scratch/cmangos/navmesh-coverage-20261115/coverage.py:20` identify
the retained data directory:

```text
/home/blizz/scratch/cmangos/release-20261109c/smoke/data/mmaps
```

Only these four navigation artifacts were sampled. They were not modified. No server or
client was launched, and no data was added to Git.

| File | Bytes | SHA256 |
|---|---:|---|
| `000.mmap` | 28 | `5bfae4cd801172511a7cb76fe64fed4df7814afa4bf97c6e3d214e2da1152609` |
| `0002239.mmtile` | 109128 | `26084d182f4cf1053f6007a0bff645fdfcb273287883616f54825ec7c5181776` |
| `509.mmap` | 28 | `fd0aa67e62541bb9f1bc3259c5bc60a0f6e97594091dba3aad42975f7d7de528` |
| `5094627.mmtile` | 353612 | `80557e38c00386dde3e48ee04fff5a9a5bb9c33fe792d1467dd21c96abaf02ae` |

The build0002 packaged `bnav-extract` has SHA256
`186c3f1c5f8de156cf1959422e9b5a427b40f8d0edd469f66de8b7b7154528bd`.
Its original results are retained, including every command and error:

- `inspect-mmap PATH` rejects both maps with `invalid maximum polygon count`.
  Each stores raw `maxPolys=0x80000000`, signed `-2147483648`.
- `inspect-mmtile cmangos-v8 PATH` rejects both tiles because the payload size
  disagrees with its explicitly selected 32-bit reference layout.
- Each tile has the documented 20-byte v8 wrapper and Detour version 7. The
  exact payload, saved only in the external evidence directory, passes
  `inspect-detour 64` and fails `inspect-detour 32`.

| Tile | Payload bytes | Polygons | Vertices | Detour tile coordinates |
|---|---:|---:|---:|---|
| `0002239.mmtile` | 109108 | 673 | 741 | `[5, 39, 0]` |
| `5094627.mmtile` | 353592 | 1996 | 2490 | `[3, 7, 0]` |

The selected tile bounds agree with each corresponding map origin and grid
size within `0.001` cell. This is placement consistency, not connectivity.
The filename's map identifier is still external association metadata; neither
format independently authenticates the producer or map identity.

## Why this is a separate profile

**OBSERVED source facts:** cMaNGOS checkout
`aa539d47fa00640d77408402ba3e7aeb193c8c91` has clean inspected source files.
Its native server/extractor build enables `DT_POLYREF64` through CMake, even
though the define is commented out in the standalone Detour header:

| Source | Relevant fact | SHA256 |
|---|---|---|
| `contrib/mmap/CMakeLists.txt:20` | Extractor defines `DT_POLYREF64` | `a6d6824639c5c6a18736e10618be7c7f4c095a2e044fe4f2df8e16d9ac2d8987` |
| `dep/recastnavigation/CMakeLists.txt:21` | Server/extractor dependency build defines it | `b1032f9ddf1738cfd6046a505733ab548c41dde139aaf5ae93b5a0ec0b882864` |
| `contrib/mmap/src/MapBuilder.cpp:684` | Writes `1 << DT_POLY_BITS` to `maxPolys` | `80ac2aecd8d38cdd2718ae6dfaa645cf0f8e371c1d9a783dfed40e5289e7ddb0` |
| `dep/recastnavigation/Detour/Include/DetourNavMesh.h:43` | Fixed 12 salt / 21 tile / 31 polygon bits with 64-bit references | `26c4268830b800659798a3e652b3a5f89b0c7eaffc141306dec4fec960bec481` |
| `src/game/MotionGenerators/MoveMapSharedDefines.h` | Wrapper version 8, 20 bytes | `7994c9cbb53c81bc30b92b71201e17081040e5988c0e54d9425e0746dec7fd16` |

`DetourNavMesh.h:531` and `:547` encode/decode the fixed bit fields. In
`DetourNavMesh.cpp:254`, derivation of reference bits from the signed
`maxPolys` field is compiled only for the 32-bit build; the corresponding
per-tile dynamic bit-count check at `:918` is also excluded for ref64.
`dtNavMeshParams::maxPolys` remains a signed `int` in the serialized layout.
Thus the observed bit pattern represents this generator's fixed 31-bit
capacity; it does not authorize treating arbitrary negative counts as valid.

**INFERRED:** these artifact layouts agree with the pinned producer's 64-bit
configuration. Exact historical extractor inputs, build and generation flags
are still not established by this sample. The existing owner live-content
comparison receipt is referenced for provenance only; this task did not repeat
live inspection.

The standalone Banshee cMaNGOS helper in build0002 remains **32-bit**: its
direct compiler invocation does not inherit the owning project's CMake
defines. Its previous synthetic checks remain valid. A shared dependency
source tree does not imply that two binaries use the same reference ABI.

## Explicit inspection interface

```sh
bnav-extract inspect-mmap cmangos-v8-ref64 /path/to/000.mmap
bnav-extract inspect-mmtile cmangos-v8-ref64 /path/to/0002239.mmtile
```

The new profile selects a 20-byte v8 wrapper with 64-bit Detour section sizes.
Its map-parameter mode permits exactly `0x80000000` in addition to ordinary
positive signed counts, reports `max_polygons_semantics=fixed-31bit-capacity`
for that bit pattern, and checks the fixed 21-bit tile capacity. It does not
allocate a navmesh, infer ABI from filenames or silently retry another profile.

`inspect-mmap PATH` and `cmangos-v8` retain their existing behavior.
`acore-v20` still selects a different 56-byte wrapper and does not acquire the
cMaNGOS-specific map-field exception. Header output continues to say
`producer_identity=unverified`; tile output leaves connectivity/walkability
unverified.

To repeat the focused retained-sample check with an explicitly selected binary
and a new external receipt directory:

```sh
python3 crates/bnav-extract/tests/smoke_wow_profiles.py \
  --bnav /path/to/bnav-extract \
  --data-root /home/blizz/scratch/cmangos/release-20261109c/smoke/data/mmaps \
  --evidence-dir /home/blizz/.local/share/banshee-bot-core/evidence/new-wow-preflight
```

This receipt script pins the four sample hashes above; it is a focused
regression check, not a scanner for arbitrary game data.

## Evidence and remaining work

All receipts and diagnostic payloads are outside Git:

```text
~/.local/share/banshee-bot-core/evidence/wow-nav-preflight-20261115/
  artifact-receipt.json       original packaged failures and raw64 passes
  source-receipt.json         source pins and path-provenance file hashes
  pair-grid-receipt.json      corresponding map/tile placement checks
  acore-availability.json     bounded lookup and missing-volume observations
  correction-build.json      focused Rust parser tests and build
  corrected-samples/          corrected inspector results and source readback
```

The original receipt preserves the packaged binary identity and before/after
source hashes. The corrected-sample receipt pins the new binary separately.
Focused parser checks cover all explicit wrapper profiles, opposite reference
widths, version/length failures, the exact cMaNGOS capacity exception and
rejection of other negative/zero counts or excessive fixed tile counts.

**VERIFIED, 02:18 CST:** six Rust parser tests and the build passed; the
corrected inspector passed all ten expected command outcomes on both actual
retained pairs, including legacy strict refusals. All four input hashes and
mtimes remained unchanged, and both placement checks passed. The tested debug
binary SHA256 is
`40c8cd95b74f673f7370c5bfaba58820fa82886c193dd23f3012b5ebef5142a9`;
the corrected-sample receipt SHA256 is
`b256e2f5b3dd5fdefc50f754cdc28f46d4623cc3b6374dca8e2e548f7769b079`.
The later HELP-only wording correction for the separate FFXI export wrapper
does not change these parser results; packaged build0003 gets its own receipt.

**OBSERVED AzerothCore availability:** the reference checkout at
`/home/blizz/dev/wow/ref/azerothcore-playerbot` remains at
`47960183bb03b83e8943eb2f0f39c16df9710c9d`; `MapDefines.h` selects v20 and the
Detour header selects ref64. Its `data/` contains only SQL. The owning
`/home/blizz/dev/wow/wotlk-solo/docker-compose.yml` names `ac-client-data`;
the expected `wotlk-solo_ac-client-data` volume was absent, and filtered volume
and container listings on the current daemon found no matching resources.
This limited search does not prove the artifacts are absent elsewhere. An
owning lead's exact retained data path is needed before an actual v20 sample
can be checked; no download, broad filesystem scan or runtime launch occurred.

Next correction: obtain that specific AzerothCore artifact path and generation
receipt, then run the explicit existing profile. Native loader/path tests,
game geometry coverage and Game QA remain separate work.

Source licences: the cMaNGOS CMake extractor file grants unrestricted copying
with its notice retained; its dependency CMake and MapBuilder/wrapper sources
carry GPL-2.0-or-later notices. Detour source carries the zlib licence. These
files were studied read-only; all inspector and receipt code here is original.
