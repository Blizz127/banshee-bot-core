# Shared decision policy

`brain::decision` is a pure, bounded action selector for future in-process
adapters. A strategy contributes a proposal only through an action ID from the
adapter's legal set. The selector chooses a deterministic fallback and can
apply optional advice within a restricted set of equally ranked choices.
It performs no gameplay mutation, network access, session creation or LLM call.

The optional [strategy-frame interface](STRATEGY_FRAMES.md) evaluates bounded
adapter callbacks and freezes their proposals before this selection step.

This is shared architecture groundwork. No FFXI call site uses it, no feature
switch changes, and no C2+ rollout or native C1/P0 acceptance follows. The owning
FFXI source adoption stays on its existing coherent 6ead candidate.

## Inputs and deterministic selection

The adapter supplies one `FrameId`, up to 64 unique `LegalAction` entries and up
to 256 `Proposal` entries. Each proposal has an action ID, priority, integer
weight and evaluated trigger. Both lists are validated before selection;
unknown proposal IDs are errors even when their trigger is false. Duplicate
legal IDs and any `Privileged` legal action are refused.

| Priority, highest first | Selection | Advice |
| --- | --- | --- |
| Safety | Highest weight, then first triggered proposal | Never applied |
| OwnerOrder | Highest weight, then first triggered proposal | Never applied |
| Role | Highest weight, then first triggered proposal | Equal-priority/equal-weight ordinary ties only |
| Goal | Highest weight, then first triggered proposal | Equal-priority/equal-weight ordinary ties only |

Inactive proposals cannot win. Priority always outranks weight; weights are
compared directly without arithmetic that could overflow. Repeated proposals
for the same legal action are permitted, but that action appears only once in
the advice choices. Empty frames or frames with no active proposal return an
explicit `None` action; the selector invents no default movement or attack.

`Decision` records the originating frame, selected action, priority, weight,
advice outcome and eligible advice choices. `ActionId` and `FrameId` are plain
adapter declarations, not authorization tokens. The selector does not establish
that the adapter's world facts or action classifications are correct.

## Optional advice and fallback

Call `select(..., None)` to obtain the fallback and `advice_choices`. When at
least two eligible ordinary actions tie at the winning priority and weight, an
adapter may request a ranking of exactly those IDs. Advice cannot cross a
priority or weight boundary, enable an inactive trigger, introduce an action,
or replace a safety/owner decision. If any tied winning action is `Economy`,
the frame exposes no advice choices. Movement, combat and social classifications
do not themselves grant permission to execute an action.

Advice must carry the matching frame ID and an exact permutation of all exposed
choices. Stale frames, wrong lengths, duplicate IDs or ineligible IDs reject the
entire ranking and retain the deterministic fallback. `AdviceStatus` records the
reason. No choices means advice is `NotApplicable`; omitting advice yields
`NotRequested`. A timeout, unavailable model or parse failure should use the
same no-advice path. The core neither parses model prose nor invents missing IDs.

## Adapter obligations

Build the legal set from current, authoritative native facts. Evaluate strategy
triggers against that same snapshot. Assign a fresh frame identity whenever the
snapshot or eligible proposals change; frame identities must not be reused
while advice for an old frame can arrive. This is separate from the FFXI control
clock's cancellation epoch, which does not identify every planning frame.

If the world changes while advice is pending, select from a fresh frame and
reject the old response. Before executing any selected ID, revalidate ownership,
session/party lifetime, feature flags, readiness, human-target protections and
current game legality through the native adapter. Existing C1 authority tickets,
control fences and native execution checks remain authoritative. A returned
decision is an intent, not a claim that an action ran or succeeded.

For a movement candidate, the adapter can use
[Rust route measurements](NAV_CORE_METRICS.md) alongside its native collision
and movement checks before adding the action to the legal set. A projection
outcome alone does not establish route legality. The selector receives the
resulting action ID, not a new path invented by advice.

The API provides ordering and validation, not strategies for a particular job,
native triggers, chat phrasing, movement, auction policy or population control.
Those remain in their ordered rollout phases and require owning-game evidence.

## Focused evidence

VERIFIED, 2026-11-15 CST: 11 focused Rust integration tests pass. They cover
hard priority ordering across integer weight extremes, trigger filtering,
stable ties, valid and invalid advice, frame identity, economy/privileged
restrictions, duplicate and unknown IDs, empty frames, and exact/oversized limits.
Command: `nice -n 19 cargo test --offline --locked -j2 -p banshee-bot-core
--test decision_policy`.

Receipt: `~/.local/share/banshee-bot-core/evidence/decision-policy-20261115-01/result.json`,
SHA256 `a49f7f8b3ff8a22bb2a4fd44ee981cc7bdae2991129c66889508abb7d6ec2fa1`.
The source and lock hashes are unchanged through that run.

The earlier C1 comparison remains historical evidence for its exact source.
At this policy check, 17 of its 18 recorded inputs were byte-identical; `brain/mod.rs` adds
only `pub mod decision;`, and `brain/decision.rs` is new. No existing C1
primitive, feature flag, Cargo manifest or lock changed. The comparison was not
replayed and is not presented as whole-current-crate equivalence. This API has
no native runtime call site and no game/LLM service was exercised.

The subsequent [navigation measurement API](NAV_CORE_METRICS.md) adds a second
module/export. Its separate receipt records 16 unchanged historical inputs and
unchanged decision-module/test bytes; it does not replay or expand this result.
