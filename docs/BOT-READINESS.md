# C0 bot readiness — refreshed 2026-11-15 04:28 CST

The latest bounded refresh found **no new attributed scores**. E&B now reports
85/152 visual placements exported in sector1705, 11 tiles and 9 empty cells in
a 20-cell window, plus separate isolated quest/ability fixtures. Collision
export stays empty, complete coverage stays 0/85 and behavior stays no (0).
Current FFXI native C1/P0 acceptance and bot-core publication still have no
completion receipt in the inspected summaries. See B3 below; no job or closed
packet was replayed and no request was rebroadcast.

One bounded coordinator snapshot and existing owning documents now establish an
attributed E&B headless score of **yes (2)**; its row is **2/1/1/0, total 4/8**.
This is isolated native-session acceptance, not live/companion readiness. New
sector-coordinate visual geometry also produced seven tiles and a short
cross-tile query, but collision export is empty and complete coverage stays
**0/85**. Walking maps remain partial. See B2 below for exact evidence and limits.
No other new attributed score or geometry coverage was found in this bounded
read. No native job, closed packet or acceptance check was replayed.

Independent offline-tool evidence later progressed: two bounded FFXI crops now
load/query in the owning native library, and the shared pure C1 extraction
passes comparison against observed source 5c73. See [the current build](BUILD_0008.md).
These results do not change attributed readiness scores, establish complete
zone maps or satisfy native C1 adoption/P0 or Game QA. No request was rebroadcast.

At 02:29 CST the attributed scores are still unchanged. E&B now reports four
model-local Recast tiles and a short two-tile path; per-tile Recast is its
required output and the earlier output-model choice is reported resolved.
Sector transforms, calibration, native loading and complete coverage remain
unverified (`0/85`). The FFXI corrected geometry-wrapper packet is a source
handoff, not C1 adoption/P0. See [the latest refresh](HANDOFF_0230.md).

The bounded 02:20:40 CST refresh found no new attributed scores. E&B's lead
now reports 3,446 bounded placements across 77 sectors, 339 unresolved, and a
nine-class catalog; pathing remains 0/85 and behavior remains no (0). These
are preparation artifacts, not a readiness or QA upgrade. The FFXI lead's
reconciled standing **Never restart FFXI servers** hold also remains binding;
zero players does not restore authority. Details and immutable snapshot hashes
are appended to [the handoff record](HANDOFF_STATUS_20261115.md).

**Verdict: PARTIAL.** Six corrected lead scorecards have arrived. Their reports
are recorded below; this consolidation did not run a server, client, navmesh bake
or Game QA check. No readiness request was rebroadcast and no other project was
edited. C1 and the shared builder may proceed while the remaining rows arrive.

The 02:00 CST refresh leaves all scores unchanged. New E&B geometry preparation,
GW2 sequencing and the narrow FFXI adapter/publication boundaries are recorded
in [the handoff refresh](HANDOFF_STATUS_20261115.md); none is a new Game QA pass.

The owner's 2026-11-15 00:46 CST correction uses **0 = no, 1 = partial,
2 = yes**. It supersedes the initial 0–3 request; do not translate old 0–3
numbers mechanically. **Pending** means no attributed corrected score was found
in the sources inspected, not that the capability is missing. Scores are the
owning lead's assessment, not independent certification. A partial pathing score
may mean usable geometry or a raster exists while Recast/Detour coverage is zero.

The existing catalog names FFXI LSB and WoW Benilla/AC. The received FFXI score
explicitly covers the **Forever Rust platform**, not regular LSB; keep those
rows separate. Fixed rollout C1–C6 remains authoritative; totals inform C7+
ordering and do not move a game ahead of its assigned phase.

| Server lane | Headless player session | Walking maps | Complete-enough server | Behavior library | Total | Evidence / owning lead |
| --- | --- | --- | --- | --- | ---: | --- |
| FFXI Forever Rust | yes (2) | partial (1) | partial (1) | partial (1) | 5/8 | F1; `claude-ffxi-platform` |
| FFXI regular LSB | pending | pending | pending | pending | — | Separate lane; catalog row unfilled |
| WoW Forever, Benilla/AC | pending | pending | pending | pending | — | Catalog names this as reference model; no score supplied |
| FF14 Banshee Realm, Kawari | pending | pending | pending | pending | — | Catalog row unfilled; client files absent per governing spec |
| SWTOR | partial (1) | no (0) | partial (1) | partial (1) | 3/8 | S1; `claude-swtor-preservation` |
| DCUO Rust | no (0) | no (0) | no (0) | no (0) | 0/8 | D1; `claude-dcuo-rust` |
| ESO Rust | pending | pending | pending | pending | — | E0; correction delivered, no scored reply in inspected board |
| GW2 Rust | partial (1) | partial (1) | partial (1) | partial (1) | 4/8 | G1; `claude-gw2-rust` |
| LOTRO Rust | partial (1) | partial (1) | partial (1) | partial (1) | 4/8 | L1; `claude-lotro-rust` |
| Earth & Beyond DIT | yes (2) | partial (1) | partial (1) | no (0) | 4/8 | B2 (B1 historical); `claude-Earth-and-Beyond-DIT` |
| Marvel Heroes | pending | pending | pending | pending | — | Catalog row unfilled |
| Lineage II C4 / Interlude | pending | pending | pending | pending | — | Catalog row unfilled |

The catalog's remaining “others” row is unresolved. Add individual server lanes
as their existing broadcast replies land; this table does not claim a complete
inventory of all configured projects or live servers.

## Attributed evidence

All six scored rows are **OBSERVED lead reports** in coordinator `task_board`,
queried read-only at 01:06 CST. Stable saved copy:
`/home/blizz/.local/share/devbox-coordinator-state/workspace/records/watch-eso-hollow-20261115-070500/task_board.json`,
SHA-256 `e72f7ed95cd7465fdeb6c6524a4f8fda0a9a2bf9f29523709ac11c99a0febeef`.
The file contains all six task IDs and timestamps below. Runtime claims inside
those reports have not been independently repeated here.

The seven relevant task records (six scores plus ESO's pending correction) are
also retained under this project's evidence root:
`~/.local/share/banshee-bot-core/evidence/c0-readiness-20261115/selected-reports.json`,
SHA-256 `91753d2346ed1972d82260d8e36068b2f7f928ca41a718807187474570e9b4f1`.
The subset records the original snapshot path/hash and omits unrelated tasks.

### F1 — FFXI Forever Rust

Task `0fcbfa0421bc`, lead `claude-ffxi-platform`, updated 00:58:03 CST.

- Headless: `server/crates/xi-map/src/bot.rs:370–417,512–526` creates a real
  `Session` and drives `handle_direct` without a game client or per-bot UDP;
  local driver IPC is separate.
- Walking maps: `server/devstack/forever-data/navmeshes/SOURCE.md` and metadata
  report 43 cached `.nav` files plus two Horutoto supplements. Owner DAT/MZB
  provenance is in `forever-audit/src/lib.rs:19–54`. The current bake is a safety
  table, **not a reproducible DAT-to-navmesh build**. Complete per-zone coverage
  is still being inventoried by the lead.
- Server: the unresolved entity/wall incident remains in
  `/home/blizz/scratch-build/ffxi-client142-entity-wall-20261115/ROOT-FIRST-CHECKED-FINDINGS.json`;
  no current real-player quest/fight/loot/trade end-to-end proof is claimed.
- Behavior: `population/brain.rs:383–768` has job/role combat and care strategies;
  encounters and job coverage remain incomplete. Lead distinguishes inspected
  `5d9bed62` (unrun) from rc180 / `0c866f43` (one native check plus 79 kit checks).

Refresh at 02:00:19 CST: this task's 02:00:17 report describes current native
checks and an independent offline raw32-to-MSET adapter (`a13dabcd`); it does
not report shared Clock/grammar adoption or a completed P0/client gate. Its
source note marks actual builder output unconsumed and the five synthetic tests
unrun; the newer board report says those tests were launched and still in
progress. This does not upgrade the row or geometry coverage.

### S1 — SWTOR

Task `ddfa31d97341`, lead `claude-swtor-preservation`, updated 00:51:54 CST;
explicitly supersedes the 0–3 row on `5895cf9705a8`.

- Headless: full in-process player sessions exist in the replay harness at
  `~/scratch/swtor-lanes/warrior-1-50/goal-1to50-20261107/lanes/earned-kit-r1/kit48/earnedkit.py`.
  The associated `SCOREBOARD-1to30.txt` reports 446/524 level 1–30 quests. No
  long-running clientless player session beside humans on the live gateway.
- Walking maps: **0/27 served area packs** have navmesh. Retail archive room,
  placement and path records are partly decoded; collision meshes and an
  extractor are missing. Movement is straight-line. Stairs, ramps, lifts and
  zone links need geometry-backed checks after extraction and per-tile baking.
- Server: quest/fight/loot/vendor/travel work is reported, with live c168s;
  `integrated/c168s/tree/private_dk_gtn.py` records absent trading transport.
  Player trade/mail and 39 lifts below level 30 remain incomplete.
- Behavior: `integrated/c168s/tree/private_bot_rotation.py` and
  `private_bot_rotation_data.py` contain class/discipline priorities and squad
  role kits. Play measurement covers Warrior and the squad; no roaming,
  questing, trading or grouping strategy layer.

**Existing hold:** this lead reports a conflict between prior task
`a31bc9a5bb4b` ordering its own `/fb` companion lane and the instruction to wait
for the shared spec. New companion behavior patches are held pending the
coordinator's resolution; read-only measurements, its default-off switch and
server defects continue. This consolidation does not release that hold.

### D1 — DCUO Rust

Task `3e436176e74c`, lead `claude-dcuo-rust`, updated 00:57:05 CST. Also directly
read `~/dev/dcuo-rust/docs/BOT_READINESS.md` at commit
`4170246bdfee8fb4cebe792425ade072187687a1`; document SHA-256
`ed297815c6df8b4b6d2caef07f7724271e01edca11d07900dd4b5532f9672602`.

- Headless: `src/bin/dcuo-server.rs` has no player session model.
- Walking maps: `docs/NAVMESH_COVERAGE.md` reports 21,095 `.map` candidates under
  `MAPS`, 282 candidate-directory rows, and no separately identifiable navmesh
  tile filenames. These are **filename candidates**, not decoded geometry or
  a proof that embedded navigation data is absent. Geometry parser, tile
  generation and actual playable coverage are unknown/missing.
- Server: `STATUS.md` has no retail login/quest/fight/loot/trade path.
- Behavior: no class/power combat strategy library.

Lead's private per-directory evidence SHA-256:
`7c599120468e8ea5e4846f1c7388ee1410f0dc8411caf9495a5088e7f50d9f32`.
Existing milestone 2 runtime holds remain in force; read-only geometry inventory
and future milestone 4 movement work do not authorize a runtime launch.

### G1 — GW2 Rust

Task `c274a1300c36`, lead `claude-gw2-rust`, updated 00:51:21 CST; corrected
row supersedes `ce5cebc9912f`.

- Headless: `crates/gw2-net/src/bin/game_observe/mission.rs` and
  `story_tables_tests.rs` run world logic without a client; each connection
  owns a private world, so a shared-world production bot session is missing.
- Walking maps: terrain/collision triangles in `Gw2.dat` are read by
  `crates/gw2-dat/src/bin/gw2-map-dump.rs`. **Zero zones have navmesh**;
  `tools/huntreach/reach.py` provides a slope-limited grid for map 379. Missing:
  tiled triangle export, Recast/Detour bake and server movement integration.
- Server: lead reports 297/724 story quests pass, 51 in the real client;
  trading post, player trade, parties, dungeons and shared world are missing.
- Behavior: species AI, `game_observe/eir_ally.rs`, and deeper Mesmer support
  (`mesmer_clone.rs`); no player-bot strategy library.

Refresh: the same task at 01:59:24 CST explicitly retains 1/1/1/1 and zero
navmesh zones. Geometry/readiness work is queued behind Norn opening builds and
handed to the Codex lead (`~/re/gw2/notes/codex-handoff-20261115.md`); no new map
artifact is reported.

### L1 — LOTRO Rust

Task `92b6773cbc68`, lead `claude-lotro-rust`, updated 00:52:13 CST; corrected
row supersedes `e83374f1b858`.

- Headless: `crates/lotro-server/src/bots_wire.rs` bots are actors in a human
  session. `session/tests/progression_sim.rs` runs full sessions without
  sockets in the harness; no production headless player session yet.
- Walking maps: own-client heightmaps, PhysObj collision and interior cells;
  `crates/lotro-dat/examples/area_nav.rs` generates 0.5 m raster/A-star paths.
  Coverage is **50 landblocks**: Archet 25 and Thorins Gate 25; no
  Recast/Detour mesh, all other zones and interiors remain missing. Proposed
  own-game tile boundary is one 160 m landblock.
- Server: live v305 report and `docs/PROGRESS.md` record 892/2,288 base-game
  quests passing, real skill damage, loot/vendor/rewards; no player trade or
  auction house, most regions unpopulated.
- Behavior: `docs/reports/w65-census-REPORT.txt` reports 95/433 skills fully
  real, 172 partial; creature AI and companion follow/attack/heal exist,
  no rotation/strategy library.

### B1 — Earth & Beyond DIT, historical initial report

Task `d30281403634`, lead `claude-Earth-and-Beyond-DIT`, updated 01:01:02 CST;
roadmap `docs/ROADMAP.md` Track B, commit `706d610`.

- Headless: `tooling/linux-build/PlayerManager.cpp:195` has
  `RegisterSimulatedPilot`; former-host DIT slice 0 had one space and one
  station controller. Gate support is off and `DebugPlayer` does not fight.
- Walking maps: `net7.sector_objects` placement transforms plus owner client
  W3D models in MIX archives; Rust `enb-w3d` reads models. **Zero sectors** have
  generated pathing; asset-to-W3D mapping and per-sector export are missing.
- Server: mission/combat/loot/trade code exists, but
  `PLAYER_EXPERIENCE_COVERAGE_20261104.md` says actual-client
  quest/reward/relog on the current host was not run.
- Behavior: `MOBClass.cpp:376` is NPC AI; no player-class combat/strategy
  library, and current DIT controllers are noncombat.

Refresh: task `d30281403634` at 01:20:34 CST and observed local commit `8f3a551`
add a concrete geometry-preparation artifact at
`~/dev/Earth-and-Beyond-DIT/evidence/pathing-b1/geometry-v1/`. It retains 85
sectors/4,660 placements and bounds 1,974 static candidates in 71 sectors;
1,811 static candidates remain unresolved. The manifest is explicitly
`pathing_ready: false`; visual bind-pose spheres are not collision-verified,
and generated pathing remains **0/85 sectors**. Readiness stays 1/1/1/0.
See `docs/PATHING_B1_GEOMETRY_EXPORT.md` in that project and the saved paths/hashes
in [the handoff refresh](HANDOFF_STATUS_20261115.md). No source check was rerun as
a game/pathing test, and this is not yet a collision-triangle intake.

**Historical design question, resolved in the 02:26 report:**
`SectorData.h:42–43` describes free 3D flight. The earlier proposal used sector
obstacle data and a gate/route graph. The later owning decision requires per-tile
Recast output, with those graphs supplemental; it is no longer an open choice.

### B2 — E&B isolated headless acceptance and partial sector triangles

OBSERVED: task `d30281403634` at **02:51:37 CST** attributes scores **2/1/1/0**.
Its retained native acceptance document reports three connection-less Player
bodies, 154/154 assertions and zero listener syscalls. Adapter commit
`4a346aed2a2315f6fb8fd72be64fa7991e66e2e0`, native build
`a96798280fdd1788195ad48b7e6a7a13447fce6a`, final parser/run-script commit
`3cd37d30eb07845f9e4f82cbf325313d06f6050c`. This is an isolated three-avatar
fixture on ILP32, not a client session, live service, class strategy, full timer
dispatch or complete native shutdown proof. Native geometry is not established
by the headless acceptance. Bot-core consumed the closed record without reruns.

OBSERVED separately: producer `c0560002fed917f7cb344d9a7117b738a47d77af`'s
**03:19 CST** sector 4115 record exports one of 100 visual placements as 120
vertices/190 triangles. Seven tiles and five explicit empty cells build with
zero missing cells; a short query traverses two tiles/seven corridor polygons.
The declared-collision mode exports zero geometry; no terrain is covered.
The remaining placements retain explicit scale, orientation, animation or
representation omissions. Engineering axes and scale are not calibrated ship
motion. Native compatibility remains NOT_VERIFIED, Game QA NOT_RUN, and complete
verified coverage **0/85**. These candidates must not reject player movement.

Retained metadata under
`~/.local/share/banshee-bot-core/evidence/c0-refresh-20261115-0319/`:

| Record | SHA-256 |
| --- | --- |
| `delta-summary.json` | `155fa208a3942d8f715aa0cca05e959be6194ce40bed2c8a07a50149a21aaa1c` |
| `enb-headless-acceptance.json` | `0d44a071cfae7c618d4df15d9ef9a9a5de890b1698baae288faa22ee8841cb05` |
| `enb-sector-verification.json` | `bcca6ae6fa3c50b13cc1234b26f9da6f87a07694014a00c81c9c1830ddf7b014` |
| `task-board.json` | `608b775b629086fd38cbbbf561c399ce8424741049fcc8b4930a1b18de0a9f51` |

VERIFIED here: these retained metadata identities. The owning lead's reported
checks, game-source pins and input hashes are attributed evidence, not tests or
asset rehashes performed by this refresh. Fixed rollout C1–C6 is unchanged.

### B3 — E&B sector1705 and isolated readiness fixtures, 04:28 refresh

OBSERVED: task `d30281403634`, reported **04:14:22 CST**, retains **2/1/1/0**.
Producer `ef8539c76d0c7c7c4c9f21480f6b9cd9a5ef9b0f` now exports 85/152 visual
placements in sector1705: 12,681 vertices and 19,137 triangles. Its requested
20-cell window has 11 built tiles, 9 explicit empty cells and zero missing cells;
one query crosses two tiles/two corridor polygons. The bake finished 03:54:15
CST. Outside cells are unrequested; declared-collision export remains zero.
The explicit engineering cell height of 2 follows a refusal at 1 and establishes
no native clearance or flight calibration. Complete coverage remains **0/85**;
native compatibility/Game QA are unverified.

Separate owning metadata reports 128 quest/reward/reload checks and 153 Sentinel
PowerDown checks. These isolated synthetic native fixtures are not actual-client
completeness, a general quest proof or a class-strategy library. They are not
combined with geometry or headless counts and do not upgrade any score here.

The same one-board refresh found no completed current C1/P0 receipt in task
`0fcbfa0421bc`'s 04:20:59 summary. Its ongoing compilation/job state is not
acceptance; no job or closed packet was rechecked. Publisher `3f9392ca5d00`
still carries the historical Nov11 b148 LOCAL ONLY summary, without a bot-core
publication receipt. These absence findings are limited to the inspected
summaries and do not request an acknowledgement or release any hold.

Retained under `~/.local/share/banshee-bot-core/evidence/c0-refresh-20261115-0428/`:

| Record | SHA256 |
| --- | --- |
| `delta-summary.json` | `ec4a89e423c1a6b26cac8cf216a23266f8e795fcc2be776d074842103ff24669` |
| `task-board.json` | `9d3f07ed272f16af04e6cf8b1080403ed8fa2eec3bfa1c251369225c4e15f69a` |
| `enb-sector1705-verification.json` | `d39fa6ed5991a6b3d49054e8cf7e8344612d0ddff2de0fdf364df4966009435f` |

### E0 and unreported rows (retained)

ESO correction task `09ac1d65c8a2` was delivered at 00:50:27 CST; its board
summary is only delivery acknowledgement. No scores can be derived from it.
The catalog `~/scratch/banshee-catalog/BOT-READINESS.md` has unfilled WoW,
regular FFXI, FF14, SWTOR, DCUO, ESO, GW2, Marvel Heroes and L2 rows. Its SHA-256
is `d6c65d46265f40c87bf15baa36e3c9f1e77dbe413a026af0181dbc9720c89d0c`.
Absence here is bounded to the catalog, coordinator reports and targeted
primary-repository docs searched; native inboxes were not inspected.

## Coordinator intakes for missing pieces

These are **proposed actionable intakes**, not claims of dispatch or receipt.
The sole integrator routes them through the coordinator under task
`dcc9a63a40ab`, naming the existing target tasks below. Reuse existing owning
leads, preserve their in-flight work and holds, and do not create a competing
writer. No prior bot-core intake is superseded; older 0–3 scorecards are
superseded only where the lead explicitly provided a corrected row.

Routing update, 01:10 CST: the integrator submitted these intakes through
`coordinator.py report --task dcc9a63a40ab`. The task board accepted the record;
native notification was unavailable. Owning-lead receipt or execution is not
yet confirmed. No new worker/session was launched and no existing hold lifted.

| Owning lead / existing task | Missing piece | Concrete next work and acceptance evidence |
| --- | --- | --- |
| SWTOR / `ddfa31d97341` | Walking maps no (0) | Reuse its queued collision-reader lane: inventory all 27 served packs, decode one representative collision source using REA when unknown, export triangles to the shared builder contract, then generate a first tile and coverage manifest. Keep extraction private; Game QA later checks obstacles/stairs/transitions. Companion hold remains separate. |
| DCUO / `3e436176e74c` | Walking maps, headless, server, behavior all no (0) | Start with cooked-map geometry identification and a reproducible private per-zone coverage manifest; decode/export a representative zone when source evidence supports it. Keep existing milestone 2 holds. Behind the server's existing milestones, scope a headless session over its own action APIs, an actual-client quest/fight/loot/trade proof, then class/power behavior as data. Score each piece only after evidence arrives. |
| Earth & Beyond DIT / `d30281403634` | Behavior no (0); zero completely verified sectors | Continue the existing Track B1/B2 intake: resolve omitted collision/placements and transforms, use the already required per-tile Recast output with supplemental obstacle/gate graphs, and implement class strategy from the catalog using the accepted isolated headless seam. Calibrated ship movement, sector coverage and Game QA remain separate. This updates the canonical intake without dispatching a duplicate. |

Maps-first follow-ups for partial rows reuse their already queued work:
FFXI needs a reproducible DAT/MZB-to-mesh path and zone coverage; GW2 needs tiled
triangle export and movement consumers; LOTRO needs landblock/interior export
and conversion beyond its 50 raster landblocks. These do not require another
readiness broadcast or delay C1.

The supported Codex reporting route is:

```text
python3 /home/blizz/.local/share/devbox-coordinator/coordinator.py report --task dcc9a63a40ab --status working --summary "C0 table and concrete owning-lead intakes: docs/BOT-READINESS.md ..."
```

`coordinator.py:1581–1628` records the summary and notifies the coordinator's
native inbox if reachable. A recorded report is not proof another lead acted;
continue independent work without waiting for an acknowledgement. The `say`
subcommand is limited to Gemini/Grok/Muse identities and is not the Codex route.

## Reconciliation sources and next correction

The 0–2 correction is
`~/scratch/model-swap-20261110/brief-solo-bots-correction-5-6-20261115-0046cst.txt`,
SHA-256 `584d96c388029f880077f94909217d89bf3909a2c2b9bdd492f3f9d60a509a81`.
Read-only source query: `coordinator.py tool --name task_board --arguments '{}'`.
Next correction: consume newly arriving scored replies, add their dates and
proof, confirm routed work via subsequent coordinator evidence, and replace
partial pathing claims with per-zone artifacts and Game QA observations when
available. Features remain off until their required QA gates pass.
