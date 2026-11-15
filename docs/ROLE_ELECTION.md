# Pure role election for the FFXI adapter boundary

`roles::election::elect` computes choices from one adapter-supplied party roster.
This is an additive extraction candidate, not an installed replacement for native
election. The existing 04b/shared6ead C1 intake and current native jobs remain
unchanged. No world state, ownership, clock, order, feature flag or gameplay
action is changed by calling this pure function.

## Inputs and choices

The input is a `BTreeMap` keyed by actor ID. Each `RoleFacts` contains an owner
grouping key, an optional manual `Role`, and optional `AutomaticRole` preferences.
The output is a new ordered map from every supplied actor ID to its chosen role
or `None`. Input facts are never changed.

`automatic: None` means no known job and supplies no automatic role. A known
ordinary job uses `Some(AutomaticRole::default())` and falls back to Dps. Game
job IDs never enter the shared helper; the native adapter maps them to tank/pull
priorities and `HealerPreference::{None, Primary, Fallback}`.

Selection preserves the observed pure native rules:

- Explicit choices always win, even when no job is known. Any manual Tank
  suppresses automatic Tank selection. Multiple manual Tanks are preserved;
  resolving that conflict belongs to the native setter, not this helper.
- Among candidates without a manual choice, the lowest tank priority wins,
  then the lowest actor ID. There is one automatic Tank across the supplied party.
- A Primary healer whose manual choice is absent or Healer suppresses automatic
  Fallback healers. An explicit non-Healer choice for that Primary does not.
- A manual Puller suppresses automatic Puller selection for that owner only.
  Other owners select independently by pull priority, then actor ID.
- Automatic assignment precedence is Tank, qualifying Healer, elected Puller,
  then Dps. Tank/puller selections are computed independently; overlapping
  custom preferences are not backfilled after higher precedence wins.

The roster is authoritative adapter data, not raw command/model input. Actor and
owner keys do not authenticate authority. The helper adds no arbitrary roster
cap; the adapter must supply its actual bounded party and enforce tick budgets.
It allocates result and election maps proportional to that roster, using ordered
lookups rather than scanning the whole population for each member.

## Native responsibilities that remain unchanged

The source reference is FFXI `world/bot_roles.rs` at
`f7c9662fc5bcfc3f37ce00db82e1fc2c00ccee74`, SHA256
`63c7a2001f063d9620e1719928433bd98f887fec296f33ff51b46d8bea370ed5`.
That complete file is byte-identical to the existing 04b adoption source.
Only `tank_priority`, `pull_priority` and `elect` are the comparison boundary.

| Native job fact | Adapter preference for the existing policy |
| --- | --- |
| 7, 13, 1, 8 | Tank priorities 0, 1, 2, 3 respectively |
| 3 | Primary healer |
| 5 | Fallback healer |
| 6, 11 | Pull priorities 0, 1 respectively |
| Other present job | Ordinary automatic preference |
| Absent job | No automatic preference |

This table describes the observed mapping; it is not new runtime configuration.
Native refresh still normalizes an observed zero job and retains prior job facts
when publication is absent. The pure source itself distinguishes an absent job
from any present job value. Human `fill_role_present` inference is a different
native rule and is not extracted or changed here.

The native owner retains full binding filtering, job/manual-choice storage,
zoning and binding-loss lifetimes, authenticated role setters, protection of
another owner's manual Tank, and clearing this owner's previous manual Tank
back to automatic choice. It also retains exclusive group preflight, atomic
role epoch updates, pending election retry, and preservation of explicit orders
and contiguous native continuations. A failed preflight must not partially apply
the computed map. No source adoption or live action follows from a pure result.

The existing `Role` and `PolicyRole` definitions are unchanged. This helper does
not add Support to `/fb role`, convert role changes to owner orders, or replace
the native Fill/Cover/Follow work currently owned by the FFXI lane.

Source snapshot receipt:
`~/.local/share/banshee-bot-core/evidence/role-election-source-20261115-01/result.json`,
SHA256 `37c4d12f23eb71fd2bdfcaee322d2d6c681ee064e154d79c3794dd34fd990a7b`.
Native source and future reference binaries remain outside Git. All committed
implementation and comparison tooling is original. Native P0/Game QA remain
separate from the focused pure-function comparison.
