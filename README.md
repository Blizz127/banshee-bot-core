# Banshee Bot Core

Private shared Rust bot primitives and offline navigation/load-test tools.
Governing scope: [spec](docs/BANSHEE_BOT_CORE_SPEC_20261115.md).

**C1 is partial.** The shared library implements the pinned FFXI cancellation
clock, roles, `/fb` grammar and pure ownership, selection and order planning
contracts. Target claims, session facts and gameplay execution remain in the
FFXI server. FFXI source 04b715eb now adopts the coherent shared 6ead type set,
with 46/0 isolated native-module results and two separate overflow passes.
The original e519 native run is separately reported at 9 passed / 3 failed;
fixes, full adapter/P0 and Game QA remain pending. New feature switches default off.
The newer observed native source's fallback, commands and formation settings
now pass an explicit source comparison. Source adoption does not establish
current native integration/P0 or gameplay acceptance.

```sh
nice -n 19 cargo build --locked -j2
nice -n 19 cargo test --locked -j2 -p banshee-bot-core --lib
```

The crate uses only Rust's standard library and never opens a network connection.
`brain/`, `roles/` and `sched/` contain the first compatibility slice; `nav/`
defines the native query boundary. `goals/`, `economy/`, `chat/` and `persona/`
reserve the specified architecture without claiming later-phase behavior.
The pure [decision policy](docs/DECISION_POLICY.md) adds bounded strategy
proposal ordering and restricted optional advice for future adapters. Native
FFXI integration and its existing C1 source candidate remain separate.
The optional [strategy-frame interface](docs/STRATEGY_FRAMES.md) supplies bounded
callback evaluation and immutable proposals for that selector.
The additive [role-election helper](docs/ROLE_ELECTION.md) computes pure choices
from adapter-supplied preferences; native FFXI role state and atomic updates
remain unchanged pending separate adoption.

`bnav-extract` builds single or fixed-grid Recast/Detour tiles from extracted
triangle geometry and provides explicit WoW tile preflight; see
[tiled navigation](docs/TILED_NAV.md), [nav tool status](docs/BNAV_EXTRACT.md) and the
[geometry intake contract](docs/GEOMETRY_CONTRACT.md). `bot-soak` validates and
summarizes a server adapter's recorded metrics; see its
[CSV contract and coverage checks](docs/BOT_SOAK.md). It does not spawn bots.

The [FFXI offline export wrapper](docs/FFXI_EXPORT.md) builds or verifies and
reuses the existing pinned reader outside Git, with explicit zone/DAT selection.
Its first bounded zone230 geometry has been
[baked and queried locally](docs/FFXI_REGION_BAKE.md). Collision completeness,
physical calibration and native/client QA remain unverified.
The corrected owning FFXI wrapper and native library now
[load/query that retained tile offline](docs/FFXI_NATIVE_CONSUMPTION.md);
this does not satisfy server P0 or actual-client QA.
Existing owner WoW artifacts have [explicit ABI preflight evidence](docs/WOW_NAV_PREFLIGHT.md);
`cmangos-v8-ref64` selects the observed retained cMaNGOS map format.
The [selected-map importer](docs/WOW_NAV_IMPORT.md) retains those raw tiles and
queries an explicitly bounded selection with a matching native backend.
Both collection and selected-map queries report
[endpoint projection distances](docs/NAV_ROUTE_METRICS.md), with an optional
caller-specified limit that can reject a complete but displaced path.
The Rust navigation boundary also provides optional
[route measurements](docs/NAV_CORE_METRICS.md) for future in-process adapters.

See [FFXI source audit](docs/C1_FFXI_SOURCE_AUDIT.md),
[adapter handoff](docs/C1_ADAPTER_HANDOFF.md),
[readiness table](docs/BOT-READINESS.md),
[provenance](docs/PROVENANCE.md) and [progress](docs/PROGRESS.md).
Private QA-candidate packaging is documented in [builds](docs/BUILDS.md).
The current proposed private tool/source candidate is [build0013](docs/BUILD_0013.md);
publication and native/Game QA remain separate pending steps.
Game data, extracted geometry, binaries and evidence stay outside git under
`~/.local/share/banshee-bot-core/`. No public release or repository remote.

