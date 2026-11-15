# Offline FFXI geometry export

`scripts/export_ffxi_geometry.py` and `scripts/ffxi_geometry_driver.rs` are
original Banshee entry points around the owning FFXI project's existing reader
and bounded exporter. They do not implement a DAT decoder. Select one zone ID,
its expected source-backed DAT path and an explicit source-space AABB. The
documented selections include East Ronfaure (101) and Southern San d'Oria (230).
They build and run offline, without starting a client or server.
Python 3.11+, the Rust toolchain and already cached pinned Cargo dependencies
are required. Future invocations record compiler/Cargo versions, wrapper hash
and CST build time; the retained initial export predates those metadata fields.

## Source and data boundaries

The script reads git objects at owning FFXI commit
`a13dabcd550e0a777be5077804ba3d51683cfa19`. It stages `forever-audit`,
`forever-safety`, `ffxi-dat`, and the `detour-sys` dev-dependency, plus the original
lockfile and `ffxi_check/data/oplen.json`, in a fresh private output directory.
Original crate files remain unchanged. A new minimal workspace manifest and the
original Banshee driver are added only there. The owning checkout is never
modified, built in, switched or used as a target directory.

Cargo reduces the copied lockfile offline; every resulting registry package's
name, version, source and checksum must occur in the original lockfile. The
subsequent driver-only build is `--offline --locked` with `nice -n 19` and one
compiler by default. Missing cached dependencies fail; the script never fetches
them. Staging `detour-sys` satisfies Cargo's path resolution; it is a
dev-dependency and is not part of the normal driver build.

The existing reader attributes its code to MIT-licensed `forever-client` commit
`a8c75ab4e981d6056cd2860d8f8e12eacfff7671`. Its exact licence is retained in the
private output. The owning FFXI workspace declares no blanket licence; this
script does not invent one. See [the source audit](FFXI_GEOMETRY_EVIDENCE.md).

After build/startup success, the script snapshots only `FFXiMain.dll`, available
ROM index table files, and the explicitly selected expected DAT. Each file is
bounded to 64 MiB, copied once with SHA256, and checked for changes during the
copy. The existing `Client` resolves the chosen zone against those snapshot tables; a
path other than the explicitly staged selection refuses extraction. No all-zone
loader or runtime Lua export is used. These assets remain beneath
`~/.local/share/banshee-bot-core/`, outside git.

The output directory also contains private source snapshots, assets and compiler
artifacts: **do not publish or package the directory as a release**. Packaging
the original scripts does not require bundling these private dependencies.

## Invocation

This bounded candidate surrounds the existing source homepoint fixture
`(-85.554, 1, -64.554)`. The region and unit assumption are explicit experiment
inputs, not proven gameplay bounds or calibrated dimensions:

```sh
python3 scripts/export_ffxi_geometry.py \
  --ffxi-source /home/blizz/dev/ffxi-platform \
  --forever-client-source /home/blizz/dev/forever-client \
  --client-root '/home/blizz/dev/ffxi/client-dat/full-1.2.2/FINAL FANTASY XI' \
  --output-dir /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-region-NEW \
  --zone-id 230 --zone-name "Southern San d'Oria" \
  --region-name 'bounded homepoint-source region' \
  --expected-asset-relative ROM/1/31.DAT \
  --bounds-min -110 -10 -90 --bounds-max -60 12 -40 \
  --metres-per-unit-assumption 1 \
  --format-evidence 'Existing pinned forever-audit reader source and its attributed format evidence; see docs/FFXI_GEOMETRY_EVIDENCE.md' \
  --jobs 1
```

The output directory must not exist. A failed attempt is retained for diagnosis;
the script never replaces or deletes previous evidence. Any ancestor `.git`
directory or worktree marker refuses output, including worktrees under the
private data root. The script verifies original/staged driver bytes and staged
external source digests after compilation before labelling the binary. Input bounds use FFXI's
source `(x,y,z)` frame, where Y points down. The original owning exporter selects
whole triangles intersecting the AABB, applies `(x,-y,-z)` once, and aligns winding
to transformed stored normals. Output triangles can extend beyond the requested
AABB; use `actual_output_bounds` for a bake. Do not transform the OBJ again.

`--metres-per-unit-assumption` satisfies the exporter's explicit declaration
contract. It does **not** scale coordinates or establish physical calibration.
The resulting sidecar labels it uncalibrated. Navigation cell/agent settings
must use the emitted source world units and remain separate experiment inputs.

The four selection arguments are now required: `--zone-id`, `--zone-name`,
`--region-name` and `--expected-asset-relative`. The names are caller declarations.
The expected path is normalized, relative, traversal-free, and ends in `.DAT`.
It is not derived from the zone ID. The existing owning reader must resolve the
zone to exactly that path before loading its collision. Neither a filename guess
nor a whole-client zone scan is used. Source tests at the pinned revision record
101 → `ROM/0/121.DAT` and 230 → `ROM/1/31.DAT`; other selections need their own
source and region evidence.

## Reusing an immutable retained driver build

Add `--reuse-build` pointing at an original successful build directory, for example
`~/.local/share/banshee-bot-core/evidence/ffxi-sandoria230-export-20261115-02`.
The script independently reads the pinned owning git objects and licence, then
checks the retained source/build manifests, complete source inventory, every
staged source file, reduced lockfile, original/staged driver and actual binary.
A different current driver, changed executable, missing/changed source record,
revision mismatch, changed lock, or path escaping the retained build refuses
reuse. The original build must be beneath the private data root and outside Git.

Only the verified executable and licence are copied to the fresh output. The
executable is hashed again after startup and export. `source-reference.json`
records the retained manifest paths and hashes, source revision, archive hash
and verified source count, and explicitly states `source_snapshots_copied: false`.
The new `build-manifest.json` labels its mode `retained_build_reuse` and makes no
new compilation claim. There is no dependency resolution or compiler invocation
in this path. A reused output lacks a source snapshot and is deliberately not a
replacement original build for another `--reuse-build` call.

Omit `--reuse-build` for the original fresh, offline, low-concurrency build path.
Both paths retain the same private-output, no-overwrite, source identity, water,
calibration and collision-coverage checks. These are local provenance consistency
checks, not signed compiler attestations or gameplay verification.

## Outputs and refusal behavior

On success, `geometry.json` is the `bnav-geometry-v1` input sidecar accepted by
`bake_nav_collection.py`. It identifies the exact `region.obj` SHA256, Y-up
coordinates, source units, transform, coverage limitations and provenance
artifacts. Additional evidence includes:

- `source-identity.json` for fresh builds, or `source-reference.json` for verified
  reuse: exact source provenance without claiming absent snapshots were copied.
- `build-manifest.json`: driver binary/source hashes and exact reduced lock hash.
- `owned-inputs.json`: original paths, snapshot paths, byte counts and SHA256.
- `request.json`: exact region, units and format-evidence declaration.
- `raw-observation.json`: resolved path, decoded counts, kinds and diagnostics.
- `export-manifest.json`: owning exporter's exact counts, bounds and omissions.
- `startup` and `export` JSON/log pairs: commands and exit codes; fresh builds
  additionally retain `resolve` and `build` pairs.

The owning exporter rejects any selected type-9 water bed, instead of silently
dropping it or treating water as ordinary ground. It rejects invalid geometry,
normals, mismatched arrays, ambiguous winding, empty selection and resource
limits. It validates the entire decoded `Raw`, even triangles outside the
selected region. The wrapper does not remove triangles to evade these checks.

The output remains incomplete: RID door boxes, dynamic doors, lifts, moving
platforms and object bookkeeping are absent from `Raw`. The existing reader can
skip malformed records and repair normals; successful decoding/export does not
certify source completeness. Other surface-kind semantics and navigation agent
dimensions remain unverified. No generated OBJ is admission of a complete zone,
no server behavior changes, and no C1 or Game QA result follows from this tool.

## Evidence classification

The earlier FFXI-lane REA startup failure in the source audit was a technical
failure without recorded session identity or owner permission denial. The root
integrator subsequently observed a healthy current REA session and retained
owned-DAT identity evidence
`ev_c7170dcd8779c2dca79420f4553dd40d08163c4824357bf5299e7897933fa2d6` in
`~/.local/share/banshee-bot-core/evidence/rea-owned-dat-20261115/bundle.json`.
That establishes identity only, not binary-format semantics. This driver uses
the existing documented reader; it performs no unknown-format or key research,
does not invoke REA/Ghidra, and does not repair MCP/runtime configuration.

## 2026-11-15 CST bounded export result

**VERIFIED:** offline pinned driver build, startup help, original/staged source
identity, and the nav collection sidecar/OBJ hash contract. The first staging
attempt `ffxi-sandoria230-export-20261115-01` refused the unadjusted workspace
lockfile before any asset snapshot or extraction; its failure receipt is kept.
The corrected offline resolution preserves all registry package identities from
the owning lock. No native `detour-sys` build was needed.

**OBSERVED:** attempt
`~/.local/share/banshee-bot-core/evidence/ffxi-sandoria230-export-20261115-02/`
decoded the exact selected DAT and exported the requested source AABB
`[-110,-10,-90]` through `[-60,12,-40]` successfully:

| Measurement | Result |
| --- | --- |
| Input DAT | `ROM/1/31.DAT`, SHA256 `4d17ce938e53da7a075d985aba5902723527884b6a86fd2046e90ea232e91433` |
| Decoded `Raw` | 106,462 triangles, 400 × 400 grid, matching normal/kind/flag counts, zero degenerate triangles |
| Selected output | 1,821 triangles, 5,463 vertices, 261,651 OBJ bytes |
| Water | All 16 decoded type-9 faces lie outside the selected region; none selected or silently dropped |
| Selected kinds | 0:61, 2:76, 5:1,469, 6:31, 7:184; semantics beyond the documented water refusal are not certified |
| Winding | All 1,821 output faces reversed to align with the transformed original stored normal |
| Actual Y-up bounds | `[-114.1289978,-2,34.6699982]` through `[-58.6599998,11.6000004,74.6699982]` |
| Source fixture after transform | `(-85.554,-1,64.554)`; no new runtime fixture check |
| Omitted outside-region `Raw` | 104,641 triangles; missing source collision count remains unknown |

`region.obj` SHA256:
`df8acf8bbb3f16386d07e4ad5d595dce12f432d220ca4b0e20d5b0d87fa1685a`.
`geometry.json` SHA256:
`2d666d9698de1755be8b751e4fac8f5f98072a58062aacd1b2ec2d0a8fcf6396`.
`export-manifest.json` SHA256:
`70a3a1765ea31a81671154467dcfed0665e969bffc7c2e0fd34bc203ad156051`.

The original driver SHA256 is
`13f4aee4b62a197dd54f825915ae07cc339e43ab1f6443dfc62fa51d1256cd4d`;
the offline debug driver binary SHA256 is
`4f097f2cc391db43a03685c07923748705507e2057fa8a9b9e02c17662134c27`.
`post-build-identity-check.json` verifies that run's original/staged driver,
binary, and 62 staged source files. The final wrapper's automatic post-build
checks and general Git-ancestor guard were added while this run was already in
progress, so the same identities were checked independently afterward rather
than misreporting those final wrapper branches as executed. Its Python syntax,
help, existing-directory refusal and sibling Git-worktree refusal were checked
separately. `sidecar-validation.json` records the exact nav collection validator
digest and successful sidecar/hash check without writing to its source tree.

**Not run:** a mesh bake by this exporter, native adapter query, game runtime or
Game QA. No completeness, physical calibration or navigation coverage upgrade
is claimed. The whole-triangle output exceeds the requested bounds; any later
grid that clips it at the requested outer region has less padding there and
must report that loss separately.

## 2026-11-15 CST zone selection and retained-build reuse result

**VERIFIED:** ten focused synthetic tests cover exact relative paths and retained
binary, driver, source inventory, source bytes, revision and lock integrity.
Run `python3 -B scripts/tests/test_ffxi_geometry_export.py`. The Rust driver was
unchanged, retaining SHA256
`13f4aee4b62a197dd54f825915ae07cc339e43ab1f6443dfc62fa51d1256cd4d`.
The actual new export verified and reused the original Southern San d'Oria
build above; it created neither an `external-source` tree nor a `cargo-target`.
The fresh build path remains available; it was not recompiled in this increment.

The new region comes from historical source evidence at the same FFXI pin:
`reports/2026-11-06-spawn-audit/points.tsv:621` records East Ronfaure zone 101,
`(176,-20.002,-240)`, `PASS/ok`, ground delta `-0.00`, originating at
`scripts/globals/unity.lua:21`. That report's SHA256 is
`1faec81dbc44a330a6fb9f11ee9b25d7aed98cfb9065c1aac5a5e46e3e6f6bcf`.
Its README defines the ground/water checks and excludes doors, subareas, moving
platforms and server clamping. This is historical point evidence, not a fresh
game observation or a certificate that a surrounding area is dry. The earlier
open-field probe `(86.131,-65.817,273.861)` is historically a `DROP`; it was not
used as the new standing fixture.

The explicit experiment used:

```text
--zone-id 101 --zone-name 'East Ronfaure'
--region-name 'unity destination historical PASS point, experimental surrounding crop'
--expected-asset-relative ROM/0/121.DAT
--reuse-build /home/blizz/.local/share/banshee-bot-core/evidence/ffxi-sandoria230-export-20261115-02
--bounds-min 166 -30.002 -250 --bounds-max 186 -10.002 -230
--metres-per-unit-assumption 1
```

**OBSERVED:** new output is
`~/.local/share/banshee-bot-core/evidence/ffxi-east-ronfaure101-export-20261115-01/`.
It resolved the exact expected path with DAT SHA256
`003e17cffcb940c88a015dbf02a56256507ef978cefa183e757ee93446dde488`.
The decoder returned 385,748 triangles, a 440 × 400 grid, and no degenerate
triangles. The crop contains 72 triangles (216 vertices), all stored kind 2,
with every output face reversed to match transformed stored normals. All 4,221
decoded water faces are outside this selection. No water was silently dropped.

The actual Y-up bounds are `[164,19.5,227.5037537]` through
`[188.0000458,23.8678703,252.0000153]`. The historical point becomes
`(176,20.002,240)` under the unchanged `(x,-y,-z)` transform. Geometry completeness,
non-water surface semantics, physical units and agent calibration remain
unverified; the same door and dynamic-collision omissions apply.

| Artifact | SHA256 |
| --- | --- |
| `region.obj` (10,187 bytes) | `9a67b137532e08e3c5935027ce7c400d7980ca2ab5290facf18957ed2d1e3329` |
| `geometry.json` | `3fc130b165a5f2c00e6231eadbdd90a645d55d5c1e69b87fa904211ef5bc2789` |
| `export-manifest.json` | `cad9ba2e329b900eac2506d92d4d116846cc977d9a68e80618da3e0cf61558f7` |
| `source-reference.json` | `0b0e87c3a85f508ba4a3acd1a74f74d5c0340d8845b25bc5d96c17ab1ca8f7e9` |

Two deliberate real-input negative probes retained their evidence:

- `ffxi-zone-path-mismatch-20261115-01`: zone 101 with the explicitly supplied
  zone-230 path `ROM/1/31.DAT` refused with the resolved path `ROM/0/121.DAT`.
  No collision decode, `Raw` observation, OBJ or geometry sidecar resulted.
- `ffxi-zone-water-refusal-20261115-01`: source bounds `[457,-18,-318]` through
  `[460,-15,-315]` surround the existing river fixture
  `(458.558,-16.5,-316.667)` in `forever-audit/tests/real_client.rs:26`.
  The unchanged exporter refused `SelectedWater(121716)`; no OBJ or geometry
  sidecar resulted. The refusal was retained, not avoided by filtering faces.

The successful output's `focused-validation.json` records sidecar/OBJ validation,
both expected refusal logs and their hashes, and absence of source/compiler
snapshots on reuse. No new mesh bake, native query, runtime test or Game QA was
performed by this exporter increment.

Root integration subsequently reran the original zone230 crop through the
generalized selector and verified reuse mode. It returned the exact same1821
triangles and byte-identical OBJ, without source staging or compiler output.
Receipt: `evidence/ffxi-sandoria230-reuse-20261115-01/root-integration-result.json`
beneath the private data root. This checks preservation of the earlier export;
it is not a new compilation or game-runtime result.
