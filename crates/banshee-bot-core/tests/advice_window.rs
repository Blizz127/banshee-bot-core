use banshee_bot_core::brain::advice_window::{
    AdviceWindow, Outcome, PendingReason, Reply, Resolution, WindowError,
};
use banshee_bot_core::brain::decision::{
    ActionClass, ActionId, Advice, AdviceRejection, AdviceStatus, Decision, FrameId, LegalAction,
    Priority,
};
use banshee_bot_core::brain::strategy::{
    prepare, PreparedFrame, ProposalWriter, Strategy, StrategyBinding, StrategyFailure, StrategyId,
};

const FRAME: FrameId = FrameId(61);
const REVERSED: [ActionId; 2] = [ActionId(2), ActionId(1)];

fn prepared(priority: Priority, classes: &[ActionClass]) -> PreparedFrame {
    struct Emit<'a>(&'a [LegalAction]);
    impl Strategy<()> for Emit<'_> {
        fn evaluate(&self, _: &(), output: &mut ProposalWriter<'_>) -> Result<(), StrategyFailure> {
            for action in self.0 {
                output
                    .emit(action.id, 4, true)
                    .map_err(|_| StrategyFailure::Refused)?;
            }
            Ok(())
        }
    }
    let legal = classes
        .iter()
        .enumerate()
        .map(|(index, class)| LegalAction {
            id: ActionId(index as u32 + 1),
            class: *class,
        })
        .collect::<Vec<_>>();
    let strategy = Emit(&legal);
    prepare(
        FRAME,
        &legal,
        &(),
        &[StrategyBinding {
            id: StrategyId(1),
            priority,
            strategy: &strategy,
        }],
    )
    .unwrap()
}

fn choices() -> PreparedFrame {
    prepared(
        Priority::Role,
        &[ActionClass::Movement, ActionClass::Social],
    )
}

fn ready(outcome: Outcome) -> (Decision, Resolution) {
    match outcome {
        Outcome::Ready { decision, reason } => (decision, reason),
        _ => panic!("expected one ready decision"),
    }
}

#[test]
fn safety_owner_economy_single_and_empty_frames_need_no_advice() {
    let cases: &[(Priority, &[ActionClass])] = &[
        (
            Priority::Safety,
            &[ActionClass::Movement, ActionClass::Combat],
        ),
        (
            Priority::OwnerOrder,
            &[ActionClass::Movement, ActionClass::Social],
        ),
        (Priority::Goal, &[ActionClass::Social, ActionClass::Economy]),
        (Priority::Role, &[ActionClass::Movement]),
        (Priority::Goal, &[]),
    ];
    for (priority, classes) in cases {
        for wait in [0, 10] {
            let frame = prepared(*priority, classes);
            let fallback = frame.fallback().clone();
            let mut window = AdviceWindow::new(frame, 100, wait).unwrap();
            assert!(window.request().is_none());
            let (decision, reason) = ready(
                window
                    .poll(
                        500,
                        Some(Reply::Ranking(Advice {
                            frame: FrameId(0),
                            ranking: &REVERSED,
                        })),
                    )
                    .unwrap(),
            );
            assert_eq!(reason, Resolution::NoAdviceChoices);
            assert_eq!(decision, fallback);
            assert!(matches!(window.poll(0, None).unwrap(), Outcome::Closed));
            assert!(!window.cancel());
        }
    }
}

#[test]
fn a_matching_ranking_resolves_once_and_equal_timestamps_are_valid() {
    let mut window = AdviceWindow::new(choices(), 100, 10).unwrap();
    let request = window.request().unwrap();
    assert_eq!(request.frame, FRAME);
    assert_eq!(request.choices, &[ActionId(1), ActionId(2)]);
    assert_eq!(request.deadline_ms, 110);
    assert!(matches!(
        window.poll(100, None).unwrap(),
        Outcome::Pending(PendingReason::AwaitingReply)
    ));
    let (decision, reason) = ready(
        window
            .poll(
                100,
                Some(Reply::Ranking(Advice {
                    frame: FRAME,
                    ranking: &REVERSED,
                })),
            )
            .unwrap(),
    );
    assert_eq!(reason, Resolution::Ranking);
    assert_eq!(decision.frame, FRAME);
    assert_eq!(decision.action, Some(ActionId(2)));
    assert_eq!(decision.advice, AdviceStatus::Applied);
    assert!(window.request().is_none());
    assert!(matches!(
        window
            .poll(0, Some(Reply::Unavailable { frame: FRAME }))
            .unwrap(),
        Outcome::Closed
    ));
    assert!(!window.cancel());
}

#[test]
fn invalid_matching_rankings_consume_the_window_with_the_frozen_fallback() {
    let cases: &[(&[ActionId], AdviceRejection)] = &[
        (&[], AdviceRejection::InvalidLength),
        (
            &[ActionId(2), ActionId(2)],
            AdviceRejection::DuplicateAction,
        ),
        (
            &[ActionId(2), ActionId(999)],
            AdviceRejection::IneligibleAction,
        ),
    ];
    for (ranking, rejection) in cases {
        let frame = choices();
        let mut expected = frame.fallback().clone();
        expected.advice = AdviceStatus::Rejected(*rejection);
        let mut window = AdviceWindow::new(frame, 100, 10).unwrap();
        let (decision, reason) = ready(
            window
                .poll(
                    101,
                    Some(Reply::Ranking(Advice {
                        frame: FRAME,
                        ranking,
                    })),
                )
                .unwrap(),
        );
        assert_eq!(reason, Resolution::Ranking);
        assert_eq!(decision, expected);
        assert!(window.request().is_none());
        assert!(matches!(window.poll(102, None).unwrap(), Outcome::Closed));
    }
}

#[test]
fn stale_replies_leave_the_current_frame_open_without_extending_its_deadline() {
    let mut window = AdviceWindow::new(choices(), 100, 10).unwrap();
    assert!(matches!(
        window
            .poll(
                101,
                Some(Reply::Ranking(Advice {
                    frame: FrameId(60),
                    ranking: &[]
                }))
            )
            .unwrap(),
        Outcome::Pending(PendingReason::StaleReply)
    ));
    assert!(matches!(
        window
            .poll(102, Some(Reply::Unavailable { frame: FrameId(62) }))
            .unwrap(),
        Outcome::Pending(PendingReason::StaleReply)
    ));
    assert!(matches!(
        window.poll(102, None).unwrap(),
        Outcome::Pending(PendingReason::AwaitingReply)
    ));
    let request = window.request().unwrap();
    assert_eq!(request.frame, FRAME);
    assert_eq!(request.deadline_ms, 110);
    let (decision, reason) = ready(
        window
            .poll(
                109,
                Some(Reply::Ranking(Advice {
                    frame: FRAME,
                    ranking: &REVERSED,
                })),
            )
            .unwrap(),
    );
    assert_eq!(reason, Resolution::Ranking);
    assert_eq!(decision.action, Some(ActionId(2)));
}

#[test]
fn exact_late_and_zero_budget_deadlines_ignore_any_ranking() {
    for (wait, poll_at, reply_frame) in [
        (10, 110, FRAME),
        (10, 115, FrameId(0)),
        (0, 100, FRAME),
        (0, 105, FRAME),
    ] {
        let frame = choices();
        let fallback = frame.fallback().clone();
        let mut window = AdviceWindow::new(frame, 100, wait).unwrap();
        assert_eq!(window.request().is_none(), wait == 0);
        let (decision, reason) = ready(
            window
                .poll(
                    poll_at,
                    Some(Reply::Ranking(Advice {
                        frame: reply_frame,
                        ranking: &REVERSED,
                    })),
                )
                .unwrap(),
        );
        assert_eq!(reason, Resolution::Deadline);
        assert_eq!(decision, fallback);
        assert!(window.request().is_none());
        assert!(matches!(
            window.poll(poll_at, None).unwrap(),
            Outcome::Closed
        ));
    }
}

#[test]
fn matching_unavailability_returns_the_fallback_once() {
    let frame = choices();
    let fallback = frame.fallback().clone();
    let mut window = AdviceWindow::new(frame, 100, 10).unwrap();
    let (decision, reason) = ready(
        window
            .poll(109, Some(Reply::Unavailable { frame: FRAME }))
            .unwrap(),
    );
    assert_eq!(reason, Resolution::Unavailable);
    assert_eq!(decision, fallback);
    assert!(window.request().is_none());
    assert!(!window.cancel());
    assert!(matches!(
        window
            .poll(
                109,
                Some(Reply::Ranking(Advice {
                    frame: FRAME,
                    ranking: &REVERSED
                }))
            )
            .unwrap(),
        Outcome::Closed
    ));
}

#[test]
fn cancellation_is_idempotent_and_closed_windows_ignore_clock_regression() {
    let mut window = AdviceWindow::new(choices(), 100, 10).unwrap();
    assert!(matches!(
        window.poll(103, None).unwrap(),
        Outcome::Pending(PendingReason::AwaitingReply)
    ));
    assert!(window.cancel());
    assert!(!window.cancel());
    assert!(window.request().is_none());
    assert!(matches!(
        window
            .poll(
                0,
                Some(Reply::Ranking(Advice {
                    frame: FRAME,
                    ranking: &REVERSED
                }))
            )
            .unwrap(),
        Outcome::Closed
    ));
    assert!(matches!(window.poll(200, None).unwrap(), Outcome::Closed));
}

#[test]
fn regressing_clocks_abort_without_a_decision_and_deadline_addition_is_checked() {
    let mut window = AdviceWindow::new(choices(), 100, 10).unwrap();
    assert!(matches!(
        window.poll(105, None).unwrap(),
        Outcome::Pending(PendingReason::AwaitingReply)
    ));
    assert_eq!(
        window
            .poll(
                104,
                Some(Reply::Ranking(Advice {
                    frame: FRAME,
                    ranking: &REVERSED
                }))
            )
            .err()
            .unwrap(),
        WindowError::ClockRegressed
    );
    assert!(window.request().is_none());
    assert!(!window.cancel());
    assert!(matches!(window.poll(0, None).unwrap(), Outcome::Closed));

    let mut empty = AdviceWindow::new(prepared(Priority::Goal, &[]), 100, 10).unwrap();
    assert_eq!(
        empty.poll(99, None).err().unwrap(),
        WindowError::ClockRegressed
    );
    for frame in [choices(), prepared(Priority::Goal, &[])] {
        assert_eq!(
            AdviceWindow::new(frame, u64::MAX, 1).err().unwrap(),
            WindowError::DeadlineOverflow
        );
    }
    let mut boundary = AdviceWindow::new(choices(), u64::MAX - 1, 1).unwrap();
    assert_eq!(boundary.request().unwrap().deadline_ms, u64::MAX);
    assert_eq!(
        ready(boundary.poll(u64::MAX, None).unwrap()).1,
        Resolution::Deadline
    );
}
