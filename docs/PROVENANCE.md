# Provenance

All application code authored here is original. External code is not copied
into this repository. Private game data and source snapshots used for checks
live under `~/.local/share/banshee-bot-core/`, outside git. Licence notes record
observed source notices, not a new licence grant for this private project.

| Source | Use | Licence / evidence |
| --- | --- | --- |
| FFXI private `ffxi-platform` `/fb`, candidate `36b90715b29728ecbccd2fee95493bbc7c14db29` | Behavioral reference for cancellation clock, role vocabulary, parsers, ownership, selection and pure order planning; original implementation here. | No root licence or package licence field found in the bounded source audit; private-project permission, redistribution terms unspecified. `fb/mod.rs` attributes early native grammar/authority/listing contracts to DIT r8 `456837be`. See [audit](C1_FFXI_SOURCE_AUDIT.md) for exact file hashes and scope. |
| [cMaNGOS Playerbots engine](https://github.com/cmangos/playerbots/blob/master/playerbot/strategy/Engine.cpp) | Studied strategy/trigger/action organization and useful/possible action checks; no translated/copied code. | GPL-family upstream lineage; no licence file identified in the inspected playerbots root. Confirm each source notice before any future copying/linking; none occurs here. |
| [AzerothCore mod-playerbots](https://github.com/mod-playerbots/mod-playerbots) | Architectural reference required by the spec; no linked/copied implementation. | [GPL-2.0 licence text](https://github.com/mod-playerbots/mod-playerbots/blob/master/LICENSE). |
| [Recast/Detour](https://github.com/recastnavigation/recastnavigation) | Navigation format/API reference; any native backend build must retain external source identity and notice. | [zlib-style licence](https://github.com/recastnavigation/recastnavigation/blob/main/License.txt), copyright Mikko Mononen. Tool-specific profiles, pinned local sources and limitations belong in `BNAV_EXTRACT.md`. |
| [cMaNGOS mmap wrapper](https://github.com/cmangos/mangos-classic/blob/master/src/game/MotionGenerators/MoveMapSharedDefines.h) and [AzerothCore wrapper](https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/common/Collision/Maps/MapDefines.h) | Format layout references for original `bnav-extract` inspectors; no implementation copied. | GPL-2.0-or-later notices observed in local declarations. Source revisions and header SHA-256 values are pinned in [nav tool provenance](BNAV_EXTRACT.md). |
| [Lumina](https://github.com/NotAdam/Lumina) | Future FFXIV sqpack format reference; no decoder or assets imported. | [WTFPL v2](https://github.com/NotAdam/Lumina/blob/master/LICENSE), inspected 2026-11-15. No FF14 game-data decoding has been performed. |

The governing spec itself is owner-supplied, with SHA-256
`fe8138bb5bec23f55f26060626f28c76aff9d64b54b24ec0b8cd9cb2b0a43bc3`.
This initial Rust core has no third-party Cargo dependencies. No public licence
or publication decision is made by these notes.

The build0001 native `bnav-recast` helper statically links the owner's existing cMaNGOS
Recast/Detour dependency (32-bit polygon references). Its complete input hash
manifest and licence are retained at
`~/.local/share/banshee-bot-core/evidence/nav-backend-20261115/build-cmangos-final/`.
The private candidate includes `manifest.json` and `RECAST-LICENSE.txt` from that
build alongside the original bridge source. The helper SHA-256 is
`d9996beda74bb7168198392040341e4823ff20b34c64da38bcca3dfca8f36e5c`.
At build0001, the optional 64-bit pipeline had only wrapper inspection evidence.
The later [ABI verification](NAV_ABI_VERIFICATION.md) records a full synthetic
64-bit pipeline pass against pinned AzerothCore Recast/Detour sources, including
single and tiled queries. Its backend SHA-256 is
`b32097eb8e9205ee51b1738129a15e4ffe8cad211d2ad61a4576ee76a725fcfb`.
This separately built helper does not change FFXI's 32-bit adapter contract.

The tiled 32-bit backend retains the same external licence and records every
input hash in `evidence/tiled-nav-20261115/backend-v2/manifest.json` under the
private data root. Its SHA-256 is
`e2d9f815d5354fc3612f4498ae424c76ef4ff461af3ad8fe293eb9ffb5c85818`.
FFXI collision source lineage, source licence scope, coordinate conventions and
owner asset identities are recorded in [the geometry audit](FFXI_GEOMETRY_EVIDENCE.md).
That audit establishes available source interfaces; it does not claim a decoded
asset or tested walking map.
