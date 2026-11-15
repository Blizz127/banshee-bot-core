# C1 FFXI adapter intake — 2026-11-15

Status: **PARTIAL, not deployed or Game QA verified**. This is an actionable
source integration proposal for the existing FFXI lead, routed through Devbox
task `dcc9a63a40ab`. It does not authorize a restart or alter any live gate.

**Additive authority-only adoption — OBSERVED source and closed test evidence:**
FFXI source `756eb1659d7a189273fd4d0a16c1bf568558c1d5` directly re-exports exact
shared db74 authority types/functions. The actual native authority module's
eight unchanged tests pass in an isolated offline crate. This establishes a
partial source adoption, not a full `xi-map` build, native Session/driver P0,
runtime-kit acceptance or Game QA. Command, selection, control and orders stay
native and unchanged per the saved source review. The shared authority file is
byte-identical to the current bot-core copy, SHA-256
`7b49a28fb5ecc294073634c9f729a58e845c3c9c19633eee391633f0549c10ae`.

The [existing intake's authority addendum](FFXI_OFFLINE_INTAKE.md#c-partial-authority-source-adoption)
records the exact packet, root and closed terminal. It supersedes only the af2
root-vendor layout. Existing e519/rc183 work, source-gap findings and the broader
comparison below are preserved. C1 remains independent of maps; no other shared
module is adopted by implication and no test was replayed for this intake.

**02:51 CST source reconciliation — VERIFIED offline:** the pinned reference candidate
is `5c73a8751940ba767c7b86a50bb96b38b5d1e4f6`. It changes command grammar,
fallback control transitions and geometry-setting orders relative to the
original pin below. Authority and selection remain byte-identical. The shared
extraction now covers those additions and passes the expanded comparison against
that exact candidate. Earlier equivalence receipts still apply only to
`36b90715`. This candidate is not a confirmed live baseline or native C1
acceptance receipt. The later authority-only adoption above does not change
this comparison's source pin or promote it to whole-adapter acceptance.
Evidence: `evidence/c1-source-drift-20261115-0247/result.json`, SHA-256
`85b39bb843aeb0e5cf7aeb36a75513df7aa3442c2abd65e2d1d04f6be1fee80b`,
beneath the private data root. Use the current source and receipt below when
integrating; do not substitute the older seam. Native geometry placement remains native.

The current comparison receipt is
`evidence/c1-current-compat-5c73a875-attempt1/result.json`, SHA-256
`dcecb524ad08d1c2c43e5ce009b9b3578270a299aad51003939086e76dbc38ea`.
It verifies 97,032 parser and 70 directed precedence comparisons, 87,040 clock
result/state comparisons, 112,802 authority/selection/order comparisons, and
1,136,900 formation-setting comparisons. Eleven original pure reference tests
and the shared overflow check pass. All six native files and shared-core inputs
remain byte-identical before/after. Nineteen integrated changed-core checks
also pass (`evidence/c1-current-integrated-20261115-01/result.json`, SHA-256
`579df0f17bc9cd8e006db0207bb5ac2bbe401f59b9a5186dfef4ce0a05206c87`).
These are finite offline checks, not whole-program equivalence or native P0.

The coordinator's additive db74/e519 source reconciliation is retained in
[the existing intake](FFXI_OFFLINE_INTAKE.md#b-closed-historical-c1-source-reconciliation).
It describes the older shared db74 primitives and their historical proof,
not a replacement verdict for build0006. The native features it identifies
must be preserved; no current e519 adapter/P0 acceptance is inferred from
either record. C1 source readiness remains independent of maps, and the
platform's already-running/prepared jobs are not retargeted or duplicated.

Native `formation` should re-export the coherent shared `Shape`, `Setting`,
`Config` and `decimal` types/functions while retaining native `desired` placement.
This avoids mixing nominally different setting types in `Order::Geometry` and
`Directive::Geometry`. Geometry directives retain the native setting readiness
exception after authority/session/control checks; they do not move a bot.
The new grammar covers fill/rally/pullback/fallback; native effects stay native.
Fallback replacement, owner-order interruption and binding loss preserve the
observed cancellation-clock semantics; durable operation fences remain closed
until native reconciliation.

```sh
python3 scripts/check_ffxi_compat.py --profile ffxi-5c73a875 \
  --source /home/blizz/dev/ffxi-platform-detour-detail-boundary-20261115/server/crates/xi-map/src/fb \
  --evidence /absolute/private/path/to/new-receipt-directory
```

The selected working source must match all six immutable pins. A later owning
change requires a new comparison, not an automatic profile upgrade. The command
unit tests use a recorded enum-only Role shim; full pinned modules are used by
the differential binaries. Native placement is excluded from the comparison.

## Exact extraction boundary

| Existing `xi-map/src/fb` surface | Shared surface | Adapter responsibility |
| --- | --- | --- |
| `control::{Clock,Token,Operation,Phase,Refusal,Snapshot}` | `banshee_bot_core::sched::control` | Retain one clock for the whole registered bot/map lifetime; supply verified binding revisions, cancel queues, verify actual operation completion. |
| `command::{parse,Command,Target,ParseError,MAX_COMMAND_BYTES,MAX_NAME_BYTES}` | `banshee_bot_core::brain::command` | Re-export types to preserve callers; consume errors as private system feedback. |
| `authority` pure contracts | `banshee_bot_core::brain::authority` | Supply authoritative owner binding, actor/session and party facts. Tickets remain opaque and cannot grant authority without fresh native facts. |
| `selection` pure contracts | `banshee_bot_core::brain::selection` | Supply the current owned candidate set; preserve unavailable-member feedback and private name resolution. |
| `orders` pure contracts, including `prepare` and `revalidate` | `banshee_bot_core::brain::orders` (`Role` also in `roles`) | Re-export the coherent authority/selection/planner type set together; retain native `ORDER_HELP`, scene collection, ability mapping, queues and execution. |
| `formation::{Shape,Setting,Config,decimal}` | `banshee_bot_core::brain::formation` | Re-export these pure setting contracts; retain `desired`, game coordinates, rotation, placement and movement natively. |

The first source candidate is commit
`36b90715b29728ecbccd2fee95493bbc7c14db29` from
`~/dev/ffxi-platform-tank-add-rescue-composed-20261115`. The full hash manifest
and observed contracts are in [the audit](C1_FFXI_SOURCE_AUDIT.md). This checkout
was selected for readable `/fb` source, not because it was verified as the live
or current integrator baseline. The owning lead must reconcile its actual
baseline before accepting the seam; changed files require a fresh comparison.

## No-behavior-change obligations

1. Preserve existing `/fb` feature flags and exact off path. Shared
   `FeatureFlags::default()` enables nothing and does not override server policy.
2. Keep native owner binding, PartyBook, session generation and target facts.
   Pure authority/selection functions can use the shared implementations after
   baseline reconciliation. A parsed name or cancellation token is not permission.
3. Preserve two checks of controlled work (admission and execution), and retain
   login generation separately from cancellation epochs. Never reconstruct the
   clock on logout, toggle or rebind. Disable/adoption must preserve or invalidate
   pending native work through the existing single writer.
4. Role changes preflight the entire group before advancing any clock, retain
   explicit owner orders and keep native election semantics. `Puller` and
   `Dps` remain accepted; the broader `PolicyRole::Support` is not an FFXI verb.
5. Preserve preparation/revalidation call sites and their fresh native facts.
   The pure planner can be re-exported; ability mapping, claim observation,
   pull continuation, queues, packets and all gameplay mutation stay native.
   `Assist` uses the supplied elected tank and target; it invents neither.
   Role metadata must not overwrite an owner order.
6. Keep summon/gear/dismiss fences closed on unknown outcomes. A queued transfer
   is not arrival; a queued leave is not completed dismissal. Reconciliation
   requires the current token and actual native state.

The crate's `Clock::initially_detached` and `Clock::can_order` are public so the
adapter can use the same formerly crate-private helpers across the crate boundary.
Their semantics remain unchanged. The clock is intentionally not `Clone` and
does not expose deserialization, reset or token injection APIs.

## Focused acceptance

- Differential comparison of both parsers and public clock transitions against
  the pinned source, including malformed input and stale/rebound work.
- Pure local tests cover overflow without wrapping and nonmutating group
  preflight. These are not real-server P0 results.
- FFXI lead runs its authoritative focused `/fb` native checks on its current
  composed baseline, including role preservation, stale work, lifecycle fences
  and first invitation. Existing test names are listed in the source audit.
- Game QA Bot checks `/fb` in the actual supported server/client and reports
  the build identity. C1 must pass before C2 persona adoption.

Any live installation remains owned by the FFXI lead, with zero players,
backup/readback/rollback and all existing holds. The current owning instruction
is **Never restart FFXI servers**; zero players does not restore that authority.
See `/home/blizz/dev/ffxi/AGENTS.md:3` and its
`handoffs/CURRENT-OPERATION-CONSTRAINTS.json`. This is an existing owner hold
newly reconciled in current reports, not a new authorization to install/reload.
Source and offline P0 preparation may continue independently. This repo has made no live
changes and cannot certify that those deployment conditions are satisfied.

## Initial comparison result

**VERIFIED locally, 2026-11-15 01:11 CST:** 39,862 input cases produced 79,724
matching parser results. 128 control traces exercised 38,400 steps and compared
76,800 results/snapshots across all twelve public transition/admission methods.
Eleven original pure tests (six clock, five command) and the shared overflow
test passed. This finite deterministic corpus is not exhaustive equivalence.

Receipt:
`~/.local/share/banshee-bot-core/evidence/c1-compat-build-0001-attempt-2/result.json`,
SHA-256 `1b5fd72b1a8bef3ac958b49f53e824de83d024260ad8782714815a0eeb11143a`.
Source hashes were stable before/after the check. An earlier harness compilation
error was fixed and its failed receipt retained separately; no production code
change was needed. Repeat against a reconciled source only when its pins or the
shared primitives change:

```sh
python3 scripts/check_ffxi_compat.py \
  --profile ffxi-36b907 --core /absolute/path/to/historical-core \
  --source /absolute/path/to/xi-map/src/fb \
  --evidence /absolute/private/path/to/new-receipt-directory
```

The script refuses unrecognized source hashes and existing evidence directories.
Snapshots, compiler output and original test binaries remain outside both repos.

## Expanded comparison and superseding intake

**VERIFIED locally, 2026-11-15 02:05 CST:** the expanded harness adds 47,524
authority, selection, order preparation and fresh-state revalidation comparisons.
It includes 3,643 prepared outcomes, 859 per-bot refusals, successful operations,
and stale binding/session/claim/target mutations. The original parser, clock,
eleven reference pure tests and shared overflow checks also pass. Nine focused
shared authority/planner tests passed separately. This is finite local evidence,
not native P0 or whole-program equivalence.

Receipt:
`~/.local/share/banshee-bot-core/evidence/c1-planner-compat-build0002-attempt1/result.json`,
SHA-256 `2b15ac4441095abf928b25a37e09e39b65eb6958767d3051a2d8407e2c3c7d07`.
The before/after core source hashes match. The five pinned native files remain
the same candidate baseline; this does not establish compatibility with later
FFXI edits.

This expanded source intake supersedes the build0001 grammar-only proposal.
Integrate all interacting types together rather than mixing private native and
shared `MutationTicket`, `Candidate`, `Order` or `Role` definitions. The owning
lead may keep the earlier narrow extraction if its composed baseline has moved,
but must record which boundary it adopted and run its focused P0 checks. The
shared core performs no server action and does not replace the native single
writer or a current authority check at execution.

