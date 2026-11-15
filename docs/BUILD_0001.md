# Private QA candidate 0.1.0-build0001

Created **2026-11-15 01:15:02 CST**. Status: **QA_CANDIDATE, not released**.
Native FFXI P0 and Game QA: **NOT_RUN**. New feature defaults: **OFF**.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0001/banshee-bot-core-0.1.0-build0001.tar.gz` |
| SHA-256 | `bfe62b4fa37fe807d28009c8906f7f5a71404af8ef9097cae4a5d52d421f525e` |
| Bytes | `679264` |
| Source commit | `5e4ba6d6bd961a6915154e6d3f0ad3f6c3b60281` |
| Manifest | Same build directory, `manifest.json` |
| Archive checksum file | Same build directory, `SHA256SUMS` |

Contains original source, release Rust CLI tools, the native Recast helper,
third-party dependency licence/manifest and selected verification receipts.
The core library is supplied as source for in-process server integration; this
is a developer-tool package, not a playable client or running game service.
No proprietary game geometry, accounts or captures are included.

## Verified scope

- Release build of all three Rust crates and CLI startup checks passed.
- Four core tests, four nav tests and six soak tests passed in their focused
  development checks. No routine whole-game suite was run.
- Pinned-source compatibility: 79,724 parser comparisons and 76,800 clock
  result/state comparisons matched; eleven original pure tests plus shared
  overflow test passed. See [C1 handoff](C1_ADAPTER_HANDOFF.md).
- Archive readback checked all 51 manifest entries by hash and byte size, plus
  the embedded manifest. Receipt:
  `~/.local/share/banshee-bot-core/evidence/build0001-readback/readback.json`.
- The binaries read back from the archive passed the synthetic single-tile
  floor/wall/disconnected route smoke and rejection checks. Receipt:
  `~/.local/share/banshee-bot-core/evidence/build0001-readback/nav-smoke/result.json`;
  detailed command output is beside it in `commands.json`.
- Synthetic soak startup remains exit 3 / INCOMPLETE, as required. No live
  telemetry is substituted for that fixture.

Unverified: actual server adapter behavior, proprietary geometry extraction,
multi-tile world coverage, a real hour-long N-bot soak, C2–C6 and actual-client
Game QA. Native builder end-to-end evidence uses 32-bit Detour references.

## Publisher intake

**First bot-core publisher intake; supersedes none.** Route through coordinator
task `dcc9a63a40ab` to the existing owner:

- Project/session: `claude-banshee-realm-client`.
- Workspace: `/home/blizz/dev/banshee-realm-client`.
- Existing standing publisher task: `3f9392ca5d00`.
- Current project mapping is Codex thread
  `01a1cbf1-769a-7982-8b67-a24bf86327a5`; route by owner project/session rather
  than assume its historical provider. Do not launch a replacement worker.

The configured owner and its artifact intake requirements were inspected
read-only. See that project's `AGENTS.md:207–212` for uploaded size/hash readback,
private build identity/launch contract, launcher update detection and rollback.

Entry points after extracting the archive's top-level directory:

```text
bin/bnav-extract --help
bin/bot-soak --help
bin/bnav-recast --help
```

`bnav-extract build-obj` requires an explicit path to the bundled `bnav-recast`
and private triangulated geometry; `bot-soak replay` requires a private CSV
recording. There is no daemon entry point and no server restart requirement.
Do not present the tool bundle as a playable game build. Retain the candidate
hash and all existing rollback artifacts when publishing through the owner's
appropriate private tools channel.

**Publication blocker:** no bot-core private feed/launcher entry contract exists
in this repo, and the existing Banshee Client Bot owns that integration. The
concrete package is ready for its intake; private publication and launcher
readback have not occurred here. Coordinator reports are saved on the task
board, but native notification is unavailable and owner-lane receipt is unconfirmed.

## Other pending intakes

These retain the earlier scopes; this build does not issue competing tasks.

- FFXI lead: [exact C1 integration seam and checks](C1_ADAPTER_HANDOFF.md),
  baseline confirmation and native P0/Game QA before C2.
- SWTOR, DCUO and Earth & Beyond owning leads: [maps-first C0 intakes](BOT-READINESS.md),
  preserving existing holds and E&B's pending free-flight design decision.
- Geometry exports: [common intake contract](GEOMETRY_CONTRACT.md).
