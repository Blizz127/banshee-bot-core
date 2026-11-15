# C1 FFXI source audit

2026-11-15 CST. Task `dcc9a63a40ab`. Verdict: **PARTIAL**. This is a
read-only source audit for original implementation of the shared core, not an
FFXI adapter change, runtime verification, or completed C1 migration.

## Source identity and limits

**OBSERVED:** `/home/blizz/dev/ffxi-platform` is on `main` at
`faa18b85a4338cbf4d09843377d78797bcd979fa`, with unrelated working changes.
Its source predates the current native `/fb` implementation. Do not assume the
main worktree is the current integration or deployed source.

The bounded audit used this existing, read-only candidate:

- Root: `/home/blizz/dev/ffxi-platform-tank-add-rescue-composed-20261115`.
- Detached commit: `36b90715b29728ecbccd2fee95493bbc7c14db29`.
- Commit subject: `Compose retained Tank add-rescue onto current WS source`.
- Commit time: 2026-11-14 08:42:12 PM CST.
- Scoped diff against HEAD for the six production files below: empty.

| File relative to candidate root | SHA256 |
| --- | --- |
| `server/crates/xi-map/src/fb/control.rs` | `6db0a98b3b14ebaff78354192400b2d92591cfa7fef50c39617c2eb16020835e` |
| `server/crates/xi-map/src/fb/command.rs` | `34480a234e86b7a28731ebd56d1135bd42771cfba513a8f1bf81ef81ce2939be` |
| `server/crates/xi-map/src/fb/orders.rs` | `b236c09b5c9f88b102560106ccfe4de3bf979d8d045c31fdf4157ad8c10db469` |
| `server/crates/xi-map/src/world/bot_roles.rs` | `61fe48642edf8cd596c69908db4fa4a87434a8dac686c13b759d3a71aaf8f753` |
| `server/crates/xi-map/src/world/bot_control.rs` | `92a087dbae910b814ee91c7282f492c3a8e291dd0b4064a1c6e51b55c69ffa78` |
| `server/crates/xi-map/src/bot.rs` | `0193c3a2c057ee04df94e0078f8282badacb726e178965cc938654df4c382f4e` |

The broader path/hash manifest is outside git at
`/home/blizz/.local/share/banshee-bot-core/evidence/c1-source-audit-20261115/source-manifest.json`.
The last change touching `control.rs` is
`d4a4d82867d513615a88b7f7ade929ef7a9bb07e` (2026-11-14 05:19:59 PM CST,
opt-in first-invite custody). The last change touching `orders.rs` is
`3274c7e8ef8d0ea9cefdc62f9bf00ea0051cdf2c` (2026-11-11 08:32:58 PM CST,
Pull return help).

**Unknown:** which composed commit the FFXI lead currently integrates and which
binary is installed. The adapter owner must confirm the pin before integration;
this does not prevent building and comparing the pure modules now.

## Control clock contract

**OBSERVED:** `fb/control.rs:13-247` is a pure cancellation state machine using
only `std::num::NonZeroU64`. This clock is an epoch counter, not wall time.
There is no duration, timestamp unit, deadline, or token TTL in this module.
Invitation expiry is a native event supplied by the adapter.

- Token: `binding_revision: u64` plus `epoch: u64`.
- Phases: `Legacy`, `Active`, `Fenced(Gear|Summon|Dismiss)`, `Detached`,
  `Invited`, `Exhausted`.
- Default: Legacy, epoch zero, binding revision zero; snapshot has no token.
- Explicit opt-in enrollment: Detached, epoch one, binding revision zero.
- Every successful transition increments the epoch with checked arithmetic.
  Overflow sets Exhausted permanently without wrapping.
- Preserve one clock for each registered bot throughout the map incarnation,
  including its logout/relogin. Native session generation is a separate check.
- A snapshot token is not authority, queue cancellation, or success evidence.

| API | Observed behavior |
| --- | --- |
| `begin(operation, binding)` | Legacy or Active with matching binding becomes Fenced; a different Active binding is Stale; other phases are Closed except Exhausted. |
| `order(binding)` | Same eligibility as begin, then Active with a new epoch. Cannot interrupt a pending operation. |
| `can_order(binding)` | Same eligibility and overflow preflight, without changing state. Used before an atomic role election. |
| `summon_arrived(token)` / `summon_reconciled(token)` | Requires exact current Summon fence and nonzero binding, then Active with a new epoch. Actual arrival/reconciliation is the caller's responsibility. |
| `gear_finished(token)` | Requires exact current Gear fence and nonzero binding. Only called after committed/refreshed state or proven rollback. |
| `summon_abandoned(token)` | Requires current Summon fence; becomes Detached if unbound, otherwise Active. This is not a summon success receipt. |
| `dismiss_completed(token)` | Requires current Dismiss fence; becomes Detached with binding zero after actual native leave. |
| `binding_changed(actual)` | Legacy returns no change. Identical revision returns no change. Changed revision increments epoch and preserves any pending fence; otherwise becomes Active when bound or Detached when unbound. |
| `human_invitation()` | Only Detached can become Invited. Must follow validation of an actual human invitation. |
| `invitation_finished(token, binding)` | Exact current Invited token becomes Active with supplied binding or Detached without one. |
| `admit(token, party_accept)` | Legacy accepts only absent token. Managed control requires a token, exact identity, then Active or Invited with actual party-accept intent. Other current phases are Closed. |

Failure ordering matters: managed admission checks missing token before checking
Exhausted; current-token checks report Exhausted before token mismatch; completion
checks compare token before checking operation. Original code and differential
checks must preserve these distinctions.

## Command and order grammar

**OBSERVED:** `fb/command.rs:7-98` owns first-slice commands; `fb/orders.rs:62-123`
only receives its `UnknownSubcommand` result. Preserve this composition.

1. Scan leading ASCII whitespace to recognize the case-insensitive exact `/fb`
   token. A following byte must be absent, ASCII whitespace, or ASCII control.
   `/fbar` and other unrelated input return `Ok(None)` before size/text checks.
2. Recognized raw input over 200 bytes is `TooLong`. Otherwise every byte must
   be printable ASCII `0x20..=0x7e`, including leading/trailing bytes. Tabs,
   newlines, NUL, DEL and non-ASCII text are refused, not normalized away.
3. Split only literal spaces, ignoring empty words. No quoting is supported.
4. Bare `/fb` means Help; help/list accept no arguments. Summon/dismiss accept
   zero arguments or `all`, otherwise one alphabetic name of at most 16 bytes.
5. Orders forwards only `TooLong` and `InvalidText` as grammar errors. Every
   other first-parser result besides `UnknownSubcommand`, including malformed
   first-slice commands, remains owned by the first parser (`Ok(None)`).
6. Follow, Stay, Rest, Attack, Pull and Assist accept no arguments.
7. Role requires one name and one role; extra arguments are refused before name
   validation. `all` is not a role target. Name spelling/case is retained.
   Accepted roles are case-insensitive `tank`, `healer`, `dps`, `puller` only.

No grammar result establishes ownership or changes gameplay. Keep
`fb/authority.rs`, `selection.rs`, `orders::prepare` and `orders::revalidate`
in the FFXI adapter for the first extraction increment. The native caller
supplies coherent authenticated game-thread facts and revalidates at execution.

## Roles versus retained orders

**OBSERVED:** `world/bot_control.rs:66` stores the owner's persistent policy as
Follow(actor), Stay, Rest, Attack(target), or Pull(target). Assist resolves to an
Attack target; a role is independent metadata, not a replacement movement order.

`begin_bot_order` at line 341 validates actual binding/human ownership, advances
the clock, replaces the explicit order and clears obsolete navigation/defense
custody and queued default-follow admission. `begin_bot_role_epoch` at line 414
advances the clock while retaining explicit owner policy and approved native
continuations. Replacing both with a generic "set goal" would change behavior.

`world/bot_roles.rs:10-180` stores job, manual role and elected role scoped to the
full native owner binding. Zoning preserves it; leave/rebind clears it. All
changed clocks are preflighted before an election commits any assignment.

Observed automatic job preference, which belongs in FFXI data/adapter policy:

- One party Tank, ordered by native job IDs 7, 13, 1, 8, then actor ID; a manual
  Tank suppresses automatic selection. An owner cannot replace another owner's
  manual Tank.
- Job 3 is Healer; job 5 is Healer only without a qualifying job-3 healer.
- Per-owner automatic Puller preference is job 6 then 11, then actor ID; manual
  Puller choices suppress that owner's automatic election.
- Other known jobs become Dps. Missing job does not invent a role. Manual
  choices override automatic classification.

Do not add a Support role to the existing `/fb role` vocabulary during C1.
The wider game-neutral role model can express support separately without
changing FFXI command acceptance.

## Headless session and adapter seam

**OBSERVED from source, not a fresh runtime test:** `bot.rs:1-40` and the native
implementation use a real in-server `Session`. A pseudo-peer is an internal
session-map key, not a bot network client. The bot's intents reach native
`Session::handle_direct`, which retains ordinary spell, recast, claim, party and
progress validation. Native code owns session creation and persistence.

Keep packet encodings, pseudo-peer addresses, login paths, database access,
FFXI job/ability IDs, world mutation, navigation custody, and success receipts
outside the shared core. The narrow initial seam is pure types and state
transitions; native aliases/wrappers can substitute the shared modules without
changing existing caller ordering. The FFXI lead owns that adapter patch.

## Focused verification plan

**Not run in this audit:** upstream builds/tests, native P0, live server/client,
database access, bot login, movement, combat, or Game QA. Reading historical
test reports does not reverify them. The bounded document search did not find a
single declared `/fb P0` suite; do not relabel an arbitrary subset as that gate.

For the core extraction, a small scratch `rustc` harness can load original
`control.rs` with `#[path = "absolute/path"]` without copying it into this repo.
Grammar comparison can load sibling `command`, `authority`, `selection`,
`control` and `orders` modules under a temporary parent module. They use only
the standard library. Compare public results and clock snapshots for the same
inputs/transition sequences against the original shared-core implementation.
Write binaries/logs under the external evidence directory. Do not invoke the
server, FFXI build scripts, or live fixtures for this pure comparison.

After the native owner integrates the exact candidate, relevant existing
focused filters include:

- `fb::control::tests::failed_dismiss_stays_fenced_and_exhaustion_never_wraps`
- `fb::orders::tests::revalidation_cancels_changed_plans_instead_of_retargeting`
- `fb::orders::tests::dismissal_fence_rejects_order_work_stamped_before_it`
- `session::tests::fb_summon_executor_tests::fb_native_summon_executor_confirms_same_zone_arrival_once_and_fences_old_work`
- `session::tests::fb_orders_tests::fb_follow_stay_native_cancels_old_work_and_rejects_driver_override`
- `session::tests::fb_orders_tests::fb_order_refusal_preserves_current_stay_and_stale_request_cannot_rebind`
- `session::tests::fb_orders_tests::fb_role_change_keeps_active_attack_pursuing_same_target`
- `session::tests::fb_rest_tests::fb_rest_rejects_driver_stop_until_owner_changes_order`

The FFXI lead selects its current P0 invocation and matching fixture inputs.
`docs/forever-fb-dit-integrated-acceptance.md` also describes actual Python
driver/native checks requiring explicit pinned driver paths and hashes. Its
saved failures/partial outcomes must not be represented as current passes.

## Provenance and next correction

**OBSERVED:** `fb/mod.rs:1-4` records historical grammar/authority/listing
provenance from DIT r8 `456837be`. The inspected project root had no LICENSE file;
the server workspace and xi-map package manifests specify no license. Treat
these as owner-authorized private project sources with unspecified external
licensing, not as MIT/GPL material by assumption. Shared-core implementations
must be original; record this provenance in `docs/PROVENANCE.md`.

**INFERRED integration plan:** implement and compare the narrow pure contracts,
then send one actionable intake through the coordinator for the FFXI owner to
choose the current pin, apply the adapter change, and run its native P0 plus
Game QA. C1 remains PARTIAL until that integration and QA evidence exists.
