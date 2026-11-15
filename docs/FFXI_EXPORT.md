# Offline FFXI geometry export

`scripts/export_ffxi_geometry.py` and `scripts/ffxi_geometry_driver.rs` are
original Banshee entry points around the owning FFXI project's existing reader
and bounded exporter. They do not implement a DAT decoder. The first supported
selection is Southern San d'Oria, zone 230, with an explicit source-space AABB.
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
ROM index table files, and explicitly selected `ROM/1/31.DAT`. Each file is
bounded to 64 MiB, copied once with SHA256, and checked for changes during the
copy. The existing `Client` resolves zone 230 against those snapshot tables; a
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

## Outputs and refusal behavior

On success, `geometry.json` is the `bnav-geometry-v1` input sidecar accepted by
`bake_nav_collection.py`. It identifies the exact `region.obj` SHA256, Y-up
coordinates, source units, transform, coverage limitations and provenance
artifacts. Additional evidence includes:

- `source-identity.json`: git pin, every staged source digest and MIT provenance.
- `build-manifest.json`: driver binary/source hashes and exact reduced lock hash.
- `owned-inputs.json`: original paths, snapshot paths, byte counts and SHA256.
- `request.json`: exact region, units and format-evidence declaration.
- `raw-observation.json`: resolved path, decoded counts, kinds and diagnostics.
- `export-manifest.json`: owning exporter's exact counts, bounds and omissions.
- `resolve`, `build`, `startup` and `export` JSON/log pairs: commands and exit codes.

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
