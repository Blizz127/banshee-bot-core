use banshee_bot_core::brain::{command, orders};
use banshee_bot_core::roles::Role;
use banshee_bot_core::sched::control::{Clock, Operation, Phase, Refusal};
use std::num::NonZeroU64;

fn revision(value: u64) -> NonZeroU64 {
    NonZeroU64::new(value).unwrap()
}

#[test]
fn current_commands_preserve_first_parser_ownership() {
    use command::Command;
    for (input, expected) in [
        (" /fb fill ", Command::Fill(None)),
        ("/FB FiLl TaNk", Command::Fill(Some(Role::Tank))),
        ("/fb fill healer", Command::Fill(Some(Role::Healer))),
        ("/fb fill DPS", Command::Fill(Some(Role::Dps))),
        ("/fb rally", Command::Rally { clear: false }),
        ("/fb rally CLEAR", Command::Rally { clear: true }),
        (" /FB PuLlBaCk ", Command::PullBack),
        ("/fb FALLBACK", Command::FallBack),
    ] {
        assert_eq!(
            command::parse(input.as_bytes()),
            Ok(Some(expected)),
            "{input}"
        );
        assert_eq!(orders::parse(input.as_bytes()), Ok(None), "{input}");
    }
}

#[test]
fn invalid_setting_precedes_extra_arguments_but_text_checks_come_first() {
    use command::ParseError;
    for (input, expected) in [
        ("/fb fill puller extra", ParseError::InvalidName),
        ("/fb fill tank extra", ParseError::TooManyArguments),
        ("/fb rally 0 extra", ParseError::InvalidName),
        ("/fb rally clear extra", ParseError::TooManyArguments),
        ("/fb fallback all", ParseError::TooManyArguments),
        ("/fb pullback owner=9", ParseError::TooManyArguments),
    ] {
        assert_eq!(command::parse(input.as_bytes()), Err(expected), "{input}");
        assert_eq!(orders::parse(input.as_bytes()), Ok(None), "{input}");
    }
    let mut too_long = b"/fb fill\0".to_vec();
    too_long.resize(command::MAX_COMMAND_BYTES + 1, b' ');
    assert_eq!(command::parse(&too_long), Err(ParseError::TooLong));
    assert_eq!(
        command::parse(b"/fb rally\tclear"),
        Err(ParseError::InvalidText)
    );
    assert_eq!(command::parse(b"/fbrally clear"), Ok(None));
}

#[test]
fn fallback_replacement_and_owner_orders_invalidate_queued_work() {
    let mut clock = Clock::default();
    let old_work = clock.order(revision(31)).unwrap();
    let retreat = clock.begin(Operation::Fallback, revision(31)).unwrap();
    let before = clock.snapshot();
    assert_eq!(clock.admit(Some(old_work), false), Err(Refusal::Stale));
    assert_eq!(clock.admit(Some(retreat), false), Err(Refusal::Closed));
    assert_eq!(clock.can_order(revision(31)), Ok(()));
    assert_eq!(clock.can_order(revision(32)), Err(Refusal::Stale));
    assert_eq!(clock.order(revision(32)), Err(Refusal::Stale));
    assert_eq!(
        clock.begin(Operation::Fallback, revision(32)),
        Err(Refusal::Closed)
    );
    for operation in [Operation::Gear, Operation::Summon, Operation::Dismiss] {
        assert_eq!(clock.begin(operation, revision(31)), Err(Refusal::Closed));
    }
    assert_eq!(clock.snapshot(), before);

    let replacement = clock.begin(Operation::Fallback, revision(31)).unwrap();
    assert_eq!(replacement.epoch, retreat.epoch + 1);
    assert_eq!(clock.admit(Some(retreat), false), Err(Refusal::Stale));
    let current = clock.order(revision(31)).unwrap();
    assert_eq!(current.epoch, replacement.epoch + 1);
    assert_eq!(clock.snapshot().phase, Phase::Active);
    assert_eq!(clock.admit(Some(replacement), false), Err(Refusal::Stale));
    assert_eq!(clock.admit(Some(current), false), Ok(()));
}

#[test]
fn fallback_binding_changes_end_retreat_without_reviving_old_work() {
    let mut clock = Clock::default();
    let retreat = clock.begin(Operation::Fallback, revision(41)).unwrap();
    let before = clock.snapshot();
    assert_eq!(clock.binding_changed(Some(revision(41))), Ok(None));
    assert_eq!(clock.snapshot(), before);
    let rebound = clock.binding_changed(Some(revision(42))).unwrap().unwrap();
    assert_eq!(clock.snapshot().phase, Phase::Active);
    assert_eq!(clock.admit(Some(retreat), false), Err(Refusal::Stale));
    assert_eq!(clock.admit(Some(rebound), false), Ok(()));

    let next_retreat = clock.begin(Operation::Fallback, revision(42)).unwrap();
    let detached = clock.binding_changed(None).unwrap().unwrap();
    assert_eq!(clock.snapshot().phase, Phase::Detached);
    assert_eq!(clock.admit(Some(next_retreat), false), Err(Refusal::Stale));
    assert_eq!(clock.admit(Some(detached), true), Err(Refusal::Closed));
    assert_eq!(clock.order(revision(42)), Err(Refusal::Closed));
    let invitation = clock.human_invitation().unwrap();
    assert_eq!(clock.admit(Some(invitation), false), Err(Refusal::Closed));
    assert_eq!(clock.admit(Some(invitation), true), Ok(()));
}

#[test]
fn durable_operations_still_require_their_native_completion() {
    for operation in [Operation::Gear, Operation::Summon, Operation::Dismiss] {
        let mut clock = Clock::default();
        let pending = clock.begin(operation, revision(51)).unwrap();
        let revoked = clock.binding_changed(None).unwrap().unwrap();
        let rebound = clock.binding_changed(Some(revision(52))).unwrap().unwrap();
        assert_eq!(clock.snapshot().phase, Phase::Fenced(operation));
        assert_eq!(clock.admit(Some(pending), false), Err(Refusal::Stale));
        assert_eq!(clock.admit(Some(revoked), false), Err(Refusal::Stale));
        assert_eq!(clock.admit(Some(rebound), false), Err(Refusal::Closed));
        assert_eq!(
            clock.begin(Operation::Fallback, revision(52)),
            Err(Refusal::Closed)
        );
        assert_eq!(clock.can_order(revision(52)), Err(Refusal::Closed));
        assert_eq!(clock.order(revision(52)), Err(Refusal::Closed));
        assert_eq!(clock.human_invitation(), Err(Refusal::Closed));
    }
}
