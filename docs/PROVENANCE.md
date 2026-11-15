# Provenance

All application code authored here is original. External code is not copied
into this repository. Private game data and source snapshots used for checks
live under `~/.local/share/banshee-bot-core/`, outside git. Licence notes record
observed source notices, not a new licence grant for this private project.

| Source | Use | Licence / evidence |
| --- | --- | --- |
| FFXI private `ffxi-platform` `/fb`, candidate `36b90715b29728ecbccd2fee95493bbc7c14db29` | Behavioral reference for cancellation clock, role vocabulary and parsers; original implementation here. | No root licence or package licence field found in the bounded source audit; private-project permission, redistribution terms unspecified. `fb/mod.rs` attributes early native grammar/authority/listing contracts to DIT r8 `456837be`. See [audit](C1_FFXI_SOURCE_AUDIT.md) for exact file hashes and scope. |
| [cMaNGOS Playerbots engine](https://github.com/cmangos/playerbots/blob/master/playerbot/strategy/Engine.cpp) | Studied strategy/trigger/action organization and useful/possible action checks; no translated/copied code. | GPL-family upstream lineage; no licence file identified in the inspected playerbots root. Confirm each source notice before any future copying/linking; none occurs here. |
| [AzerothCore mod-playerbots](https://github.com/mod-playerbots/mod-playerbots) | Architectural reference required by the spec; no linked/copied implementation. | [GPL-2.0 licence text](https://github.com/mod-playerbots/mod-playerbots/blob/master/LICENSE). |
| [Recast/Detour](https://github.com/recastnavigation/recastnavigation) | Navigation format/API reference; any native backend build must retain external source identity and notice. | [zlib-style licence](https://github.com/recastnavigation/recastnavigation/blob/main/License.txt), copyright Mikko Mononen. Tool-specific profiles, pinned local sources and limitations belong in `BNAV_EXTRACT.md`. |
| [Lumina](https://github.com/NotAdam/Lumina) | Future FFXIV sqpack format reference; no decoder or assets imported. | [WTFPL v2](https://github.com/NotAdam/Lumina/blob/master/LICENSE), inspected 2026-11-15. No FF14 game-data decoding has been performed. |

The governing spec itself is owner-supplied, with SHA-256
`fe8138bb5bec23f55f26060626f28c76aff9d64b54b24ec0b8cd9cb2b0a43bc3`.
This initial Rust core has no third-party Cargo dependencies. No public licence
or publication decision is made by these notes.
