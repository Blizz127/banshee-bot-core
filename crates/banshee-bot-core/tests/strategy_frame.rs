use banshee_bot_core::brain::decision::{
    ActionClass, ActionId, Advice, AdviceRejection, AdviceStatus, DecisionError, FrameId,
    LegalAction, Priority, MAX_ACTIONS, MAX_PROPOSALS,
};
use banshee_bot_core::brain::strategy::{
    prepare, PlanError, ProposalWriter, Strategy, StrategyBinding, StrategyFailure, StrategyId,
    MAX_STRATEGIES,
};
use std::cell::{Cell, RefCell};

const FRAME: FrameId = FrameId(44);

fn action(id: u32, class: ActionClass) -> LegalAction {
    LegalAction {
        id: ActionId(id),
        class,
    }
}

struct Script {
    emissions: RefCell<Vec<(u32, i32, bool)>>,
    failure: Option<StrategyFailure>,
    calls: Cell<usize>,
}

impl Script {
    fn new(emissions: Vec<(u32, i32, bool)>, failure: Option<StrategyFailure>) -> Self {
        Self {
            emissions: RefCell::new(emissions),
            failure,
            calls: Cell::new(0),
        }
    }
}

impl Strategy<()> for Script {
    fn evaluate(&self, _: &(), output: &mut ProposalWriter<'_>) -> Result<(), StrategyFailure> {
        self.calls.set(self.calls.get() + 1);
        for &(id, weight, triggered) in self.emissions.borrow().iter() {
            // Deliberately uncooperative callbacks cannot suppress writer errors.
            let _ = output.emit(ActionId(id), weight, triggered);
        }
        self.failure.map_or(Ok(()), Err)
    }
}

fn binding(id: u32, priority: Priority, strategy: &Script) -> StrategyBinding<'_, ()> {
    StrategyBinding {
        id: StrategyId(id),
        priority,
        strategy,
    }
}

#[test]
fn callbacks_share_one_snapshot_and_binding_order_with_fixed_priorities() {
    struct Snapshot {
        marker: u64,
    }
    struct Observer<'a> {
        id: u32,
        calls: &'a RefCell<Vec<(u32, usize, u64)>>,
    }
    impl Strategy<Snapshot> for Observer<'_> {
        fn evaluate(
            &self,
            snapshot: &Snapshot,
            output: &mut ProposalWriter<'_>,
        ) -> Result<(), StrategyFailure> {
            self.calls.borrow_mut().push((
                self.id,
                snapshot as *const Snapshot as usize,
                snapshot.marker,
            ));
            output
                .emit(
                    ActionId(self.id),
                    if self.id == 2 { i32::MIN } else { i32::MAX },
                    true,
                )
                .map_err(|_| StrategyFailure::Refused)
        }
    }
    let snapshot = Snapshot { marker: 813 };
    let calls = RefCell::new(Vec::new());
    let observers = [
        Observer {
            id: 1,
            calls: &calls,
        },
        Observer {
            id: 2,
            calls: &calls,
        },
        Observer {
            id: 3,
            calls: &calls,
        },
    ];
    let legal = [
        action(1, ActionClass::Movement),
        action(2, ActionClass::Combat),
        action(3, ActionClass::Social),
    ];
    let bindings = [
        StrategyBinding {
            id: StrategyId(70),
            priority: Priority::Goal,
            strategy: &observers[0] as &dyn Strategy<Snapshot>,
        },
        StrategyBinding {
            id: StrategyId(80),
            priority: Priority::Safety,
            strategy: &observers[1] as &dyn Strategy<Snapshot>,
        },
        StrategyBinding {
            id: StrategyId(90),
            priority: Priority::OwnerOrder,
            strategy: &observers[2] as &dyn Strategy<Snapshot>,
        },
    ];
    let frame = prepare(FRAME, &legal, &snapshot, &bindings).unwrap();
    let address = &snapshot as *const Snapshot as usize;
    assert_eq!(
        *calls.borrow(),
        vec![(1, address, 813), (2, address, 813), (3, address, 813)]
    );
    assert_eq!(
        frame
            .proposals()
            .iter()
            .map(|proposal| proposal.priority)
            .collect::<Vec<_>>(),
        vec![Priority::Goal, Priority::Safety, Priority::OwnerOrder]
    );
    assert_eq!(frame.fallback().action, Some(ActionId(2)));
    assert_eq!(frame.fallback().priority, Some(Priority::Safety));
    assert_eq!(frame.fallback().weight, Some(i32::MIN));
}

#[test]
fn prepared_frames_freeze_inputs_and_resolve_advice_without_reevaluation() {
    let mut legal = vec![
        action(1, ActionClass::Movement),
        action(2, ActionClass::Social),
    ];
    let script = Script::new(vec![(1, 5, true), (2, 5, true)], None);
    let frame = prepare(FRAME, &legal, &(), &[binding(1, Priority::Role, &script)]).unwrap();
    let frozen_legal = frame.legal_actions().to_vec();
    let frozen_proposals = frame.proposals().to_vec();
    let fallback = frame.fallback().clone();
    legal.clear();
    script.emissions.borrow_mut().clear();

    let ranking = [ActionId(2), ActionId(1)];
    let advised = frame
        .resolve(Some(Advice {
            frame: FRAME,
            ranking: &ranking,
        }))
        .unwrap();
    assert_eq!(advised.action, Some(ActionId(2)));
    assert_eq!(advised.advice, AdviceStatus::Applied);
    let stale = frame
        .resolve(Some(Advice {
            frame: FrameId(43),
            ranking: &ranking,
        }))
        .unwrap();
    assert_eq!(stale.action, fallback.action);
    assert_eq!(
        stale.advice,
        AdviceStatus::Rejected(AdviceRejection::StaleFrame)
    );
    assert_eq!(frame.resolve(None).unwrap(), fallback);
    assert_eq!(frame.fallback(), &fallback);
    assert_eq!(frame.legal_actions(), frozen_legal);
    assert_eq!(frame.proposals(), frozen_proposals);
    assert_eq!(script.calls.get(), 1);
}

#[test]
fn unknown_inactive_emissions_are_sticky_and_outrank_callback_failure() {
    let legal = [action(1, ActionClass::Movement)];
    let mut emissions = vec![(999, 0, false)];
    emissions.extend(vec![(1, 0, true); MAX_PROPOSALS + 1]);
    let broken = Script::new(emissions, Some(StrategyFailure::Refused));
    let later = Script::new(vec![(1, 0, true)], None);
    let result = prepare(
        FRAME,
        &legal,
        &(),
        &[
            binding(7, Priority::Goal, &broken),
            binding(8, Priority::Safety, &later),
        ],
    );
    assert_eq!(
        result.err().unwrap(),
        PlanError::Proposal {
            strategy: StrategyId(7),
            error: DecisionError::UnknownProposal
        }
    );
    assert_eq!(broken.calls.get(), 1);
    assert_eq!(later.calls.get(), 0);
}

#[test]
fn explicit_strategy_failures_abort_the_frame_before_later_callbacks() {
    let legal = [action(1, ActionClass::Movement)];
    for reason in [
        StrategyFailure::Unavailable,
        StrategyFailure::InvalidSnapshot,
        StrategyFailure::Refused,
    ] {
        let first = Script::new(vec![(1, 0, true)], None);
        let failed = Script::new(vec![(1, 1, true)], Some(reason));
        let later = Script::new(vec![(1, 2, true)], None);
        let result = prepare(
            FRAME,
            &legal,
            &(),
            &[
                binding(1, Priority::Goal, &first),
                binding(2, Priority::Role, &failed),
                binding(3, Priority::Safety, &later),
            ],
        );
        assert_eq!(
            result.err().unwrap(),
            PlanError::Strategy {
                strategy: StrategyId(2),
                reason
            }
        );
        assert_eq!(
            (first.calls.get(), failed.calls.get(), later.calls.get()),
            (1, 1, 0)
        );
    }
}

#[test]
fn legal_validation_and_all_binding_ids_are_checked_before_callbacks() {
    let script = Script::new(vec![(1, 0, true)], None);
    let duplicate_bindings = [
        binding(1, Priority::Goal, &script),
        binding(2, Priority::Role, &script),
        binding(1, Priority::Safety, &script),
    ];
    let invalid_inputs = [
        (
            vec![
                action(1, ActionClass::Movement),
                action(1, ActionClass::Combat),
            ],
            DecisionError::DuplicateAction,
        ),
        (
            vec![action(1, ActionClass::Privileged)],
            DecisionError::PrivilegedAction,
        ),
        (
            (0..=MAX_ACTIONS as u32)
                .map(|id| action(id, ActionClass::Movement))
                .collect(),
            DecisionError::TooManyActions,
        ),
    ];
    for (legal, error) in invalid_inputs {
        assert_eq!(
            prepare(FRAME, &legal, &(), &duplicate_bindings)
                .err()
                .unwrap(),
            PlanError::Input(error)
        );
        assert_eq!(script.calls.get(), 0);
    }
    let legal = [action(1, ActionClass::Movement)];
    assert_eq!(
        prepare(FRAME, &legal, &(), &duplicate_bindings)
            .err()
            .unwrap(),
        PlanError::DuplicateStrategy(StrategyId(1))
    );
    assert_eq!(script.calls.get(), 0);
}

#[test]
fn thirty_two_strategies_run_but_thirty_three_are_rejected_before_any_callback() {
    assert_eq!(MAX_STRATEGIES, 32);
    let legal = [action(1, ActionClass::Movement)];
    let script = Script::new(vec![(1, 0, true)], None);
    let mut bindings = (0..MAX_STRATEGIES)
        .map(|id| binding(id as u32, Priority::Goal, &script))
        .collect::<Vec<_>>();
    let frame = prepare(FRAME, &legal, &(), &bindings).unwrap();
    assert_eq!(frame.proposals().len(), MAX_STRATEGIES);
    assert_eq!(script.calls.get(), MAX_STRATEGIES);
    bindings.push(binding(MAX_STRATEGIES as u32, Priority::Safety, &script));
    assert_eq!(
        prepare(FRAME, &legal, &(), &bindings).err().unwrap(),
        PlanError::TooManyStrategies
    );
    assert_eq!(script.calls.get(), MAX_STRATEGIES);
}

#[test]
fn proposal_limit_is_global_and_stays_first_when_later_emissions_are_unknown() {
    assert_eq!(MAX_PROPOSALS, 256);
    let legal = [action(1, ActionClass::Movement)];
    let first = Script::new(vec![(1, 0, true); 128], None);
    let second = Script::new(vec![(1, 0, false); 128], None);
    let overflow = Script::new(
        vec![(1, 0, false), (999, 0, true)],
        Some(StrategyFailure::Unavailable),
    );
    let later = Script::new(vec![(1, 0, true)], None);
    let frame = prepare(
        FRAME,
        &legal,
        &(),
        &[
            binding(1, Priority::Goal, &first),
            binding(2, Priority::Role, &second),
        ],
    )
    .unwrap();
    assert_eq!(frame.proposals().len(), MAX_PROPOSALS);
    assert_eq!(frame.fallback().priority, Some(Priority::Goal));
    let result = prepare(
        FRAME,
        &legal,
        &(),
        &[
            binding(1, Priority::Goal, &first),
            binding(2, Priority::Role, &second),
            binding(3, Priority::Safety, &overflow),
            binding(4, Priority::Safety, &later),
        ],
    );
    assert_eq!(
        result.err().unwrap(),
        PlanError::Proposal {
            strategy: StrategyId(3),
            error: DecisionError::TooManyProposals
        }
    );
    assert_eq!(
        (
            first.calls.get(),
            second.calls.get(),
            overflow.calls.get(),
            later.calls.get()
        ),
        (2, 2, 1, 0)
    );
}

#[test]
fn empty_frames_and_economy_ties_preserve_decision_advice_restrictions() {
    let empty = prepare(FRAME, &[], &(), &[]).unwrap();
    assert!(empty.legal_actions().is_empty());
    assert!(empty.proposals().is_empty());
    assert_eq!(empty.fallback().frame, FRAME);
    assert_eq!(empty.fallback().action, None);
    assert_eq!(empty.resolve(None).unwrap(), *empty.fallback());
    assert_eq!(
        empty
            .resolve(Some(Advice {
                frame: FrameId(0),
                ranking: &[]
            }))
            .unwrap()
            .advice,
        AdviceStatus::NotApplicable
    );

    let legal = [
        action(1, ActionClass::Social),
        action(2, ActionClass::Economy),
    ];
    let script = Script::new(vec![(1, 0, true), (2, 0, true)], None);
    let economy = prepare(FRAME, &legal, &(), &[binding(1, Priority::Goal, &script)]).unwrap();
    assert!(economy.fallback().advice_choices.is_empty());
    let ranking = [ActionId(2), ActionId(1)];
    let decision = economy
        .resolve(Some(Advice {
            frame: FRAME,
            ranking: &ranking,
        }))
        .unwrap();
    assert_eq!(decision.action, Some(ActionId(1)));
    assert_eq!(decision.advice, AdviceStatus::NotApplicable);
    assert_eq!(script.calls.get(), 1);
}
