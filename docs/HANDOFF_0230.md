# Handoff refresh — 2026-11-15 02:29 CST

**PARTIAL.** One read-only coordinator snapshot at 02:29:15 CST was compared
with the retained 02:20:40 snapshot. A concrete FFXI wrapper correction has
arrived. C1 native adoption/P0, owned FFXI native navigation and private bot-core
publication still have no completion receipt in these inspected sources.
No request was rebroadcast, no acknowledgement was polled and no other lane
was modified.

## FFXI correction ready for independent consumption

**OBSERVED:** owning task `0fcbfa0421bc`, updated 02:28:51 CST, supplies
`5c73a8751940ba767c7b86a50bb96b38b5d1e4f6` as the direct successor of
`a13dabcd550e0a777be5077804ba3d51683cfa19`. It supersedes the proposed
detail-boundary correction only; the original failing receipt remains valid
for a13, and C1 integration remains separate.

**VERIFIED identity:** the commit exists in the local FFXI object database,
has exactly that parent, and its tree is
`1079dd6cdf686aec38f62de68d8a9bb2eabeaab7`. All three supplied source files
match the exact git objects:

| File under `/home/blizz/dev/ffxi-platform` | SHA-256 |
| --- | --- |
| `server/crates/forever-audit/src/detour_mset.rs` | `1cd9c8d9d540c704b84fd9f3c1d7c6006185fd96ea8e7f54cb3c2996456517ad` |
| `server/crates/forever-audit/src/detour_mset/tests.rs` | `52ac48f6be9b3796faeb60f57808b5aa0d55dde34e12a4dcaeb28942c17e84c2` |
| `docs/ffxi-detour-mset-adapter-20261115.txt` | `f4d9e49acd4c7e3b091aeb56a871970e1ccc17b6b23b308b9a90f92574af4eb0` |

Packet:
`/home/blizz/scratch-build/ffxi-detour-detail-boundary-5c73a875-source-test-20261115.tar.gz`,
39,847 bytes, SHA-256
`9f56d53b0053e59a87f1d75186e24d81a1e9fb2cdac2c8bb27cbcf1b7906876d`.
The 15 regular archive entries were read and hashed; all 14 entries declared
by its manifest match. No asset, tile or executable is supplied in this packet.
Its receipt is the neighboring directory's `RECEIPT.json`, SHA-256
`b7ad0d38cf57de1e3b58cfca72e41cf994fa2f02b9b058f7f6a5d9d6ecf08b1e`.

The source adds a bounded binary32 rounding-consistency allowance only for
extra detail vertices on marked boundary segments. It requires closed-segment
projection and caps the new allowance at `1e-5` source units. The report does
not propose a global EPS increase or snapping the payload. The exact producer
arithmetic cause remains **INFERRED**. Coarse convexity, unmarked detail points,
topology, winding/area, BV, ABI, hash and query restrictions remain in scope.

The owner reports three separate focused runs, which this refresh did not
execute again:

- Seven adapter tests pass, including synthetic native loading/query.
- Twelve retained interoperability cases pass, now accepting the unchanged
  owned tile `4ad75760178b7f7c2f518994a466df2f2b95e7e96780134598674ffa02378fb4`.
- Three deliberately corrupted owned copies are refused: outside detail point,
  inward point off its marked boundary and removed boundary flags.

The producer still requires backend
`d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`.
Build0002's `e2d9f8…` backend remains refused. Metadata now distinguishes
`contract_source_reference=ae73…` from the retained build0001 package source
`5e4ba6d…` and package manifest `3c96a311…`; none authenticates a compilation
HEAD. Tiled, 64-bit and wrong-hash refusals remain reported.

**Explicit limit:** owned FFXI native load/query and Game QA are **NOT RUN**.
The packet supplies a synthetic test-filter recipe
`cargo test --offline --locked -j2 -p forever-audit --lib detour_mset::tests:: -- --test-threads=1`,
not a recipe or result for loading the owned tile in FFXI. The source note's
earlier UNRUN paragraphs are retained historical sections; dated separate
receipts describe the newer offline checks. Source acceptance cannot upgrade
collision coverage, physical scale, agent calibration or omitted dynamics.

The next independent bot-core check can consume these exact source objects
and retained inputs. No server runtime, restart or install is authorized by
the packet.

## Other concrete deltas

| Lane | Change since 02:20 | Limit retained |
| --- | --- | --- |
| C1 FFXI | Lead accepts the shared C1/P0 handoff as independently ready input with no new map gate. | Actual current-native seam adoption/P0 still not reported complete. |
| Bot-core publisher `3f9392ca5d00` | No changed report; its latest remains Nov 11 b148 local-only launcher work. | No bot-core private publication, feed readback or receipt found. A local build0003 smoke is separate. |
| E&B `d30281403634` | At 02:26:48, lead retains `1/1/1/0`; commit `61da5b4` reports four model-local Recast tiles from actual W3D triangles and a short path across two tiles using shared build0003. Per-tile Recast/Detour is now the required output; obstacle/gate graphs are supplemental. | Complete sector coverage remains `0/85`; no sector transform, ship calibration, E&B native loader or Game QA. The former pathing-model decision is reported resolved, not a remaining blocker. |
| FF14 `87c294e006ae` | Reports private candidate `banshee-dev-0005-2d1e8708` staged with 43 focused tests and package readback. | No new four-piece scorecard, publication, actual-client/Game QA or ARR completion; owner data/Oodle still absent. |
| DCUO `3e436176e74c` | Reports refreshed distribution-manifest metadata. | No changed readiness scores or actual retail startup proof. |

There are no new attributed readiness scores in this bounded snapshot.
E&B evidence is an owning-lead report; this refresh does not rerun its geometry
or runtime checks.

## Holds and retained evidence

**Never restart FFXI servers.** The previously observed current owner hold
remains unchanged. A zero-player window does not restore restart authority.
`/home/blizz/dev/ffxi/handoffs/CURRENT-OPERATION-CONSTRAINTS.json` still hashes
to `506e5b447510761be446fd3c7208120b12b65cccdc0af1680f94d4478a9ed134`.
Existing access, player/progress, install and other action-time constraints
remain; a continuation relay or source-test pass does not lift them.

External snapshot directory:
`~/.local/share/banshee-bot-core/evidence/handoff-refresh-20261115-022915cst/`.

| Retained file | SHA-256 |
| --- | --- |
| `task-board.json` | `99942b22c5d23d30963bfacb9b4fb2b880c91372728be320f27dbe8f6360de89` |
| `selected-reports.json` | `15c6b2bf7809ff9ef9dea6ab456ae69effeb7adc2ed0708a7d1feafa8d1638a4` |
| `packet-source-verification.json` | `335ced217fe69eeef0c153e0415ea7c1f7147661c12aedb830bd2e4201115c13` |

The packet copy, receipt and exact three source snapshots also remain there,
outside git. Only this observation note enters the shared repository. No
test, native query, live action or publication was performed by this refresh.
