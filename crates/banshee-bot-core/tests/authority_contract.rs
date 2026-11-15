use banshee_bot_core::brain::{
    authority::{
        self, ActorKind, Denial, InvitationOutcome, Mutation, OwnerBinding, RequesterSnapshot,
        TargetSnapshot,
    },
    command::Target,
    selection::{select_owned, Candidate, SelectionError},
};

fn fixture() -> (RequesterSnapshot, TargetSnapshot) {
    (
        RequesterSnapshot {
            actor_id: 17,
            kind: ActorKind::Human,
            current_session: true,
            generation: 31,
            party_uid: Some(81),
        },
        TargetSnapshot {
            actor_id: 29,
            kind: ActorKind::PopulationBot,
            registered_population: true,
            current_session: true,
            generation: 42,
            party_uid: Some(81),
            binding: Some(OwnerBinding {
                owner: 17,
                party_uid: 81,
                revision: 53,
            }),
        },
    )
}

#[test]
fn unavailable_owned_members_can_be_selected_but_cannot_receive_mutations() {
    let (owner, mut bot) = fixture();
    bot.current_session = false;
    bot.generation = 0;
    assert_eq!(
        select_owned(
            &owner,
            &Target::Name("zOeY".into()),
            &[Candidate {
                target: bot,
                name: "Zoey"
            }]
        ),
        Ok(vec![0])
    );
    for mutation in [
        Mutation::Summon,
        Mutation::Dismiss,
        Mutation::Order,
        Mutation::Gear,
    ] {
        assert_eq!(
            authority::issue_ticket(mutation, &owner, &bot),
            Err(Denial::TargetUnavailable)
        );
    }
    // A missing session does not conceal an ownership failure.
    bot.binding.as_mut().unwrap().owner = 18;
    assert_eq!(
        authority::issue_ticket(Mutation::Order, &owner, &bot),
        Err(Denial::WrongOwner)
    );
}

#[test]
fn tickets_expire_on_relog_or_new_binding_even_for_the_same_named_party() {
    let (owner, bot) = fixture();
    let ticket = authority::issue_ticket(Mutation::Order, &owner, &bot).unwrap();
    assert_eq!(
        (ticket.mutation(), ticket.owner(), ticket.target()),
        (Mutation::Order, 17, 29)
    );
    assert_eq!(authority::validate_ticket(&ticket, &owner, &bot), Ok(()));
    let relogged = RequesterSnapshot {
        generation: 32,
        ..owner
    };
    assert_eq!(
        authority::validate_ticket(&ticket, &relogged, &bot),
        Err(Denial::StaleTicket)
    );
    let mut changed = bot;
    changed.binding.as_mut().unwrap().revision += 1;
    assert_eq!(
        authority::validate_ticket(&ticket, &owner, &changed),
        Err(Denial::StaleTicket)
    );
    changed = TargetSnapshot {
        generation: 43,
        ..bot
    };
    assert_eq!(
        authority::validate_ticket(&ticket, &owner, &changed),
        Err(Denial::StaleTicket)
    );
    // Fresh ownership validation takes precedence over stale-ticket diagnosis.
    changed.binding.as_mut().unwrap().owner = 18;
    assert_eq!(
        authority::validate_ticket(&ticket, &owner, &changed),
        Err(Denial::WrongOwner)
    );
}

#[test]
fn binding_requires_a_matching_completed_acceptance_and_an_unbound_bot() {
    let (owner, mut bot) = fixture();
    let accepted = InvitationOutcome::Accepted {
        inviter: 17,
        invitee: 29,
        party_uid: 81,
    };
    assert_eq!(
        authority::binding_from_accepted_invitation(accepted, &owner, &bot, 54),
        Err(Denial::AlreadyBound)
    );
    bot.binding = None;
    assert_eq!(
        authority::binding_from_accepted_invitation(accepted, &owner, &bot, 54),
        Ok(OwnerBinding {
            owner: 17,
            party_uid: 81,
            revision: 54
        })
    );
    let invalid_owner = RequesterSnapshot {
        actor_id: 0,
        ..owner
    };
    assert_eq!(
        authority::binding_from_accepted_invitation(
            InvitationOutcome::Pending,
            &invalid_owner,
            &bot,
            0
        ),
        Err(Denial::InvitationNotAccepted)
    );
    let wrong_receipt = InvitationOutcome::Accepted {
        inviter: 18,
        invitee: 29,
        party_uid: 81,
    };
    assert_eq!(
        authority::binding_from_accepted_invitation(wrong_receipt, &owner, &bot, 0),
        Err(Denial::InvitationMismatch)
    );
    assert_eq!(
        authority::binding_from_accepted_invitation(accepted, &owner, &bot, 0),
        Err(Denial::InvalidBinding)
    );
}

#[test]
fn foreign_rows_cannot_leak_names_or_invalidate_owned_selection() {
    let (owner, bot) = fixture();
    let own = Candidate {
        target: bot,
        name: "Zoey",
    };
    let mut foreign = Candidate {
        target: bot,
        name: "Private\nMalformedName",
    };
    foreign.target.binding.as_mut().unwrap().owner = 18;
    assert_eq!(
        select_owned(&owner, &Target::All, &[foreign, own]),
        Ok(vec![1])
    );
    assert_eq!(
        select_owned(&owner, &Target::Name("Zoey".into()), &[foreign, own]),
        Ok(vec![1])
    );
    let duplicate = Candidate {
        name: "Invalid\n",
        ..own
    };
    assert_eq!(
        select_owned(&owner, &Target::All, &[own, duplicate]),
        Err(SelectionError::DuplicateActor)
    );
    let same_name = Candidate {
        target: TargetSnapshot {
            actor_id: 30,
            ..bot
        },
        name: "ZOEY",
    };
    assert_eq!(
        select_owned(&owner, &Target::All, &[same_name, own]),
        Ok(vec![0, 1])
    );
    assert_eq!(
        select_owned(&owner, &Target::Name("Zoey".into()), &[same_name, own]),
        Err(SelectionError::AmbiguousName)
    );
}

#[test]
fn requester_capacity_and_exact_selector_checks_have_stable_precedence() {
    let (owner, bot) = fixture();
    let rows = [Candidate {
        target: bot,
        name: "Zoey",
    }; 7];
    let malformed = Target::Name("ALL".into());
    assert_eq!(
        select_owned(&owner, &malformed, &rows),
        Err(SelectionError::TooManyCandidates)
    );
    assert_eq!(
        select_owned(&owner, &malformed, &[]),
        Err(SelectionError::InvalidSelector)
    );
    let invalid = RequesterSnapshot {
        kind: ActorKind::PersonaBot,
        ..owner
    };
    assert_eq!(
        select_owned(&invalid, &malformed, &rows),
        Err(SelectionError::Unauthorized(Denial::InvalidRequester))
    );
    assert_eq!(select_owned(&owner, &Target::All, &[]), Ok(vec![]));
    assert_eq!(
        select_owned(&owner, &Target::Name("Zoey".into()), &[]),
        Err(SelectionError::NotFound)
    );
}
