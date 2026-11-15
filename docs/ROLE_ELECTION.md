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

## Focused comparison result

VERIFIED, 2026-11-15 CST: **8,498 comparisons** against the pinned pure functions
pass, with **19 separate generic helper checks**. The deterministic cases cover
every present `u8` job and absent jobs, all manual-role choices, representative
job pairs under shared/separate owners, mixed groups and tie ordering. Generic
checks cover arbitrary priorities/IDs, manual overrides, missing-job behavior,
overlapping preferences without backfill and an input larger than six members.
These finite cases are not a general or whole-program equivalence proof.

The checker verifies the complete native source hash before extracting only the
three pure functions into a new external directory. A documented minimal
Assignment/OwnerBinding/four-role enum shim and original projection wrapper make
that function boundary compilable. It compiles the shared library and driver
directly with `rustc`; no native World, server, Session/P0 or earlier comparison
suite is built or run. Source, core, compiler and tool hashes stayed stable.

```sh
python3 scripts/check_ffxi_role_election.py \
  --core /home/blizz/dev/banshee-bot-core \
  --source /absolute/private/path/to/pinned-bot_roles.rs \
  --evidence /absolute/private/path/to/new-evidence-directory
```

Two additional CLI refusal checks pass: unsupported source fails before
compilation/evidence creation, and an existing evidence directory is refused
without changing its retained files. There is no overwrite option.

| Receipt under `~/.local/share/banshee-bot-core/` | SHA256 |
| --- | --- |
| `evidence/role-election-compat-20261115-01/result.json` | `872e5f917fd60f7867cfd650c4ce083b9426531b5d1a89676cf48d1ed709498a` |
| `evidence/role-election-refusals-20261115-01/result.json` | `7e2abef2cb4bd53f8729a637938456af3bc218953a362b63ee700d0c7cd9cef5` |
| `evidence/role-election-compat-20261115-01/scope-join.json` | `9b9b6fc43a69b09cdd1685ec7dfbd75a66b9cc49c25a73474409ebb3630a18b8` |

The receipt pins 22 current core inputs. Relative to the earlier strategy
receipt, only `roles/mod.rs` gains an export and `roles/election.rs` is added;
existing Role/PolicyRole definitions are byte-identical after removing that
export. Strategy, decision and navigation source/test bytes retain their saved
identities, without replaying their tests. Of the historical C1 comparison's
18 inputs, 15 are unchanged; brain/nav/roles files only gained module exports.
This does not promote the earlier comparison to whole-current-crate proof or
authorize a native adoption, install or restart.
