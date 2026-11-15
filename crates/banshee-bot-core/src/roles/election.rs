//! Pure role choices for one adapter-supplied party roster.
//!
//! Native code maps game jobs to preferences and retains authenticated bindings,
//! cached jobs, explicit choices, role storage and atomic clock updates. This
//! module neither validates authority nor mutates those facts. Actor/owner IDs
//! are grouping and tie-break keys, not permission tokens. Input size and tick
//! budgets remain the adapter's responsibility; do not supply an unbounded world
//! population in place of the actual party roster.

use super::Role;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum HealerPreference {
    #[default]
    None,
    Primary,
    Fallback,
}

/// Lower numeric priority wins, then lower actor ID. A known ordinary job maps
/// to Some(AutomaticRole::default()); an unknown job maps to None in RoleFacts.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct AutomaticRole {
    pub tank_priority: Option<u8>,
    pub healer: HealerPreference,
    pub pull_priority: Option<u8>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RoleFacts {
    pub owner: u32,
    pub manual: Option<Role>,
    pub automatic: Option<AutomaticRole>,
}

/// Return choices without changing the supplied roster or any native state.
///
/// Explicit choices are preserved, including multiple explicit tanks. The
/// native setter must resolve conflicts before election; this function must not
/// silently rewrite another owner's choice. Automatic candidates never include
/// an explicit choice. Tank and puller selections are independent; assigning
/// tank/healer before puller does not backfill an overlapping preference.
pub fn elect(roster: &BTreeMap<u32, RoleFacts>) -> BTreeMap<u32, Option<Role>> {
    let explicit_tank = roster
        .values()
        .any(|facts| facts.manual == Some(Role::Tank));
    let tank = if explicit_tank {
        None
    } else {
        roster
            .iter()
            .filter(|(_, facts)| facts.manual.is_none())
            .filter_map(|(&actor, facts)| {
                facts
                    .automatic?
                    .tank_priority
                    .map(|priority| (priority, actor))
            })
            .min()
            .map(|(_, actor)| actor)
    };

    let primary_healer = roster.values().any(|facts| {
        matches!(facts.manual, None | Some(Role::Healer))
            && facts
                .automatic
                .is_some_and(|job| job.healer == HealerPreference::Primary)
    });
    let explicit_puller_owners: BTreeSet<_> = roster
        .values()
        .filter(|facts| facts.manual == Some(Role::Puller))
        .map(|facts| facts.owner)
        .collect();
    let mut puller_choices = BTreeMap::new();
    for (&actor, facts) in roster {
        if facts.manual.is_some() || explicit_puller_owners.contains(&facts.owner) {
            continue;
        }
        if let Some(priority) = facts.automatic.and_then(|job| job.pull_priority) {
            let choice = (priority, actor);
            puller_choices
                .entry(facts.owner)
                .and_modify(|current| {
                    if choice < *current {
                        *current = choice;
                    }
                })
                .or_insert(choice);
        }
    }

    roster
        .iter()
        .map(|(&actor, facts)| {
            let selected = match (facts.manual, facts.automatic) {
                (Some(role), _) => Some(role),
                (None, None) => None,
                (None, Some(job)) => Some(if tank == Some(actor) {
                    Role::Tank
                } else if job.healer == HealerPreference::Primary
                    || (job.healer == HealerPreference::Fallback && !primary_healer)
                {
                    Role::Healer
                } else if puller_choices
                    .get(&facts.owner)
                    .is_some_and(|(_, choice)| *choice == actor)
                {
                    Role::Puller
                } else {
                    Role::Dps
                }),
            };
            (actor, selected)
        })
        .collect()
}
