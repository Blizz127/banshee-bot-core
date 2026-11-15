# FFXI collision geometry source audit — 2026-11-15 CST

**PARTIAL.** OBSERVED: the owner has zone DATs and an existing offline Rust
collision reader. Newer FFXI source also provides a bounded `Raw` → OBJ exporter.
No new asset decode, OBJ extraction, navmesh bake, native runtime or game QA was
run in this audit. Existing `.nav` files are navigation outputs, not input
collision geometry and not proof of a new bake.

**Current-session addendum, 02:08 CST:** root REA metadata now responds, with no
active target. Ghidra specifically reports `runtime_unavailable` and a full JDK
21+ requirement; configuration was not changed. Target-free `inspect_byte_entropy`
succeeded for `ROM/1/31.DAT`, retaining file identity as
`ev_c7170dcd8779c2dca79420f4553dd40d08163c4824357bf5299e7897933fa2d6`.
The external receipt is `evidence/rea-owned-dat-20261115/final-bundle.json` under
the project private data root. This is an identity/entropy observation only;
it does not validate the decoder, collision surfaces or encryption properties.
The historical failure below does not establish a current MCP-wide block.
The documented existing decoder can be exercised without new format research.

Evidence is retained outside git at
`/home/blizz/.local/share/banshee-bot-core/evidence/ffxi-geometry-source-audit-20261115/`.
`AUDIT.json` records source pins, byte counts, SHA256 identities and preserved
failure receipts. No client assets, key tables or decoded geometry enter git.

## Exact retained REA failure and its scope

The original receipt is
`/home/blizz/scratch-build/ffxi-giddeus145-retail-source-check-5d9bed62-20261115/REA-ATTEMPT.json`,
SHA256 `2c5ac02ad94ee604c328752d4de0cc1abbe1095e306670a4fa90d1d2f1070cd9`.
Its `mcp__rea__inspect_byte_entropy` request targeted the owner's `VTABLE.DAT`,
offset 0, length 256, block size 256, detail `complete`. The tool returned
`isError: true` with exactly:

> Do not repeat this startup. Tell the user REA could not start and ask them to restart the MCP client, then run `rea doctor`.

The accompanying `FINDINGS.json` explicitly calls this a startup failure, not an
artifact denial, and retains a previous Ghidra Java ownership-preparation
`ETIMEDOUT`. No artifact digest, header, index resolution or evidence ID was
returned; `actual_collision_parser_run` is false. The receipt records that lane
stopped, made no unchanged retry or direct-reader workaround, and did not run
doctor, setup or config changes.

**OBSERVED distinction:** these files record a technical MCP startup failure and
the tool's no-repeat instruction. They do **not** record an owner-imposed asset
permission denial, a native trust/login/approval prompt or a global prohibition
on every other session. They do not identify the MCP-client session, REA server
instance, agent/thread/host, or attempt timestamp. The named tool, asset path,
FFXI source pin `5d9bed627e5b94d6aa87f9b1828476a9e782e840`, and receipt directory
are the available attribution. Whether the current session/provider is the same
failed startup or has recovered is **unknown** from this evidence. Do not infer
either recovery or a new owner approval requirement from tool discovery alone.

This audit did not retry startup, invoke recovery, use an alternative reader to
work around that failure, or decode assets. The root integrator has the exact
receipt to determine the applicable next step. The same directory's
`handoff.json` has SHA256
`e24f21849f769650156d38bdcde36a17921fb84186ec5e80c3c3db47e4be279d`.
Copies of all four original receipt JSON files are in the evidence directory
above. Earlier Giddeus source notes separately preserve existing content and
instance restrictions; selecting Giddeus is not admission of Balgas Dais.

## Source identities and existing interfaces

The initial read-only reference checkout is
`/home/blizz/dev/ffxi-platform-tank-add-rescue-composed-20261115`, commit
`36b90715b29728ecbccd2fee95493bbc7c14db29`. The relevant crates were clean against
that commit when inspected. The newer source is available as git object
`a13dabcd550e0a777be5077804ba3d51683cfa19` in
`/home/blizz/dev/ffxi-platform`; reading that object did not change its checkout.

| Source relative to the FFXI repo | What it supplies |
| --- | --- |
| `server/crates/forever-audit/src/vana.rs` | Public `key1` and `load_collision`, with public `Raw` triangles, stored normals, surface kinds, object flags and grid size |
| `server/crates/forever-audit/src/lib.rs` | `Client::open`, table-resolved zone path, and zone loading; newer pin adds public `Client::raw_collision` before `Zone::from_raw` consumes it |
| `server/crates/forever-audit/src/geometry_export.rs` at newer pin | Pure bounded `export_region(&Raw, &Request)` → OBJ string and coverage manifest; no file I/O, asset loading or builder invocation |
| `server/crates/ffxi-dat/src/zonelines.rs` | Zone-to-file-ID/table resolution and the DAT chunk walker |
| `server/crates/forever-audit/src/main.rs` | `spawn-audit` audit/safety-table CLI; no OBJ option at either inspected pin |
| `docs/ffxi-geometry-export-20261115.txt` at newer pin | Export source handoff, limitations and retained startup failure |
| `docs/ffxi-detour-mset-adapter-20261115.txt` at newer pin | Separate raw Detour32 single-tile → native MSET wrapper; not a collision extractor |

`vana.rs` is unchanged between these pins: 9,807 bytes, SHA256
`78d23281f6c3d9c6f93261851abe0f7845b4a9ba1c5e577033dfe0fc228da251`.
New `geometry_export.rs` is 20,405 bytes, SHA256
`a1a1720be121af1939a70e5c7e90bcef70d7775e113daaf88c2f1c3219b27822`.
The newer `lib.rs` is 2,906 bytes, SHA256
`30bffba0dbb0e1761733ba7d0c98e0403412ecc8a34a71582d3a34c182ccf21c`.
All inspected source sizes and digests are retained in `AUDIT.json`.

The newer library depends on local `ffxi-dat` and `forever-safety`, `glam =
"0.34"`, `md-5 = "0.10"`, `serde_json = "1"`, and `sha2 = "0.10"`.
`detour-sys` is a dev-dependency. The earlier reader only needs the first four
dependencies. `ffxi-dat` and `forever-safety` have no normal external
dependencies at the inspected baseline. A direct standalone `rustc` import of
`vana.rs` is not self-contained; it requires these Rust crate dependencies.
The existing CLI also collects broad audit inputs and normally writes reports;
`--bake` creates a runtime safety table, not a Recast navmesh. It was not run.

**INFERRED integration seam:** an original thin tool in this repo could consume
the existing external library through an explicit pinned local dependency,
without copying its reader into this repo or editing the FFXI checkout. This
audit establishes source availability only, not a built dependency graph or
authorization to bypass a failed provider. No wrapper was implemented or run.

## Owned asset identities

Root: `/home/blizz/dev/ffxi/client-dat/full-1.2.2/FINAL FANTASY XI/`.
These are OBSERVED read-only size/SHA256 identities collected before the
retained failure was brought to this audit's attention. They are not new REA
format evidence; no key extraction, table resolution or collision decode was
performed, and the asset reads were not repeated afterward.

| Relative path | Bytes | SHA256 |
| --- | ---: | --- |
| `ROM/1/31.DAT` | 9,511,280 | `4d17ce938e53da7a075d985aba5902723527884b6a86fd2046e90ea232e91433` |
| `ROM/0/121.DAT` | 11,404,832 | `003e17cffcb940c88a015dbf02a56256507ef978cefa183e757ee93446dde488` |
| `FFXiMain.dll` | 2,901,584 | `59b9c813ad46350e9b5681e4540a28463f55a33d4a5c938d62e50da95ed1ea67` |
| `VTABLE.DAT` | 109,701 | `b5c19176dd9f6bf97cb0b76cbe5ec98e35a5b02c0d8674d86827ba2c149c37db` |
| `FTABLE.DAT` | 219,402 | `2d6a507a2ac4ee50f6a55bba52d15fc06922dd734c523c5c9a79106a41a1f72c` |

Existing source/test metadata identifies zone 230 Southern San d'Oria with file
ID 330 and `ROM/1/31.DAT`, and zone 101 East Ronfaure with file ID 201 and
`ROM/0/121.DAT`. Giddeus 145 → file ID 245 → `ROM/0/104.DAT` is retained historical
metadata in the other lane's receipt; this audit did not hash or read that DAT.
The formula is `100 + zone` below zone 256, `83635 + zone` otherwise. The reader
consults root `VTABLE.DAT`/`FTABLE.DAT` and available `ROMn/VTABLEn.DAT` /
`ROMn/FTABLEn.DAT`, so a source-selected path does not replace fresh table
resolution against an exact client installation.

The source reader searches `FFXiMain.dll` for a 256-byte model table with
expected MD5 `0bfa75c0e9ff6ff8497b370024b3b148`. This is a **source-declared
expected digest**, not a measured digest of a table extracted in this audit.
No table bytes were extracted, printed or copied.

## Format, coordinates and conservative omissions

These are OBSERVED facts about the inspected reader source, not a new
interpretation or successful parse of the current DATs:

- DAT contains a flat sequence of 16-byte chunk headers. Resource type is bits
  0–6 of the word at header +4; length is bits 7–25 times 16, including the
  header. MZB collision is type `0x1c`; RID regions are `0x36`.
- The existing reader decodes MZB versions at least `0x1b` using its model table,
  follows the collision grid, and deduplicates object/geometry offset pairs.
  Object records provide position and normal transforms. `Raw` already contains
  world-space vertices and mirrored-object winding correction; do not apply the
  object transform a second time.
- Client Y points down. A stored floor normal has negative Y. Existing client
  source tests show retail raw triangle winding is opposite the stored normal;
  blindly preserving or reversing indices without the chosen axis transform is
  insufficient.
- The newer pure exporter explicitly uses `(x, -y, -z)` and aligns each output
  geometric normal with the transformed original stored normal. It does not
  force all faces upward; walls and ceilings remain collision. A different
  axis conversion must not be silently substituted by a consumer.
- Type 9 denotes a water bed in the existing source; object flags encode the
  associated water surface. The exporter refuses an entire selection containing
  type 9. Silently dropping those faces could expose terrain below water; treating
  them as ordinary solid ground would invent a walkability policy.
- `Raw` omits RID door boxes, moving/dynamic collision, lights, merged subarea and
  object/entry bookkeeping. Its parser also skips some malformed/absent records,
  repairs invalid stored normals, and retains the last MZB that successfully
  parses. A successful result cannot prove all source collision was retained.

The exporter selects whole triangles whose source-space AABBs overlap an explicit
region, including boundary contact. It does not clip triangles; consumers must
use actual output bounds. Every input triangle and normal is checked before
selection. Array mismatch, non-finite or degenerate geometry, zero/orthogonal
normals, empty selection and explicit resource-limit violations refuse output.
Limits cap input at 1,000,000 triangles, output at 333,333 triangles (three
vertices each), OBJ at 64 MiB and provenance text at 64 KiB.

Its manifest always states `collision_complete: false`, keeps omitted-from-Raw
and unknown missing-source counts distinct, and leaves agent/navigation
calibration unset. Physical units remain caller-declared; this audit establishes
no metres-per-unit calibration, agent radius/height/climb, slope, cell size or
cell height. Parser success and synthetic builder defaults must not fill those
gaps implicitly.

## First real-region candidates and proof still absent

The earlier `server/crates/forever-audit/tests/real_client.rs` contains a Southern
San d'Oria homepoint fixture at source position `(-85.554, 1.0, -64.554)`, described
there as previously checked in game. A small region around that fixture is a
concrete source-grounded candidate for eventual geometry inspection; this audit
does not choose its bounds, certify it dry, or claim the fixture was rerun.
East Ronfaure fixtures provide explicit water counterexamples and should not be
mistaken for dry starter-zone geometry. The FFXI lane selected Giddeus as a
missing Windurst-neighbour zone; it has not exported a real Giddeus region.

Also present in `/home/blizz/dev/forever-client` at
`a88d5f912378d797d7dd79f88a976055927dfb80`: runtime Lua `game.collision_mesh()` in
`crates/vana-client/src/client/lua/state.rs`, backed by `Ground::all_tris()` in
`client/ground.rs`. It emits nine little-endian f32 values per triangle and
filters degenerate/currently open door-box geometry. It loses normals, surface
kinds and object flags, depends on a live client, and was not invoked. The newer
pure offline exporter retains a more useful evidence seam for this task.

No actual zone triangle count, selected bounds, surface-kind distribution, OBJ,
Recast bake, Detour reload/query, door/water coverage or game-client QA is
VERIFIED by this audit. The newer FFXI handoffs label their exporter and MSET
tests source-only/unrun at handoff; no test success is inferred here. C0 navmesh
coverage and C1 `/fb` behavior/QA status are unchanged by this document.

## Provenance and licensing

`vana.rs` explicitly attributes its minimized copied reader to
`/home/blizz/dev/forever-client` commit
`a8c75ab4e981d6056cd2860d8f8e12eacfff7671`, files
`crates/vana-client/src/dat/{collision,zone,tables}.rs`. That exact commit's
`LICENSE` is MIT, copyright 2026 Lenon Kitchens. The current inspected client
also declares MIT. Licence text SHA256 is
`2b3084da24f4f327d447cdb4e982612dd8a94c4345250cf3f5e8cad122e937fc`.
The FFXI `forever-audit` package and inspected workspace do not declare a licence;
the MIT attribution does not establish a blanket licence for all FFXI code.
An external dependency should preserve those distinctions and any notices.

Existing navmesh provenance is in the composed checkout's
`server/devstack/forever-data/navmeshes/SOURCE.md`: 43 cached LSB outputs plus
Inner/Outer Horutoto supplements, referencing `LandSandBoat/xiNavmeshes` pin
`4961893b94e4463af8434aa5e39dbf10ce7c8d82`. They are already-produced navigation
meshes, not evidence that the shared builder has consumed source collision.
No licence for that data was established by this bounded source audit; none is
assumed. Owner client assets remain private third-party game data, outside git.

Only this documentation was added to Banshee Bot Core. No external source code
was copied into the repository, and no other project or shared configuration was
modified. Next correction is to resolve current-session applicability of the
recorded technical startup failure, then obtain explicit actual-asset evidence
and calibration before claiming a usable zone mesh.
