//! Original bounded differential cases for the pure role-election function.
//! The checker supplies a pinned native fragment outside this repository.
//! No native World, binding mutation, setter, control clock or epoch is run.

mod reference {
    include!(env!("FFXI_ROLE_ELECTION_REFERENCE"));
}

use banshee_bot_core::roles::{
    election::{elect, AutomaticRole, HealerPreference, RoleFacts},
    Role,
};
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug)]
struct Row {
    actor: u32,
    owner: u32,
    job: Option<u8>,
    manual: Option<Role>,
}

#[derive(Default)]
struct Counts {
    differential_cases: usize,
    kernel_cases: usize,
    input_stability_checks: usize,
    result_rows: usize,
    families: BTreeMap<&'static str, usize>,
    outcomes: BTreeMap<&'static str, usize>,
}

fn native_role(role: Role) -> reference::Role {
    match role {
        Role::Tank => reference::Role::Tank,
        Role::Healer => reference::Role::Healer,
        Role::Dps => reference::Role::Dps,
        Role::Puller => reference::Role::Puller,
    }
}

fn core_role(role: reference::Role) -> Role {
    match role {
        reference::Role::Tank => Role::Tank,
        reference::Role::Healer => Role::Healer,
        reference::Role::Dps => Role::Dps,
        reference::Role::Puller => Role::Puller,
    }
}

// Adapter facts for this explicit FFXI source profile. Some(0) is intentionally
// distinct from None here: native job normalization occurs before this kernel.
fn automatic(job: u8) -> AutomaticRole {
    AutomaticRole {
        tank_priority: match job {
            7 => Some(0),
            13 => Some(1),
            1 => Some(2),
            8 => Some(3),
            _ => None,
        },
        healer: match job {
            3 => HealerPreference::Primary,
            5 => HealerPreference::Fallback,
            _ => HealerPreference::None,
        },
        pull_priority: match job {
            6 => Some(0),
            11 => Some(1),
            _ => None,
        },
    }
}

type FactsFingerprint = Vec<(u32, u32, Option<Role>, Option<(Option<u8>, u8, Option<u8>)>)>;

fn fingerprint(facts: &BTreeMap<u32, RoleFacts>) -> FactsFingerprint {
    facts
        .iter()
        .map(|(&actor, fact)| {
            let automatic = fact.automatic.as_ref().map(|automatic| {
                let healer = match automatic.healer {
                    HealerPreference::None => 0,
                    HealerPreference::Primary => 1,
                    HealerPreference::Fallback => 2,
                };
                (automatic.tank_priority, healer, automatic.pull_priority)
            });
            (actor, fact.owner, fact.manual, automatic)
        })
        .collect()
}

fn reference_fingerprint(rows: &[reference::Input]) -> Vec<(u32, u32, Option<u8>, Option<Role>)> {
    rows.iter()
        .map(|row| (row.actor, row.owner, row.job, row.manual.map(core_role)))
        .collect()
}

fn record_outcomes(counts: &mut Counts, roles: &BTreeMap<u32, Option<Role>>) {
    counts.result_rows += roles.len();
    for role in roles.values() {
        let label = match role {
            None => "None",
            Some(Role::Tank) => "Tank",
            Some(Role::Healer) => "Healer",
            Some(Role::Dps) => "Dps",
            Some(Role::Puller) => "Puller",
        };
        *counts.outcomes.entry(label).or_default() += 1;
    }
}

fn compare(counts: &mut Counts, family: &'static str, rows: &[Row]) {
    let native: Vec<_> = rows
        .iter()
        .map(|row| reference::Input {
            actor: row.actor,
            owner: row.owner,
            job: row.job,
            manual: row.manual.map(native_role),
        })
        .collect();
    let current: BTreeMap<_, _> = rows
        .iter()
        .map(|row| {
            (
                row.actor,
                RoleFacts {
                    owner: row.owner,
                    manual: row.manual,
                    automatic: row.job.map(automatic),
                },
            )
        })
        .collect();
    assert_eq!(current.len(), rows.len(), "driver actor IDs must be unique");
    let native_before = reference_fingerprint(&native);
    let current_before = fingerprint(&current);
    let expected: BTreeMap<_, _> = reference::run(&native)
        .into_iter()
        .map(|(actor, role)| (actor, role.map(core_role)))
        .collect();
    let actual = elect(&current);
    assert_eq!(actual, expected, "{family}: {rows:?}");
    assert_eq!(actual.keys().collect::<Vec<_>>(), current.keys().collect::<Vec<_>>());
    assert_eq!(fingerprint(&current), current_before, "core input changed: {family}");
    assert_eq!(reference_fingerprint(&native), native_before, "reference wrapper input changed");
    counts.input_stability_checks += 2;
    counts.differential_cases += 1;
    *counts.families.entry(family).or_default() += 1;
    record_outcomes(counts, &actual);
}

fn differential(counts: &mut Counts) {
    let manuals = [None, Some(Role::Tank), Some(Role::Healer), Some(Role::Dps), Some(Role::Puller)];
    for job in std::iter::once(None).chain((u8::MIN..=u8::MAX).map(Some)) {
        for manual in manuals {
            compare(counts, "single-job-manual", &[Row { actor: 31, owner: 9, job, manual }]);
        }
    }
    let relevant = [None, Some(0), Some(1), Some(3), Some(5), Some(6), Some(7), Some(8),
                    Some(11), Some(13), Some(20), Some(255)];
    for left in relevant {
        for right in relevant {
            for left_manual in manuals {
                for right_manual in manuals {
                    for right_owner in [9, 10] {
                        compare(counts, "pair-jobs-manuals-owner-partitions", &[
                            Row { actor: 41, owner: 9, job: left, manual: left_manual },
                            Row { actor: 7, owner: right_owner, job: right, manual: right_manual },
                        ]);
                    }
                }
            }
        }
    }
    compare(counts, "directed-empty", &[]);
    let mixed = [
        Row { actor: 31, owner: 9, job: Some(7), manual: None },
        Row { actor: 8, owner: 9, job: Some(7), manual: None },
        Row { actor: 13, owner: 9, job: Some(3), manual: None },
        Row { actor: 22, owner: 10, job: Some(5), manual: None },
        Row { actor: 4, owner: 9, job: Some(6), manual: None },
        Row { actor: 3, owner: 9, job: Some(11), manual: None },
        Row { actor: 44, owner: 10, job: Some(11), manual: None },
        Row { actor: 70, owner: 10, job: None, manual: None },
        Row { actor: 0, owner: 0, job: Some(255), manual: None },
        Row { actor: u32::MAX, owner: u32::MAX, job: Some(0), manual: None },
    ];
    compare(counts, "directed-mixed-group", &mixed);
    let mut reversed = mixed;
    reversed.reverse();
    compare(counts, "directed-reordered-input", &reversed);
    for manual in manuals {
        let mut changed = mixed;
        changed[2].manual = manual;
        compare(counts, "directed-primary-manual-choice", &changed);
    }
    for (index, manual) in [(7, Role::Tank), (7, Role::Puller), (4, Role::Dps)] {
        let mut changed = mixed;
        changed[index].manual = Some(manual);
        compare(counts, "directed-manual-overrides", &changed);
    }
    let mut manual_tanks = mixed;
    manual_tanks[7].manual = Some(Role::Tank);
    manual_tanks[9].manual = Some(Role::Tank);
    compare(counts, "directed-multiple-manual-tanks", &manual_tanks);
    let mut removed_primary = mixed;
    removed_primary[2].job = None;
    compare(counts, "directed-primary-job-absent", &removed_primary);
    assert_eq!(counts.families["single-job-manual"], 257 * 5);
    assert_eq!(counts.families["pair-jobs-manuals-owner-partitions"], 12 * 12 * 25 * 2);
}

fn preferences(tank: Option<u8>, healer: HealerPreference, pull: Option<u8>) -> Option<AutomaticRole> {
    Some(AutomaticRole { tank_priority: tank, healer, pull_priority: pull })
}

fn facts(owner: u32, manual: Option<Role>, automatic: Option<AutomaticRole>) -> RoleFacts {
    RoleFacts { owner, manual, automatic }
}

fn kernel(counts: &mut Counts, label: &'static str, rows: Vec<(u32, RoleFacts)>, expected: &[(u32, Option<Role>)]) {
    let current: BTreeMap<_, _> = rows.into_iter().collect();
    let before = fingerprint(&current);
    let actual = elect(&current);
    let expected: BTreeMap<_, _> = expected.iter().copied().collect();
    assert_eq!(actual, expected, "generic kernel: {label}");
    assert_eq!(actual.keys().collect::<Vec<_>>(), current.keys().collect::<Vec<_>>());
    assert_eq!(fingerprint(&current), before, "generic kernel input changed: {label}");
    counts.input_stability_checks += 1;
    counts.kernel_cases += 1;
    *counts.families.entry(label).or_default() += 1;
    record_outcomes(counts, &actual);
}

fn generic_kernel(counts: &mut Counts) {
    use HealerPreference::{Fallback, None as NoHealer, Primary};
    use Role::{Dps, Healer, Puller, Tank};
    kernel(counts, "kernel-empty", vec![], &[]);
    kernel(counts, "kernel-default-and-missing", vec![
        (1, facts(9, None, None)),
        (2, facts(9, None, Some(AutomaticRole::default()))),
        (3, facts(9, Some(Healer), None)),
    ], &[(1, None), (2, Some(Dps)), (3, Some(Healer))]);
    kernel(counts, "kernel-rank-then-actor", vec![
        (1, facts(9, None, preferences(Some(200), NoHealer, None))),
        (50, facts(9, None, preferences(Some(7), NoHealer, None))),
        (9, facts(10, None, preferences(Some(7), NoHealer, None))),
    ], &[(1, Some(Dps)), (9, Some(Tank)), (50, Some(Dps))]);
    kernel(counts, "kernel-max-rank-and-ids", vec![
        (u32::MAX, facts(u32::MAX, None, preferences(Some(255), NoHealer, None))),
        (0, facts(0, None, preferences(Some(255), NoHealer, None))),
    ], &[(0, Some(Tank)), (u32::MAX, Some(Dps))]);
    kernel(counts, "kernel-multiple-manual-tanks", vec![
        (1, facts(9, Some(Tank), None)),
        (2, facts(10, Some(Tank), None)),
        (3, facts(9, None, preferences(Some(0), NoHealer, None))),
    ], &[(1, Some(Tank)), (2, Some(Tank)), (3, Some(Dps))]);
    kernel(counts, "kernel-manual-dps-overrides-all", vec![
        (1, facts(9, Some(Dps), preferences(Some(0), Primary, Some(0)))),
        (2, facts(9, None, preferences(Some(5), Fallback, Some(5)))),
        (3, facts(10, None, preferences(None, Fallback, None))),
    ], &[(1, Some(Dps)), (2, Some(Tank)), (3, Some(Healer))]);
    for (manual, expected_primary, expected_fallback, label) in [
        (None, Some(Healer), Some(Dps), "kernel-primary-automatic"),
        (Some(Healer), Some(Healer), Some(Dps), "kernel-primary-manual-healer"),
        (Some(Dps), Some(Dps), Some(Healer), "kernel-primary-manual-dps"),
        (Some(Tank), Some(Tank), Some(Healer), "kernel-primary-manual-tank"),
        (Some(Puller), Some(Puller), Some(Healer), "kernel-primary-manual-puller"),
    ] {
        kernel(counts, label, vec![
            (1, facts(9, manual, preferences(None, Primary, None))),
            (2, facts(10, None, preferences(None, Fallback, None))),
        ], &[(1, expected_primary), (2, expected_fallback)]);
    }
    kernel(counts, "kernel-manual-puller-owner-scope", vec![
        (1, facts(9, Some(Puller), None)),
        (2, facts(9, None, preferences(None, NoHealer, Some(0)))),
        (8, facts(10, None, preferences(None, NoHealer, Some(255)))),
        (4, facts(10, None, preferences(None, NoHealer, Some(255)))),
    ], &[(1, Some(Puller)), (2, Some(Dps)), (4, Some(Puller)), (8, Some(Dps))]);
    kernel(counts, "kernel-puller-rank-then-actor", vec![
        (1, facts(0, None, preferences(None, NoHealer, Some(7)))),
        (8, facts(0, None, preferences(None, NoHealer, Some(2)))),
        (4, facts(0, None, preferences(None, NoHealer, Some(2)))),
    ], &[(1, Some(Dps)), (4, Some(Puller)), (8, Some(Dps))]);
    kernel(counts, "kernel-tank-precedes-healer-and-puller", vec![
        (1, facts(9, None, preferences(Some(0), Primary, Some(0)))),
        (2, facts(9, None, preferences(None, Fallback, Some(1)))),
    ], &[(1, Some(Tank)), (2, Some(Dps))]);
    kernel(counts, "kernel-healer-precedes-puller", vec![
        (1, facts(9, None, preferences(None, Primary, Some(0)))),
        (2, facts(9, None, preferences(None, NoHealer, Some(1)))),
    ], &[(1, Some(Healer)), (2, Some(Dps))]);
    kernel(counts, "kernel-fallback-precedes-puller", vec![
        (1, facts(9, None, preferences(None, Fallback, Some(0)))),
        (2, facts(9, None, preferences(None, NoHealer, Some(1)))),
    ], &[(1, Some(Healer)), (2, Some(Dps))]);
    kernel(counts, "kernel-suppressed-fallback-can-pull", vec![
        (1, facts(9, None, preferences(None, Fallback, Some(0)))),
        (2, facts(10, None, preferences(None, Primary, None))),
    ], &[(1, Some(Puller)), (2, Some(Healer))]);
    kernel(counts, "kernel-manual-tank-reveals-healer", vec![
        (1, facts(9, None, preferences(Some(0), Primary, Some(0)))),
        (2, facts(10, Some(Tank), None)),
    ], &[(1, Some(Healer)), (2, Some(Tank))]);
    let large: Vec<_> = (0..9).map(|actor| (actor, facts(actor, None, Some(AutomaticRole::default())))).collect();
    let expected: Vec<_> = (0..9).map(|actor| (actor, Some(Dps))).collect();
    kernel(counts, "kernel-more-than-six-facts", large, &expected);
}

fn main() {
    let mut counts = Counts::default();
    differential(&mut counts);
    generic_kernel(&mut counts);
    assert!(counts.differential_cases + counts.kernel_cases < 10_000, "bounded comparison budget");
    for role in ["None", "Tank", "Healer", "Dps", "Puller"] {
        assert!(counts.outcomes.get(role).copied().unwrap_or(0) > 0, "missing role outcome: {role}");
    }
    println!(
        "{{\"status\":\"PASS\",\"scope\":\"pure role election only; no World/setter/binding/state/epoch/P0 claim\",\"differential_cases\":{},\"generic_kernel_cases\":{},\"total_cases\":{},\"input_stability_checks\":{},\"result_rows\":{},\"families\":{:?},\"outcomes\":{:?}}}",
        counts.differential_cases, counts.kernel_cases, counts.differential_cases + counts.kernel_cases,
        counts.input_stability_checks, counts.result_rows, counts.families, counts.outcomes
    );
}
