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

The later [FFXI export wrapper](FFXI_EXPORT.md) uses an immutable external
snapshot of owning source `a13dabcd550e0a777be5077804ba3d51683cfa19`, including
`forever-audit::geometry_export` and the existing reader attributed to
MIT-licensed `forever-client` `a8c75ab4e981d6056cd2860d8f8e12eacfff7671`.
The owning FFXI workspace has no blanket licence declaration. All dependency
source, exact licence, registry identities, binaries and owned assets stay
external; only the original wrapper/driver are committed and packaged here.
The [bounded bake evidence](FFXI_REGION_BAKE.md) records successful offline
geometry processing without claiming a full map, native integration or Game QA.

The [FFXI navigation compatibility check](FFXI_NAV_COMPATIBILITY.md) compiles
the unchanged owning `a13dabcd` `detour_mset.rs` externally (SHA-256
`5bf2638184ec007fde180a41f24646687572bb94185684056a7b39ec59c1fd5f`).
That private source declares no independent public licence. Only the original
test driver is committed here. Native detail-mesh source observations retain
the Recast zlib notice and exact input hashes alongside external evidence.

The [actual WoW preflight](WOW_NAV_PREFLIGHT.md) pins the owning cMaNGOS CMake,
MapBuilder and Detour reference-layout declarations. Its observed v8 artifacts
use the explicitly enabled 64-bit ABI, while the earlier standalone helper
compiles a 32-bit ABI. Both remain explicit profiles; no source implementation
was copied into this repository. Actual map files and bounded raw-payload
observations remain external and are not bundled with tool candidates.

The [selected WoW import](WOW_NAV_IMPORT.md) preserves those existing binary
payloads instead of regenerating geometry. Original Rust/Python orchestration
uses the explicit wrapper/ABI declarations, original map parameters and native
Detour query interface. Caller-supplied map names and flag masks remain
declarations; the importer does not authenticate a game producer or establish
movement policy. Per-file identities, flags/areas and query receipts stay in
the private evidence directory. No map payload is committed or bundled.

The [corrected FFXI consumption](FFXI_NATIVE_CONSUMPTION.md) selects immutable
owning commit `5c73a8751940ba767c7b86a50bb96b38b5d1e4f6` and verifies the
owner's source/test packet before compiling it externally. Its `detour-sys`
tree `f60ac5be2549c158730514f004218a168c76f907` vendors zlib-licensed Detour
`1078bfe3`; the inspected private binding package declares no separate licence.
Only the original caller/reproduction logic is committed here. Owning source,
native binary, asset inputs and query coordinates remain external. The exact
capacity contract and current production call-site evidence are recorded with
the result, without claiming server/client QA or changing native guards.

Explicit zone selection and retained exporter reuse preserve that same `a13`
reader and unchanged original Rust driver. Reuse checks the immutable git
objects, retained staged sources/lock, driver, executable and MIT attribution;
it records references rather than claiming to recreate source/compiler output.
The zone101 experiment uses an existing historical source-audit point and
explicit owner DAT path. Its source/asset identities, water/path refusals and
incomplete region limits are recorded in [the export evidence](FFXI_EXPORT.md).
No new format implementation or external code was imported into this repository.
