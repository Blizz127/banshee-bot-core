# Banshee Bot Core

Private shared Rust bot primitives and offline navigation/load-test tools.
Governing scope: [spec](docs/BANSHEE_BOT_CORE_SPEC_20261115.md).

**C1 is partial.** The shared library implements the existing FFXI cancellation
clock, roles and `/fb` command/order grammar. Native authorization, selection,
planning, target claims, session handling and gameplay execution remain in the
FFXI server. No server has adopted this crate yet; no live P0 or Game QA pass is
claimed. New feature switches default off.

```sh
nice -n 19 cargo build --locked -j2
nice -n 19 cargo test --locked -j2 -p banshee-bot-core --lib
```

The crate uses only Rust's standard library and never opens a network connection.
`brain/`, `roles/` and `sched/` contain the first compatibility slice; `nav/`
defines the native query boundary. `goals/`, `economy/`, `chat/` and `persona/`
reserve the specified architecture without claiming later-phase behavior.

`bnav-extract` provides explicit WoW tile preflight and common-geometry input
validation; see [nav tool status](docs/BNAV_EXTRACT.md) and the
[geometry intake contract](docs/GEOMETRY_CONTRACT.md). `bot-soak` validates and
summarizes a server adapter's recorded metrics; see its
[CSV contract and coverage checks](docs/BOT_SOAK.md). It does not spawn bots.

See [FFXI source audit](docs/C1_FFXI_SOURCE_AUDIT.md),
[adapter handoff](docs/C1_ADAPTER_HANDOFF.md),
[readiness table](docs/BOT-READINESS.md),
[provenance](docs/PROVENANCE.md) and [progress](docs/PROGRESS.md).
Game data, extracted geometry, binaries and evidence stay outside git under
`~/.local/share/banshee-bot-core/`. No public release or repository remote.

