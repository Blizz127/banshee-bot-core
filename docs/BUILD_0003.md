# Private QA candidate 0.1.0-build0003

Created **2026-11-15 02:19:56 CST**. **QA_CANDIDATE, not released.**
Release build/startup and changed-feature checks: **PASS**.
Real FFXI wrapper compatibility: **FAIL/PARTIAL**.
Native `/fb` P0 and Game QA: **NOT_RUN**. New features: **OFF**.

| Item | Identity |
| --- | --- |
| Archive | `/home/blizz/.local/share/banshee-bot-core/builds/banshee-bot-core-0.1.0-build0003/banshee-bot-core-0.1.0-build0003.tar.gz` |
| SHA-256 | `a6331546f621a66ccda3246a70b388876ae3cba06f96043e53e2bf7f40b639c1` |
| Bytes | `785550` |
| Source commit | `c74312dee1701291263acafe54a8588abd998da1` |
| Manifest/checksum | Same build directory: `manifest.json`, `SHA256SUMS` |

This increment adds the original pinned-source FFXI export wrapper, native
wrapper compatibility reproduction, archive readback tooling, and the explicit
`cmangos-v8-ref64` map/tile inspection profile required by actual retained WoW
artifacts. The pure C1 core remains unchanged from its passing expanded
comparison. Source, tool binaries and selected evidence summaries are packaged;
game assets, raw geometry, client files and external dependency source snapshots
are not included.

## Verification and limits

- VERIFIED: clean release build, tool startup and synthetic soak refusal pass.
  Archive readback validates all **78** listed payloads, embedded manifest,
  exact archive size/SHA and seven packaged-tool checks. Receipt:
  `~/.local/share/banshee-bot-core/evidence/build0003-readback/result.json`,
  SHA-256 `81fd5292784de02c55667a6794bc6d5d04b1e47a255c0463dfe106a4297e5fec`.
- VERIFIED: the extracted release inspector passes all ten checks against two
  actual cMaNGOS map/tile pairs, including wrong-profile refusals. Original
  files remain unchanged. Receipt: the same directory's
  `wow-preflight/artifact-receipt.json`, SHA-256
  `e3596acd707b7b250025aa17a03ae6015d9fc08afaf1142bf967c71682204b83`.
- VERIFIED earlier: six focused parser tests, expanded C1 differential checks,
  32/64-bit synthetic native navigation checks and build0002 packaged tiled
  smoke. Those receipts retain their actual binary/source identities; they are
  not relabelled as repeated build0003 executions.
- OBSERVED/VERIFIED offline: the FFXI source export produces 1,821 real triangles;
  the packaged build0002 tool pair builds/reloads and queries a bounded single
  tile and four-cell collection. The final wrapper's later identity guards were
  independently checked; the initial export predates some metadata fields.
  See [export scope](FFXI_EXPORT.md) and [bake evidence](FFXI_REGION_BAKE.md).
- **FAIL/PARTIAL:** the unchanged FFXI wrapper rejects the real tile at one extra
  detail vertex's convex-boundary check. It also rejects the newer backend
  producer hash. Exact diagnosis and reproduction are in
  [FFXI compatibility](FFXI_NAV_COMPATIBILITY.md). No guard was bypassed and no
  real MSET was accepted. Native integration, dimensions, complete collision,
  actual-client QA and a live bot soak remain unverified.

## Superseding private publisher intake

**Supersedes build0002 as the proposed developer-tool package.** Preserve both
earlier builds for rollback. Route through coordinator task `dcc9a63a40ab` to
existing publisher project/session `claude-banshee-realm-client`, standing task
`3f9392ca5d00`. Publisher ownership and private channel/readback/update/rollback
requirements remain those recorded in [build0001](BUILD_0001.md).

These are Linux x86-64 developer tools with dynamic system runtime dependencies,
not a Windows client or playable game. The native helper remains **32-bit**;
the inspector's explicit 64-bit profile does not change the helper's ABI.
Python orchestration/export scripts require Python 3.11 for the complete tool
set. FFXI export additionally needs the owner's pinned local source, cached
Rust dependencies and private client files; it does not download them.

Entry points from the extracted top-level directory:

```text
bin/bnav-extract --help
bin/bnav-recast --help
bin/bot-soak --help
python3 source/scripts/bake_nav_collection.py --help
python3 source/scripts/export_ffxi_geometry.py --help
python3 source/scripts/check_ffxi_nav.py --help
```

There is no daemon, game-client launch or server restart. `bot-soak replay`
consumes recordings; it does not create headless sessions. The shared core is
source for the owning FFXI lead to integrate and run P0 against its reconciled
baseline. C2 remains behind that independent C1 gate.

The candidate is retained locally and ready for the existing private publisher.
No bot-core feed contract or publication/readback receipt is established here.
Nothing in this document labels it released or authorizes a live deployment.
