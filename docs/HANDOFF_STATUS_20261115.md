# Handoff evidence refresh — 2026-11-15 02:00 CST

**Verdict: PARTIAL.** One coordinator task-board snapshot was read at
02:00:19 CST. It returned 300 task rows; ten relevant rows were retained in a
selected-report file. This is a bounded task-board check, not an inspection of
every native inbox or a complete historical message audit. No readiness request
was rebroadcast, no other lane was messaged and no server/client check was run.

## Changes since the build 0001 report

| Boundary | Observed evidence | What remains unproved |
| --- | --- | --- |
| C1 FFXI Clock/grammar adoption | Task `0fcbfa0421bc` updated 02:00:17 CST with its own native build/check work and an offline nav adapter. It does not report adopting the shared Clock/grammar seam or executing the shared build's P0/client checks. | Current-baseline reconciliation, shared-crate integration, native `/fb` P0 and Game QA. Its unrelated in-progress native checks are not a C1 receipt. |
| Build 0001 publication | Publisher task `3f9392ca5d00` still contains a 2026-11-11 13:32:10 CST local-only launcher summary. Searching all returned task titles, summaries and instructions for the candidate hash/build/core handoff finds only our own report. | Publisher intake receipt, private feed/entry contract, uploaded artifact readback and launcher update detection. No absence claim is made beyond this snapshot. |
| FFXI navigation adapter | Existing git object `a13dabcd` adds `forever_audit::detour_mset::wrap_raw32` and query-span validation; its source note explicitly names bot-core source `ae73d7f` and backend `d9996bed…`. | Source note says no actual backend output consumed; five synthetic tests are marked UNRUN there. The newer board report says they were launched and still in progress. Neither establishes a completed native load/query or real-map result. |
| E&B geometry | Task `d30281403634` at 01:20:34 CST reports local `8f3a551`; the documented output and manifest exist. There are 1,974 bounded static candidates across 71 of 85 sectors, with 1,811 static candidates unresolved. | These are demo-corpus visual bind-pose envelopes, not verified collision or traversal data. Pathing coverage remains 0/85 and the free-flight model decision is unanswered. |
| GW2 maps | Task `c274a1300c36` at 01:59:24 CST keeps scores 1/1/1/1 and zero navmesh zones. Work is queued behind Norn opening builds and handed to the Codex lead. | No new geometry export, map bake, server consumer or Game QA result is reported. |
| Other corrected scorecards | No changed attributed scores were found for LOTRO, SWTOR or DCUO; ESO's correction is still delivery acknowledgement only. | Do not infer readiness from an unrelated release, a task status or absence of a new report. |

The six accepted scorecards remain unchanged. DCUO's newer 01:41:24 CST task
summary concerns private launcher diagnostics and retained owner-only
Steam/Visual C++ prompt decisions; it provides no replacement bot scorecard or
playable Game QA result. The historical zero row remains backed by the earlier
saved readiness report. SWTOR's companion-behavior conflict/hold and E&B's
flight-pathing decision remain unresolved in this snapshot.

## FFXI single-tile wrapper source

Read-only observation:
`git -C /home/blizz/dev/ffxi-platform show a13dabcd:docs/ffxi-detour-mset-adapter-20261115.txt`.
The same commit changes `server/crates/forever-audit/src/detour_mset.rs` and its
focused tests. It is separate from the C1 cancellation-clock/grammar extraction.

The declared producer profile is raw little-endian Detour 7 with 32-bit polygon
references, one tile, no portals/off-mesh links and zero tile x/y/layer/userId.
The wrapper preserves payload coordinates and prepends native MSET1 headers.
It explicitly binds our single-tile helper identity. **Preserve the existing
single-tile mode:** a future tile collection with portal topology is a different
integration contract, not an input this wrapper currently accepts.

The note narrows its supported query envelope to finite coordinates and extents,
tile width/depth at least one native unit, and checked native tile-loop bounds.
It does not change the live navigation loader or calibrate game coordinates.
It also records that actual owned DAT/REA source evidence remains blocked by a
retained REA startup refusal; this refresh neither retries that operation nor
reinterprets the denial as permission for an alternate asset reader.

## E&B candidate envelopes

Read-only paths under `/home/blizz/dev/Earth-and-Beyond-DIT/` at observed HEAD
`8f3a551`:

- `docs/PATHING_B1_GEOMETRY_EXPORT.md`.
- `evidence/pathing-b1/geometry-v1/manifest.json` and its per-sector candidates.
- `evidence/pathing-b1/geometry-v1-verification.json`.

The manifest declares `pathing_ready: false`. The source note states every
object is `collision_verified: false` and warns that enclosing spheres may
close legitimate passages. This is a tangible geometry-preparation artifact,
**not a triangulated collision OBJ intake** for the ground builder. The
verification receipt declares PASS for 22 focused tests, hash/conservation
checks and candidate spheres; those checks were not rerun by bot-core.

Keep the pending flight/obstacle/gate-graph choice with the coordinator and the
owning lead. No game source, asset or schema is changed by this observation.

## Evidence retained outside git

Directory:
`~/.local/share/banshee-bot-core/evidence/handoff-refresh-20261115-020019cst/`.

| File | SHA-256 |
| --- | --- |
| `task-board.json` (one raw board snapshot) | `7ed253a7acd136c6e593ed0d44a05339cd1a3f69d0c0c44196b674eda669f908` |
| `selected-reports.json` (ten relevant tasks) | `111339612abe37caffc23ed9295be0670a4e30bcaea8542550982df601a0ff6a` |
| `source-observations.json` (paths/hashes/declared fields) | `d79c0142a41092fc60fb5a366aa9a75370a4ed5ad75d5be3bd01beaffe696292` |
| `ffxi-detour-mset-source-note.txt` | `174203b49823eace56c3f48d6500f295888056d62652efafcb2b1724bc2c66c3` |
| `enb-geometry-source-note.md` | `0f156f66ef184843e18420fe7c7c8dd3b4598f815f3e0d83878803a52a7d73cf` |

The E&B source manifest hash is
`850a58550a11a56b665ebaef7ed81d477a2e2baeeca2aea6b7153d338ebdd848`;
its verification receipt hash is
`468c6ff2363e856ca5b1363c5987f12e903d3705523a2c4881f1ea456beb4a22`.
The manifests were read, not regenerated or promoted to runtime evidence.

## Next work remains available

Native C1 adoption and private publication are narrow external dependencies,
not a blanket stop on this lane. Shared geometry tiling, bounded format/ABI
validation, evidence-aware input handling and source-backed geometry work can
continue within the existing holds. Keep the first publisher/integrator intakes
as the canonical requests; a new concrete artifact should say which prior
artifact it supersedes rather than create competing work or repeatedly ask for
acknowledgement. No polling loop follows this snapshot.
