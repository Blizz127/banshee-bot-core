//! Original offline differential cases for the pinned FFXI pure contracts.
//! This binary never connects to a game or executes a planned mutation.

#[path = "reference/mod.rs"]
mod reference;

use banshee_bot_core::brain::{authority as ca, command as cc, orders as co, selection as cs};
use reference::{authority as na, command as nc, orders as no, selection as ns};
use std::collections::BTreeMap;
use std::fmt::Debug;

#[derive(Default)]
struct Counts {
    comparisons: usize,
    coverage: BTreeMap<String, usize>,
    prepared: usize,
    refused: usize,
}

impl Counts {
    fn compare(&mut self, method: &str, old: impl Debug, new: impl Debug, context: impl Debug) {
        assert_eq!(
            format!("{old:?}"),
            format!("{new:?}"),
            "{method}: {context:?}"
        );
        self.comparisons += 1;
    }

    fn result<T: Debug, U: Debug, E: Debug, F: Debug>(
        &mut self,
        method: &str,
        old: &Result<T, E>,
        new: &Result<U, F>,
        context: impl Debug,
    ) {
        self.compare(method, old, new, context);
        let outcome = match old {
            Ok(_) => "Ok".to_owned(),
            Err(error) => format!("Err({error:?})"),
        };
        *self
            .coverage
            .entry(format!("{method}:{outcome}"))
            .or_default() += 1;
    }
}

fn kind(value: na::ActorKind) -> ca::ActorKind {
    match value {
        na::ActorKind::Human => ca::ActorKind::Human,
        na::ActorKind::PopulationBot => ca::ActorKind::PopulationBot,
        na::ActorKind::PersonaBot => ca::ActorKind::PersonaBot,
        na::ActorKind::SocketlessActor => ca::ActorKind::SocketlessActor,
        na::ActorKind::Unknown => ca::ActorKind::Unknown,
    }
}

fn requester(value: na::RequesterSnapshot) -> ca::RequesterSnapshot {
    ca::RequesterSnapshot {
        actor_id: value.actor_id,
        kind: kind(value.kind),
        current_session: value.current_session,
        generation: value.generation,
        party_uid: value.party_uid,
    }
}

fn binding(value: na::OwnerBinding) -> ca::OwnerBinding {
    ca::OwnerBinding {
        owner: value.owner,
        party_uid: value.party_uid,
        revision: value.revision,
    }
}

fn target(value: na::TargetSnapshot) -> ca::TargetSnapshot {
    ca::TargetSnapshot {
        actor_id: value.actor_id,
        kind: kind(value.kind),
        registered_population: value.registered_population,
        current_session: value.current_session,
        generation: value.generation,
        party_uid: value.party_uid,
        binding: value.binding.map(binding),
    }
}

fn invitation(value: na::InvitationOutcome) -> ca::InvitationOutcome {
    match value {
        na::InvitationOutcome::Pending => ca::InvitationOutcome::Pending,
        na::InvitationOutcome::Declined => ca::InvitationOutcome::Declined,
        na::InvitationOutcome::Refused => ca::InvitationOutcome::Refused,
        na::InvitationOutcome::Accepted {
            inviter,
            invitee,
            party_uid,
        } => ca::InvitationOutcome::Accepted {
            inviter,
            invitee,
            party_uid,
        },
    }
}

fn mutation(value: na::Mutation) -> ca::Mutation {
    match value {
        na::Mutation::Summon => ca::Mutation::Summon,
        na::Mutation::Dismiss => ca::Mutation::Dismiss,
        na::Mutation::Order => ca::Mutation::Order,
        na::Mutation::Gear => ca::Mutation::Gear,
    }
}

fn role(value: no::Role) -> co::Role {
    match value {
        no::Role::Tank => co::Role::Tank,
        no::Role::Healer => co::Role::Healer,
        no::Role::Dps => co::Role::Dps,
        no::Role::Puller => co::Role::Puller,
    }
}

fn order(value: &no::Order) -> co::Order {
    match value {
        no::Order::Follow => co::Order::Follow,
        no::Order::Stay => co::Order::Stay,
        no::Order::Rest => co::Order::Rest,
        no::Order::Attack => co::Order::Attack,
        no::Order::Pull => co::Order::Pull,
        no::Order::Assist => co::Order::Assist,
        no::Order::Role { name, role: value } => co::Order::Role {
            name: name.clone(),
            role: role(*value),
        },
    }
}

fn selector(value: &nc::Target) -> cc::Target {
    match value {
        nc::Target::All => cc::Target::All,
        nc::Target::Name(name) => cc::Target::Name(name.clone()),
    }
}

fn session(value: no::OrderSession) -> co::OrderSession {
    co::OrderSession {
        generation: value.generation,
        in_zone: value.in_zone,
        transition_pending: value.transition_pending,
        event_active: value.event_active,
        shutting_down: value.shutting_down,
        superseded: value.superseded,
        alive: value.alive,
        zone: value.zone,
    }
}

fn engage(value: no::EngageTarget) -> co::EngageTarget {
    co::EngageTarget {
        actor_id: value.actor_id,
        zone: value.zone,
        hostile_mob: value.hostile_mob,
        alive: value.alive,
        claim: match value.claim {
            no::Claim::Unclaimed => co::Claim::Unclaimed,
            no::Claim::OwnerParty => co::Claim::OwnerParty,
            no::Claim::Other => co::Claim::Other,
        },
    }
}

fn scene(value: no::Scene) -> co::Scene {
    co::Scene {
        owner_target: value.owner_target.map(engage),
        main_tank: match value.main_tank {
            no::MainTank::None => co::MainTank::None,
            no::MainTank::Ambiguous => co::MainTank::Ambiguous,
            no::MainTank::Member {
                actor_id,
                party_uid,
                engaged,
            } => co::MainTank::Member {
                actor_id,
                party_uid,
                engaged: engaged.map(engage),
            },
        },
    }
}

fn candidate(value: no::OrderCandidate<'_>) -> co::OrderCandidate<'_> {
    co::OrderCandidate {
        identity: cs::Candidate {
            name: value.identity.name,
            target: target(value.identity.target),
        },
        session: value.session.map(session),
        control: match value.control {
            no::Control::Open => co::Control::Open,
            no::Control::Closed => co::Control::Closed,
        },
    }
}

fn owner() -> na::RequesterSnapshot {
    na::RequesterSnapshot {
        actor_id: 42,
        kind: na::ActorKind::Human,
        current_session: true,
        generation: 11,
        party_uid: Some(99),
    }
}

fn bot() -> na::TargetSnapshot {
    na::TargetSnapshot {
        actor_id: 301,
        kind: na::ActorKind::PopulationBot,
        registered_population: true,
        current_session: true,
        generation: 17,
        party_uid: Some(99),
        binding: Some(na::OwnerBinding {
            owner: 42,
            party_uid: 99,
            revision: 23,
        }),
    }
}

fn requesters() -> Vec<na::RequesterSnapshot> {
    let base = owner();
    let mut cases = vec![base];
    for actor_id in [0, 43] {
        cases.push(na::RequesterSnapshot { actor_id, ..base });
    }
    for kind in [
        na::ActorKind::PopulationBot,
        na::ActorKind::PersonaBot,
        na::ActorKind::SocketlessActor,
        na::ActorKind::Unknown,
    ] {
        cases.push(na::RequesterSnapshot { kind, ..base });
    }
    cases.push(na::RequesterSnapshot {
        current_session: false,
        ..base
    });
    for generation in [0, 12, u64::MAX] {
        cases.push(na::RequesterSnapshot { generation, ..base });
    }
    for party_uid in [None, Some(0), Some(100)] {
        cases.push(na::RequesterSnapshot { party_uid, ..base });
    }
    // Multiple simultaneous refusals pin error precedence rather than only isolated failures.
    cases.push(na::RequesterSnapshot {
        actor_id: 0,
        generation: 0,
        party_uid: None,
        ..base
    });
    cases
}

fn targets() -> Vec<na::TargetSnapshot> {
    let base = bot();
    let bound = base.binding.unwrap();
    let mut cases = vec![base];
    for actor_id in [0, 42, 302] {
        cases.push(na::TargetSnapshot { actor_id, ..base });
    }
    for kind in [
        na::ActorKind::Human,
        na::ActorKind::PersonaBot,
        na::ActorKind::SocketlessActor,
        na::ActorKind::Unknown,
    ] {
        cases.push(na::TargetSnapshot { kind, ..base });
    }
    cases.push(na::TargetSnapshot {
        registered_population: false,
        ..base
    });
    cases.push(na::TargetSnapshot {
        current_session: false,
        ..base
    });
    for generation in [0, 18, u64::MAX] {
        cases.push(na::TargetSnapshot { generation, ..base });
    }
    for party_uid in [None, Some(0), Some(100)] {
        cases.push(na::TargetSnapshot { party_uid, ..base });
    }
    cases.push(na::TargetSnapshot {
        binding: None,
        ..base
    });
    for binding in [
        na::OwnerBinding { owner: 43, ..bound },
        na::OwnerBinding {
            party_uid: 100,
            ..bound
        },
        na::OwnerBinding {
            revision: 0,
            ..bound
        },
        na::OwnerBinding {
            revision: 24,
            ..bound
        },
        na::OwnerBinding {
            revision: u64::MAX,
            ..bound
        },
    ] {
        cases.push(na::TargetSnapshot {
            binding: Some(binding),
            ..base
        });
    }
    cases.push(na::TargetSnapshot {
        kind: na::ActorKind::Human,
        current_session: false,
        binding: None,
        ..base
    });
    cases
}

fn authority(counts: &mut Counts) {
    let mutations = [
        na::Mutation::Summon,
        na::Mutation::Dismiss,
        na::Mutation::Order,
        na::Mutation::Gear,
    ];
    let accepted = na::InvitationOutcome::Accepted {
        inviter: 42,
        invitee: 301,
        party_uid: 99,
    };
    let invitations = [
        accepted,
        na::InvitationOutcome::Pending,
        na::InvitationOutcome::Declined,
        na::InvitationOutcome::Refused,
        na::InvitationOutcome::Accepted {
            inviter: 43,
            invitee: 301,
            party_uid: 99,
        },
        na::InvitationOutcome::Accepted {
            inviter: 42,
            invitee: 302,
            party_uid: 99,
        },
        na::InvitationOutcome::Accepted {
            inviter: 42,
            invitee: 301,
            party_uid: 100,
        },
    ];
    for actor in requesters() {
        counts.result(
            "requester",
            &na::validate_requester(&actor),
            &ca::validate_requester(&requester(actor)),
            actor,
        );
        for subject in targets() {
            let context = (actor, subject);
            counts.result(
                "authorize",
                &na::authorize_owned_bot(&actor, &subject),
                &ca::authorize_owned_bot(&requester(actor), &target(subject)),
                context,
            );
            for mutation_kind in mutations {
                let old = na::issue_ticket(mutation_kind, &actor, &subject);
                let new =
                    ca::issue_ticket(mutation(mutation_kind), &requester(actor), &target(subject));
                counts.result("ticket.issue", &old, &new, (mutation_kind, context));
                if let (Ok(old), Ok(new)) = (old, new) {
                    counts.compare(
                        "ticket.accessors",
                        (old.mutation(), old.owner(), old.target()),
                        (new.mutation(), new.owner(), new.target()),
                        context,
                    );
                    counts.result(
                        "ticket.validate",
                        &na::validate_ticket(&old, &actor, &subject),
                        &ca::validate_ticket(&new, &requester(actor), &target(subject)),
                        context,
                    );
                }
            }
            // Both a free and an already-bound target matter for acceptance precedence.
            for invitee in [
                subject,
                na::TargetSnapshot {
                    binding: None,
                    ..subject
                },
            ] {
                for outcome in invitations {
                    for revision in [0, 1, u64::MAX] {
                        counts.result(
                            "binding",
                            &na::binding_from_accepted_invitation(
                                outcome, &actor, &invitee, revision,
                            ),
                            &ca::binding_from_accepted_invitation(
                                invitation(outcome),
                                &requester(actor),
                                &target(invitee),
                                revision,
                            ),
                            (outcome, actor, invitee, revision),
                        );
                    }
                }
            }
        }
    }
    for mutation_kind in mutations {
        let old = na::issue_ticket(mutation_kind, &owner(), &bot()).unwrap();
        let new =
            ca::issue_ticket(mutation(mutation_kind), &requester(owner()), &target(bot())).unwrap();
        for actor in requesters() {
            for subject in targets() {
                counts.result(
                    "ticket.validate",
                    &na::validate_ticket(&old, &actor, &subject),
                    &ca::validate_ticket(&new, &requester(actor), &target(subject)),
                    (actor, subject),
                );
            }
        }
        // New owner/party can be fully valid now while the retained ticket is stale.
        for (new_owner, new_party, revision) in [(43, 99, 24), (42, 100, 24), (42, 99, 24)] {
            let actor = na::RequesterSnapshot {
                actor_id: new_owner,
                party_uid: Some(new_party),
                ..owner()
            };
            let subject = na::TargetSnapshot {
                party_uid: Some(new_party),
                binding: Some(na::OwnerBinding {
                    owner: new_owner,
                    party_uid: new_party,
                    revision,
                }),
                ..bot()
            };
            counts.result(
                "ticket.validate",
                &na::validate_ticket(&old, &actor, &subject),
                &ca::validate_ticket(&new, &requester(actor), &target(subject)),
                (actor, subject),
            );
        }
    }
}

fn selection(counts: &mut Counts) {
    let first = ns::Candidate {
        name: "Echo",
        target: bot(),
    };
    let second = ns::Candidate {
        name: "Fern",
        target: na::TargetSnapshot {
            actor_id: 302,
            ..bot()
        },
    };
    let mut rosters = vec![
        vec![],
        vec![first],
        vec![second, first],
        vec![first, second],
    ];
    for subject in targets() {
        for name in [
            "Echo",
            "ECHO",
            "All",
            "",
            "bad-name",
            "Néhà",
            "abcdefghijklmnop",
            "abcdefghijklmnopq",
            "private\ninvalid",
        ] {
            rosters.push(vec![
                ns::Candidate {
                    name,
                    target: subject,
                },
                first,
            ]);
            rosters.push(vec![
                first,
                ns::Candidate {
                    name,
                    target: subject,
                },
            ]);
        }
    }
    for length in [6, 7] {
        rosters.push(
            (0..length)
                .map(|i| ns::Candidate {
                    name: if i == 0 { "Echo" } else { "Fern" },
                    target: na::TargetSnapshot {
                        actor_id: 301 + i,
                        ..bot()
                    },
                })
                .collect(),
        );
    }
    let selectors: Vec<_> = std::iter::once(nc::Target::All)
        .chain(
            [
                "Echo",
                "eChO",
                "Ech",
                "Missing",
                "all",
                "ALL",
                "",
                " Echo",
                "Echo ",
                "Echo2",
                "Néhà",
                "abcdefghijklmnop",
                "abcdefghijklmnopq",
            ]
            .into_iter()
            .map(|name| nc::Target::Name(name.into())),
        )
        .collect();
    for actor in [
        owner(),
        na::RequesterSnapshot {
            actor_id: 0,
            ..owner()
        },
    ] {
        for (index, roster) in rosters.iter().enumerate() {
            let shared: Vec<_> = roster
                .iter()
                .map(|c| cs::Candidate {
                    name: c.name,
                    target: target(c.target),
                })
                .collect();
            for wanted in &selectors {
                counts.result(
                    "selection",
                    &ns::select_owned(&actor, wanted, roster),
                    &cs::select_owned(&requester(actor), &selector(wanted), &shared),
                    (index, wanted, actor),
                );
            }
        }
    }
}

fn live_session(generation: u64) -> no::OrderSession {
    no::OrderSession {
        generation,
        in_zone: true,
        transition_pending: false,
        event_active: false,
        shutting_down: false,
        superseded: false,
        alive: true,
        zone: 100,
    }
}

fn session_cases(generation: u64) -> Vec<Option<no::OrderSession>> {
    let base = live_session(generation);
    let mut cases = vec![Some(base), None];
    for value in [0, generation + 1, u64::MAX] {
        cases.push(Some(no::OrderSession {
            generation: value,
            ..base
        }));
    }
    for zone in [0, 101] {
        cases.push(Some(no::OrderSession { zone, ..base }));
    }
    for bits in 0..64 {
        cases.push(Some(no::OrderSession {
            in_zone: bits & 1 == 0,
            transition_pending: bits & 2 != 0,
            event_active: bits & 4 != 0,
            shutting_down: bits & 8 != 0,
            superseded: bits & 16 != 0,
            alive: bits & 32 == 0,
            ..base
        }));
    }
    cases
}

fn enemy() -> no::EngageTarget {
    no::EngageTarget {
        actor_id: 501,
        zone: 100,
        hostile_mob: true,
        alive: true,
        claim: no::Claim::Unclaimed,
    }
}

fn enemy_cases() -> Vec<Option<no::EngageTarget>> {
    let mut cases = vec![None];
    for actor_id in [0, 501, 502] {
        for zone in [0, 100, 101] {
            for hostile_mob in [false, true] {
                for alive in [false, true] {
                    for claim in [
                        no::Claim::Unclaimed,
                        no::Claim::OwnerParty,
                        no::Claim::Other,
                    ] {
                        cases.push(Some(no::EngageTarget {
                            actor_id,
                            zone,
                            hostile_mob,
                            alive,
                            claim,
                        }));
                    }
                }
            }
        }
    }
    cases
}

fn orders() -> Vec<no::Order> {
    let mut orders = vec![
        no::Order::Follow,
        no::Order::Stay,
        no::Order::Rest,
        no::Order::Attack,
        no::Order::Pull,
        no::Order::Assist,
    ];
    for role in [
        no::Role::Tank,
        no::Role::Healer,
        no::Role::Dps,
        no::Role::Puller,
    ] {
        orders.push(no::Order::Role {
            name: "Echo".into(),
            role,
        });
    }
    orders
}

#[derive(Clone, Debug)]
struct Scenario {
    owner: na::RequesterSnapshot,
    owner_session: Option<no::OrderSession>,
    order: no::Order,
    bots: Vec<no::OrderCandidate<'static>>,
    scene: no::Scene,
}

fn baseline(order: no::Order) -> Scenario {
    Scenario {
        owner: owner(),
        owner_session: Some(live_session(11)),
        order,
        bots: vec![
            no::OrderCandidate {
                identity: ns::Candidate {
                    name: "Echo",
                    target: bot(),
                },
                session: Some(live_session(17)),
                control: no::Control::Open,
            },
            no::OrderCandidate {
                identity: ns::Candidate {
                    name: "Fern",
                    target: na::TargetSnapshot {
                        actor_id: 302,
                        ..bot()
                    },
                },
                session: Some(live_session(17)),
                control: no::Control::Open,
            },
        ],
        scene: no::Scene {
            owner_target: Some(enemy()),
            main_tank: no::MainTank::Member {
                actor_id: 301,
                party_uid: 99,
                engaged: Some(enemy()),
            },
        },
    }
}

fn variants(base: &Scenario) -> Vec<Scenario> {
    let mut cases = vec![base.clone()];
    for actor in requesters() {
        let mut c = base.clone();
        c.owner = actor;
        cases.push(c);
    }
    for current in session_cases(11) {
        let mut c = base.clone();
        c.owner_session = current;
        cases.push(c);
    }
    for current in session_cases(17) {
        let mut c = base.clone();
        c.bots[0].session = current;
        cases.push(c);
    }
    for subject in targets() {
        let mut c = base.clone();
        c.bots[0].identity.target = subject;
        cases.push(c);
    }
    for current in enemy_cases() {
        let mut c = base.clone();
        c.scene.owner_target = current;
        cases.push(c);
        let mut c = base.clone();
        c.scene.main_tank = no::MainTank::Member {
            actor_id: 301,
            party_uid: 99,
            engaged: current,
        };
        cases.push(c);
    }
    for main_tank in [
        no::MainTank::None,
        no::MainTank::Ambiguous,
        no::MainTank::Member {
            actor_id: 0,
            party_uid: 99,
            engaged: Some(enemy()),
        },
        no::MainTank::Member {
            actor_id: 301,
            party_uid: 100,
            engaged: Some(enemy()),
        },
        no::MainTank::Member {
            actor_id: 302,
            party_uid: 99,
            engaged: Some(enemy()),
        },
        no::MainTank::Member {
            actor_id: 303,
            party_uid: 99,
            engaged: Some(enemy()),
        },
    ] {
        let mut c = base.clone();
        c.scene.main_tank = main_tank;
        cases.push(c);
    }
    let mut closed = base.clone();
    closed.bots[0].control = no::Control::Closed;
    cases.push(closed);
    for name in ["", "All", "ECHO", "Fern", "Bad-Name", "abcdefghijklmnopq"] {
        let mut c = base.clone();
        c.bots[0].identity.name = name;
        cases.push(c);
    }
    for count in [0, 1, 6, 7] {
        let mut c = base.clone();
        c.bots = (0..count)
            .map(|i| no::OrderCandidate {
                identity: ns::Candidate {
                    name: if i == 0 { "Echo" } else { "Fern" },
                    target: na::TargetSnapshot {
                        actor_id: 301 + i,
                        ..bot()
                    },
                },
                session: Some(live_session(17)),
                control: no::Control::Open,
            })
            .collect();
        cases.push(c);
    }
    let mut duplicate = base.clone();
    duplicate.bots[1].identity.target.actor_id = 301;
    cases.push(duplicate);
    let mut ambiguous = base.clone();
    ambiguous.bots[1].identity.name = "ECHO";
    cases.push(ambiguous);
    for name in ["all", "", "Missing", "Bad-Name", "ECHO"] {
        let mut c = base.clone();
        c.order = no::Order::Role {
            name: name.into(),
            role: no::Role::Tank,
        };
        cases.push(c);
    }
    cases
}

fn prepare_case(counts: &mut Counts, case: &Scenario) {
    let current: Vec<_> = case.bots.iter().copied().map(candidate).collect();
    let old = no::prepare(
        &case.owner,
        case.owner_session,
        &case.order,
        &case.bots,
        &case.scene,
    );
    let new = co::prepare(
        &requester(case.owner),
        case.owner_session.map(session),
        &order(&case.order),
        &current,
        &scene(case.scene),
    );
    counts.result("orders.prepare", &old, &new, case);
    if let (Ok(old), Ok(new)) = (&old, &new) {
        for (old, new) in old.iter().zip(new) {
            match (old, new) {
                (no::TargetOutcome::Prepared(old), co::TargetOutcome::Prepared(new)) => {
                    counts.prepared += 1;
                    counts.compare(
                        "plan.accessors",
                        (old.ticket(), old.directive()),
                        (new.ticket(), new.directive()),
                        case,
                    );
                    let index = case
                        .bots
                        .iter()
                        .position(|c| c.identity.target.actor_id == old.ticket().target())
                        .unwrap();
                    counts.result(
                        "orders.revalidate",
                        &no::revalidate(
                            old,
                            &case.owner,
                            case.owner_session,
                            &case.order,
                            &case.bots[index],
                            &case.scene,
                        ),
                        &co::revalidate(
                            new,
                            &requester(case.owner),
                            case.owner_session.map(session),
                            &order(&case.order),
                            &current[index],
                            &scene(case.scene),
                        ),
                        case,
                    );
                }
                (no::TargetOutcome::Refused { reason, .. }, co::TargetOutcome::Refused { .. }) => {
                    counts.refused += 1;
                    *counts
                        .coverage
                        .entry(format!("orders.outcome:Refused({reason:?})"))
                        .or_default() += 1;
                }
                _ => unreachable!("full preparation results already compared"),
            }
        }
    }
}

fn planner(counts: &mut Counts) {
    for requested in orders() {
        let base = baseline(requested);
        let fresh_cases = variants(&base);
        for case in &fresh_cases {
            prepare_case(counts, case);
        }
        let current: Vec<_> = base.bots.iter().copied().map(candidate).collect();
        let old = no::prepare(
            &base.owner,
            base.owner_session,
            &base.order,
            &base.bots,
            &base.scene,
        )
        .unwrap();
        let new = co::prepare(
            &requester(base.owner),
            base.owner_session.map(session),
            &order(&base.order),
            &current,
            &scene(base.scene),
        )
        .unwrap();
        for (old, new) in old.iter().zip(&new) {
            let (no::TargetOutcome::Prepared(old), co::TargetOutcome::Prepared(new)) = (old, new)
            else {
                continue;
            };
            // Revalidate the retained ticket against every one-field or boundary
            // mutation, including other identity/owner bindings and replacement orders.
            let original_index = base
                .bots
                .iter()
                .position(|c| c.identity.target.actor_id == old.ticket().target())
                .unwrap();
            for case in &fresh_cases {
                if let Some(subject) = case.bots.get(original_index) {
                    counts.result(
                        "orders.revalidate",
                        &no::revalidate(
                            old,
                            &case.owner,
                            case.owner_session,
                            &case.order,
                            subject,
                            &case.scene,
                        ),
                        &co::revalidate(
                            new,
                            &requester(case.owner),
                            case.owner_session.map(session),
                            &order(&case.order),
                            &candidate(*subject),
                            &scene(case.scene),
                        ),
                        case,
                    );
                }
            }
            for replacement in orders() {
                counts.result(
                    "orders.revalidate",
                    &no::revalidate(
                        old,
                        &base.owner,
                        base.owner_session,
                        &replacement,
                        &base.bots[original_index],
                        &base.scene,
                    ),
                    &co::revalidate(
                        new,
                        &requester(base.owner),
                        base.owner_session.map(session),
                        &order(&replacement),
                        &current[original_index],
                        &scene(base.scene),
                    ),
                    (&base.order, replacement),
                );
            }
        }
    }
}

fn quoted(value: &str) -> String {
    let mut out = String::from("\"");
    for ch in value.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '\"' => out.push_str("\\\""),
            ch if ch < ' ' => out.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn main() {
    let mut counts = Counts::default();
    authority(&mut counts);
    selection(&mut counts);
    planner(&mut counts);
    assert!(
        counts.prepared > 0 && counts.refused > 0,
        "must cover both executable plans and per-bot refusals"
    );
    for key in [
        "binding:Ok",
        "authorize:Ok",
        "ticket.validate:Err(StaleTicket)",
        "selection:Err(AmbiguousName)",
        "selection:Err(DuplicateActor)",
        "orders.prepare:Ok",
        "orders.prepare:Err(Requester(TargetClaimed))",
        "orders.prepare:Err(Requester(AmbiguousMainTank))",
        "orders.revalidate:Err(StaleOrder)",
        "orders.revalidate:Err(Authority(StaleTicket))",
    ] {
        assert!(
            counts.coverage.get(key).copied().unwrap_or(0) > 0,
            "missing contract coverage: {key}"
        );
    }
    let entries = counts
        .coverage
        .iter()
        .map(|(key, value)| format!("{}:{value}", quoted(key)))
        .collect::<Vec<_>>()
        .join(",");
    println!("{{\"status\":\"PASS\",\"comparisons\":{},\"prepared_outcomes\":{},\"refused_outcomes\":{},\"coverage\":{{{entries}}}}}",
        counts.comparisons, counts.prepared, counts.refused);
}
