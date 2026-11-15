# Private QA candidate 0.1.0-build0004

Created **2026-11-15 02:38:16 CST**. **QA_CANDIDATE, not released.**
Release/startup, packaged navigation checks and offline corrected FFXI library
consumption: **PASS**. Native `/fb` P0 and Game QA: **NOT_RUN**.
New features remain **OFF**.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0004/banshee-bot-core-0.1.0-build0004.tar.gz` |
| SHA-256 | `ec77350799557ccc7f2ad083a3c2651dbbbab2c3e1f642dc29443a9e5f12bf21` |
| Bytes | `975402` |
| Source commit | `fe57f2240a2331c01a1eed9835bb867c5a7989a2` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

This increment preserves and imports explicitly selected WoW map/tile files,
queries them with caller-selected movement flags, and packages separate 32-bit
and 64-bit Detour-reference helpers. It also consumes the corrected owning FFXI
wrapper and native library offline. The pure C1 core remains unchanged from its
passing expanded comparison. Private game files, geometry and external source
snapshots are excluded from the archive.

## Verification and limits

- VERIFIED: clean release/startup checks and synthetic soak refusal pass.
  Archive readback validates all **90** payloads and **nine** packaged startup
  checks, including both native ABIs. Receipt:
  `evidence/build0004-readback/result.json`, SHA-256
  `5256ff171bb315cb7bd4e9886d99c9c3a2e382c81c3fbc9b9b3f2c5920de8432`.
- VERIFIED: **20** packaged native navigation checks pass against explicitly
  selected retained WoW files, including complete cross-tile routing and
  profile, selection, filter and malformed-input refusals. Receipt:
  `evidence/build0004-readback/wow-query/query-receipt.json`, SHA-256
  `7813d96d950ce3849e187efad95e5b8921c20a7f327640232459c975e2736259`.
  Whole-map coverage, off-mesh traversal and game movement remain unverified.
- VERIFIED: three additional import/readback/query commands pass with packaged
  tools and two explicitly selected real tiles. Receipt:
  `evidence/build0004-readback/wow-import-smoke.json`, SHA-256
  `d70de2d1fc0b528a2fdaef1846e8b1d517847eb9458cfd81c5d1d7abf8f4225f`.
  Original map parameters, tile payloads and different vertical bounds are
  preserved. Unselected cells remain unknown.
- VERIFIED earlier in this increment: the FFXI owner's corrected source
  `5c73a875` passes 12 compatibility cases and six focused tests. Its exact
  native library loads the unchanged real tile, returns 46 valid nearest
  queries and completes a corridor and straight path. Receipt:
  `evidence/ffxi-owned-native-5c73-20261115-attempt2/result.json`, SHA-256
  `2aa4dcfe08bc4da907b72c35aa1955488be344a389acecdaf229fe1a88aed367`.
  This was not repeated as a packaged-tool execution. See
  [native consumption](FFXI_NATIVE_CONSUMPTION.md) for the exact source pins,
  explicitly filtered capacity16 test and 512-entry native-call contract.
- The accepted FFXI producer remains the retained build0001 backend. Although
  the new 32-bit helper produces identical raw bytes for the same real crop,
  its producer hash still requires owning-lead review. No guard was waived.
  Complete geometry, physical/agent calibration, native C1 adoption/P0, live
  bot soak and Game QA remain unrun.

Evidence paths above are relative to
`/home/blizz/.local/share/banshee-bot-core/`.

## Superseding private publisher intake

**Supersedes build0003 as the proposed developer-tool package.** Retain previous
candidates for rollback. Route through coordinator task `dcc9a63a40ab` to the
existing publisher `claude-banshee-realm-client`, task `3f9392ca5d00`, using its
existing private channel. Publication/update/readback remains that owner's
work; no bot-core feed contract or publication receipt is established here.

These are Linux x86-64 developer tools with dynamic system dependencies.
Python 3.11 supports the complete script set. They are not playable clients.
`bin/bnav-recast` uses 32-bit references; `bin/bnav-recast64` uses 64-bit
references. The archive manifest verifies each independently.

```text
bin/bnav-extract --help
bin/bnav-recast --help
bin/bnav-recast64 --help
bin/bot-soak --help
python3 source/scripts/import_wow_nav.py --help
python3 source/scripts/check_ffxi_nav.py --help
```

The manifest embeds the standing **never restart FFXI servers** hold, including
at zero players. No install/reload authority is granted. The newer authority
supersedes historical restart assumptions in archived source documents.
Native C1 adoption and P0 remain with the owning FFXI lead, independently of
map work. This candidate advances offline tooling, not later gameplay phases.
