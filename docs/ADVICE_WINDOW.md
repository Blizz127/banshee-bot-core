# Shared brain advice window

`brain::advice_window::AdviceWindow` owns one completed
[strategy frame](STRATEGY_FRAMES.md) while optional advice is pending. It returns
one selected intent, or discards the frame. This supplies the deadline/failure
behavior around the existing pure selector without a model call, timer, thread,
network request or game action. No native FFXI call site is changed.

## Nonblocking lifecycle

Create a window with `AdviceWindow::new(prepared, now_ms, max_wait_ms)` using
monotonic milliseconds supplied by the adapter and an explicit wait budget.
The deadline uses checked addition; overflow returns `DeadlineOverflow` and
no decision. A zero budget requests immediate deterministic fallback. There is
no core default budget or background wait. The adapter should derive its budget
from its own decision cadence and poll on its existing loop.

Call `poll(now_ms, reply)` with no reply, a ranking, or an explicit model failure:

| Condition, checked in this order | Outcome |
| --- | --- |
| Frame already consumed/cancelled | `Closed` |
| Time precedes the previous observation | `ClockRegressed`; frame discarded |
| No eligible advice choices | Immediate fallback, `NoAdviceChoices` |
| Time is at or beyond the deadline | Fallback, `Deadline`; any supplied reply is ignored |
| Reply belongs to another frame | `Pending(StaleReply)`; current frame retained |
| Matching ranking | `Ready`, `Ranking`; existing selector validates the entire ranking |
| Matching `Unavailable` | Fallback, `Unavailable` |
| No reply | `Pending(AwaitingReply)` |

Equal timestamps are allowed. The deadline is inclusive: a ranking observed
exactly at it cannot extend the wait. It is an observation deadline, not a model
server's asserted send time. A matching invalid ranking consumes the window
with the existing deterministic fallback; `Decision.advice` records the exact
rejection. A stale reply cannot prematurely select the current fallback.

Safety and owner decisions never wait, since the selector exposes no choices
for their priorities. The same applies to an economy tie, a single winner or an
empty frame. A fallback can explicitly contain no action. Eligible Role/Goal
ties retain their frozen legal set, priority and weight; advice cannot invent
an action or gain economy/privileged authority.

`request()` exposes only the frozen frame ID, eligible choices and deadline.
It returns `None` for closed windows, zero budgets and frames without choices.
It does not read a clock; poll with current time before dispatching advice.
Repeated getter calls are not permission to issue repeated model requests.
The native adapter owns request rate limiting and routing to the correct bot.

Every `Ready` result consumes the prepared frame. Later polls return `Closed`
and cannot issue a second decision. `cancel()` discards it without selecting a
fallback and reports whether a frame was present. The window is not cloneable,
resettable or resumable. Any decision-resolution error also leaves it closed.

## Adapter obligations

This is additive shared architecture, not a change to the existing FFXI
cancellation clock or its coherent 04b/shared6ead C1 adoption. C1/P0 and Game QA
remain separate, and C1 has no navigation or advice prerequisite. No feature
switch is enabled and no C2+ rollout advances.

Create a new prepared frame when relevant facts change. Cancel a pending window
when a safety condition, owner order, ownership, session lifetime or feature flag
invalidates its snapshot, then prepare the new decision. A pending role choice
does not observe a new safety trigger by itself. The adapter must not leave old
work waiting while a newly required safety/owner response should take precedence.

Frame identities must stay unique within the lifetime and routing scope of
outstanding replies. This helper does not allocate global IDs or authenticate
the reply source. Route replies by the correct bot/session as well as frame ID;
a plain equal integer does not establish identity. Cancellation closes local
planning work, not an external model request or native operation.

Before executing any selected ID, revalidate native authority, cancellation
epochs, session/party state, flags, human-target protections and game legality.
Time progression does not refresh the frozen snapshot. A timeout fallback is
an intent requiring those same checks, not evidence that old facts remain true.

The core neither parses model text nor creates a failure event. The adapter
maps a transport refusal, parse error or unavailable model to
`Reply::Unavailable { frame }`, or simply lets the deadline elapse. Advice never
receives GM/economy authority. Native execution and all mutations stay with the
game owner. **NEVER restart FFXI**, including at zero players.

## Focused evidence

VERIFIED offline: eight integration tests pass against the real shared strategy
preparer and selector. They cover immediate safety/owner/economy/single/empty
fallback, valid rankings and one-result consumption, invalid ranking fallback,
stale ranking/failure replies, inclusive deadlines and zero budget, explicit
unavailability, cancellation, equal/regressing time and checked-add overflow.

Command: `nice -n 19 cargo test --offline --locked -j1 -p banshee-bot-core
--test advice_window`, using a fresh external target directory. One compiler
job was selected under observed host load. The build has no warnings and its
source/toolchain pins stayed stable. Receipt:
`~/.local/share/banshee-bot-core/evidence/advice-window-20261115-01/result.json`,
SHA256 `29294bcafdf862571f4dedf7f6024b82288349b8a315ee9f06459dc820689bb6`.

Of the 22 inputs in the prior role-election receipt, 21 retain their exact
bytes; `brain/mod.rs` adds only the new module export. Existing C1 primitives,
feature flags, selector and strategy implementation remain unchanged. Earlier
tests/comparisons were not replayed or promoted to whole-current-crate proof.
No real model service, native adapter, runtime tick timing, Game QA or live
action was exercised. The new interface is unadopted source groundwork.
