# Shared strategy frames

`brain::strategy` evaluates a bounded set of adapter strategies against one
supplied world snapshot, freezes their proposals, and passes them to the
[decision selector](DECISION_POLICY.md). It adds no native FFXI call site,
gameplay execution, model request or feature switch. Current C1 adoption and
later rollout gates remain separate.

## Preparation

The adapter supplies a fresh `FrameId`, its current legal-action declarations,
a snapshot reference, and up to 32 `StrategyBinding` entries. Each binding has
a unique `StrategyId`, a priority and a strategy callback. Binding identities
are local diagnostics, not ownership or permission tokens.

`prepare` validates the legal set first through the existing selector, then
checks binding count and duplicate IDs before any callback runs. Valid callbacks
run once in binding order with the same snapshot reference. A strategy evaluates
its triggers and calls `ProposalWriter::emit(action, weight, triggered)`; the
writer assigns the binding's priority. A role strategy cannot promote its own
proposal to safety or owner priority through this interface. The adapter, never
model output, must supply bindings, priorities and action declarations.

The shared limit is 256 proposals across the entire preparation. Unknown action
IDs are refused even when their trigger is false. The first writer error is
sticky: ignoring its returned error or emitting again cannot recover a partial
frame. Strategies can also report `Unavailable`, `InvalidSnapshot` or `Refused`.
A writer error takes precedence over an explicit callback failure.

Any failure returns a `PlanError` and stops subsequent callbacks. It returns no
prepared frame or lower-priority fallback. This prevents an unavailable safety
strategy from silently becoming permission to run an ordinary goal. A native
adapter may have its own separately authorized safe response to planning failure.

## Frozen proposals and advice

Successful preparation owns bounded copies of legal declarations and proposals,
plus a deterministic fallback. `fallback()`, `proposals()` and `legal_actions()`
expose immutable references. No world reference or callback is retained.

`resolve` evaluates optional advice against these frozen declarations using the
existing selector. It never reruns a strategy or refreshes world facts. Safety
and owner precedence, stable ties, economy restrictions, frame matching and
invalid-advice fallback remain the selector's existing rules. Advice cannot add
actions, activate triggers or change priorities/weights.

An empty strategy set or a successful set with no triggered proposals yields
the selector's explicit no-action fallback. It does not invent an idle movement
or attack. A valid ranking is only an intent; it is not an execution receipt.

## Adapter obligations and limits

Use a stable snapshot for the whole preparation. The shared reference does not
prevent interior mutability, external state reads or side effects in callback
code. Callbacks are trusted adapter implementations and must not perform actions
while evaluating proposals. The core discards proposals on error; it cannot undo
side effects a callback improperly performed.

Count/output limits bound storage and core validation work, not callback CPU
time. The owning adapter remains responsible for tick budgets and bounded
strategy implementations. A callback panic is not caught or turned into a
successful frame.

Discard a prepared frame when its snapshot becomes stale, and use a new frame
identity when preparing again. Never reuse identities while old advice can
arrive. Immediately before execution, the native adapter must revalidate current
ownership, cancellation, session/party lifetime, feature flags, human-target
protection and game legality. A prepared frame is neither an authority token nor
a world-state lock. Existing native C1 execution checks remain authoritative.

## Focused evidence

VERIFIED, 2026-11-15 04:30 CST: eight new integration tests pass. They cover
callback order and snapshot identity, binding priorities, frozen input/advice,
sticky unknown/inactive errors, explicit callback failure, validation before
callbacks, exact/oversized strategy and global proposal bounds, and preserved
empty/economy behavior. Command: `nice -n 19 cargo test --offline --locked -j2
-p banshee-bot-core --test strategy_frame`.

Receipt: `~/.local/share/banshee-bot-core/evidence/strategy-frames-integrated-20261115-01/result.json`,
SHA256 `7c857a92b15c5594c1e67925a7aadbc9c06b6a7ae09e733949a268e54655300b`.
All 21 current source/workspace input hashes remain stable through that run.
Relative to the preceding navigation receipt, only `brain/mod.rs` adds an export
and `brain/strategy.rs` is new. Existing decision/navigation modules and tests
retain their saved identities; their earlier checks were not replayed.

The historical C1 comparison retains its original scope: 16 of 18 inputs are
unchanged, while brain/nav module files gained exports. Existing C1 primitive
implementations, flags, manifests and lock retain their bytes. No new native
acceptance, whole-current-crate C1 comparison, game action or Game QA is claimed.
