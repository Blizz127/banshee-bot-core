use banshee_bot_core::brain::decision::{
    select, ActionClass, ActionId, Advice, AdviceRejection, AdviceStatus, DecisionError, FrameId,
    LegalAction, Priority, Proposal, MAX_ACTIONS, MAX_PROPOSALS,
};

const FRAME: FrameId = FrameId(19);

fn legal(id: u32, class: ActionClass) -> LegalAction {
    LegalAction {
        id: ActionId(id),
        class,
    }
}

fn proposed(id: u32, priority: Priority, weight: i32, triggered: bool) -> Proposal {
    Proposal {
        action: ActionId(id),
        priority,
        weight,
        triggered,
    }
}

fn alternatives() -> ([LegalAction; 2], [Proposal; 2]) {
    (
        [
            legal(10, ActionClass::Movement),
            legal(20, ActionClass::Combat),
        ],
        [
            proposed(10, Priority::Role, 3, true),
            proposed(20, Priority::Role, 3, true),
        ],
    )
}

#[test]
fn safety_and_owner_orders_outrank_lower_layers_regardless_of_weight() {
    let legal = (1..=4)
        .map(|id| legal(id, ActionClass::Movement))
        .collect::<Vec<_>>();
    let mut proposals = [
        proposed(1, Priority::Goal, i32::MAX, true),
        proposed(2, Priority::Role, i32::MIN, true),
        proposed(3, Priority::OwnerOrder, i32::MIN, true),
        proposed(4, Priority::Safety, i32::MIN, true),
    ];
    for index in (0..4).rev() {
        let result = select(FRAME, &legal, &proposals, None).unwrap();
        assert_eq!(result.action, Some(proposals[index].action));
        assert_eq!(result.priority, Some(proposals[index].priority));
        assert_eq!(result.weight, Some(proposals[index].weight));
        proposals[index].triggered = false;
    }
}

#[test]
fn base_choice_uses_weight_then_first_triggered_tie() {
    let legal = (1..=4)
        .map(|id| legal(id, ActionClass::Movement))
        .collect::<Vec<_>>();
    let proposals = [
        proposed(1, Priority::Role, 7, true),
        proposed(4, Priority::Role, i32::MAX, false),
        proposed(2, Priority::Role, 8, true),
        proposed(3, Priority::Role, 8, true),
    ];
    let result = select(FRAME, &legal, &proposals, None).unwrap();
    assert_eq!(result.frame, FRAME);
    assert_eq!(result.action, Some(ActionId(2)));
    assert_eq!(result.priority, Some(Priority::Role));
    assert_eq!(result.weight, Some(8));
    assert_eq!(result.advice, AdviceStatus::NotRequested);
    assert_eq!(result.advice_choices, vec![ActionId(2), ActionId(3)]);
}

#[test]
fn valid_advice_reorders_only_the_unique_tied_role_or_goal_choices() {
    let legal = [
        legal(10, ActionClass::Movement),
        legal(20, ActionClass::Social),
    ];
    let ranking = [ActionId(20), ActionId(10)];
    for priority in [Priority::Role, Priority::Goal] {
        let proposals = [
            proposed(20, priority, 99, false),
            proposed(10, priority, i32::MIN, true),
            proposed(10, priority, i32::MIN, true),
            proposed(20, priority, i32::MIN, true),
        ];
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: FRAME,
                ranking: &ranking,
            }),
        )
        .unwrap();
        assert_eq!(result.action, Some(ActionId(20)));
        assert_eq!(result.priority, Some(priority));
        assert_eq!(result.weight, Some(i32::MIN));
        assert_eq!(result.advice, AdviceStatus::Applied);
        assert_eq!(result.advice_choices, vec![ActionId(10), ActionId(20)]);
    }
}

#[test]
fn advice_cannot_promote_inactive_lower_weight_lower_layer_or_unproposed_actions() {
    let legal = (1..=6)
        .map(|id| legal(id, ActionClass::Movement))
        .collect::<Vec<_>>();
    let proposals = [
        proposed(1, Priority::Role, 10, true),
        proposed(2, Priority::Role, 10, true),
        proposed(3, Priority::Role, 9, true),
        proposed(4, Priority::Goal, i32::MAX, true),
        proposed(5, Priority::Safety, i32::MAX, false),
    ];
    for excluded in [3, 4, 5, 6, 999] {
        let ranking = [ActionId(excluded), ActionId(2)];
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: FRAME,
                ranking: &ranking,
            }),
        )
        .unwrap();
        assert_eq!(
            result.action,
            Some(ActionId(1)),
            "excluded action {excluded}"
        );
        assert_eq!(
            result.advice,
            AdviceStatus::Rejected(AdviceRejection::IneligibleAction)
        );
        assert_eq!(result.advice_choices, vec![ActionId(1), ActionId(2)]);
    }
}

#[test]
fn malformed_or_stale_advice_has_ordered_refusals_and_deterministic_fallback() {
    let (legal, proposals) = alternatives();
    let cases: &[(FrameId, &[ActionId], AdviceRejection)] = &[
        (
            FrameId(18),
            &[ActionId(999), ActionId(999), ActionId(999)],
            AdviceRejection::StaleFrame,
        ),
        (FRAME, &[], AdviceRejection::InvalidLength),
        (FRAME, &[ActionId(20)], AdviceRejection::InvalidLength),
        (
            FRAME,
            &[ActionId(999), ActionId(999), ActionId(999)],
            AdviceRejection::InvalidLength,
        ),
        (
            FRAME,
            &[ActionId(999), ActionId(999)],
            AdviceRejection::DuplicateAction,
        ),
        (
            FRAME,
            &[ActionId(20), ActionId(20)],
            AdviceRejection::DuplicateAction,
        ),
        (
            FRAME,
            &[ActionId(20), ActionId(999)],
            AdviceRejection::IneligibleAction,
        ),
    ];
    for (frame, ranking, rejection) in cases {
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: *frame,
                ranking,
            }),
        )
        .unwrap();
        assert_eq!(result.action, Some(ActionId(10)));
        assert_eq!(result.priority, Some(Priority::Role));
        assert_eq!(result.weight, Some(3));
        assert_eq!(result.advice, AdviceStatus::Rejected(*rejection));
        assert_eq!(result.advice_choices, vec![ActionId(10), ActionId(20)]);
    }
}

#[test]
fn safety_owner_and_single_choice_frames_do_not_consume_advice() {
    let (legal, _) = alternatives();
    let malformed = [ActionId(999), ActionId(999), ActionId(999)];
    for priority in [Priority::Safety, Priority::OwnerOrder] {
        let proposals = [
            proposed(10, priority, 3, true),
            proposed(20, priority, 3, true),
        ];
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: FrameId(0),
                ranking: &malformed,
            }),
        )
        .unwrap();
        assert_eq!(result.action, Some(ActionId(10)));
        assert_eq!(result.advice, AdviceStatus::NotApplicable);
        assert!(result.advice_choices.is_empty());
        assert_eq!(
            select(FRAME, &legal, &proposals, None).unwrap().advice,
            AdviceStatus::NotRequested
        );
    }
    let proposals = [
        proposed(20, Priority::Goal, 3, true),
        proposed(20, Priority::Goal, 3, true),
    ];
    let result = select(
        FRAME,
        &legal,
        &proposals,
        Some(Advice {
            frame: FrameId(0),
            ranking: &malformed,
        }),
    )
    .unwrap();
    assert_eq!(result.action, Some(ActionId(20)));
    assert_eq!(result.advice, AdviceStatus::NotApplicable);
    assert!(result.advice_choices.is_empty());
}

#[test]
fn any_tied_economy_action_disables_advice_but_unrelated_economy_does_not() {
    let legal = [
        legal(1, ActionClass::Movement),
        legal(2, ActionClass::Social),
        legal(3, ActionClass::Economy),
    ];
    for priority in [Priority::Goal, Priority::Role] {
        let mut proposals = [
            proposed(1, priority, 4, true),
            proposed(2, priority, 4, true),
            proposed(3, priority, 4, true),
        ];
        let blocked_ranking = [ActionId(3), ActionId(2), ActionId(1)];
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: FRAME,
                ranking: &blocked_ranking,
            }),
        )
        .unwrap();
        assert_eq!(result.action, Some(ActionId(1)));
        assert_eq!(result.advice, AdviceStatus::NotApplicable);
        assert!(result.advice_choices.is_empty());

        proposals[2].weight = 3;
        let allowed_ranking = [ActionId(2), ActionId(1)];
        let result = select(
            FRAME,
            &legal,
            &proposals,
            Some(Advice {
                frame: FRAME,
                ranking: &allowed_ranking,
            }),
        )
        .unwrap();
        assert_eq!(result.action, Some(ActionId(2)));
        assert_eq!(result.advice, AdviceStatus::Applied);
        assert_eq!(result.advice_choices, vec![ActionId(1), ActionId(2)]);
    }
}

#[test]
fn privileged_actions_are_rejected_even_when_unproposed() {
    let legal = [
        legal(1, ActionClass::Movement),
        legal(2, ActionClass::Privileged),
    ];
    let proposals = [proposed(1, Priority::Safety, 0, true)];
    assert_eq!(
        select(FRAME, &legal, &proposals, None).unwrap_err(),
        DecisionError::PrivilegedAction
    );
    assert_eq!(
        select(FRAME, &legal, &[], None).unwrap_err(),
        DecisionError::PrivilegedAction
    );
}

#[test]
fn legal_identity_and_every_proposal_are_validated_before_selection() {
    let duplicate = [
        legal(1, ActionClass::Movement),
        legal(1, ActionClass::Privileged),
    ];
    assert_eq!(
        select(FRAME, &duplicate, &[], None).unwrap_err(),
        DecisionError::DuplicateAction
    );
    let legal = [legal(1, ActionClass::Movement)];
    for triggered in [false, true] {
        let proposals = [
            proposed(1, Priority::Safety, i32::MAX, true),
            proposed(2, Priority::Goal, i32::MIN, triggered),
        ];
        assert_eq!(
            select(FRAME, &legal, &proposals, None).unwrap_err(),
            DecisionError::UnknownProposal
        );
    }
}

#[test]
fn empty_and_inactive_frames_produce_no_intent() {
    let legal = [legal(1, ActionClass::Movement)];
    let inactive = [proposed(1, Priority::Safety, i32::MAX, false)];
    for (legal, proposals) in [(&[][..], &[][..]), (&legal[..], &inactive[..])] {
        for advice in [
            None,
            Some(Advice {
                frame: FrameId(0),
                ranking: &[ActionId(999)],
            }),
        ] {
            let requested = advice.is_some();
            let result = select(FRAME, legal, proposals, advice).unwrap();
            assert_eq!(result.action, None);
            assert_eq!(result.priority, None);
            assert_eq!(result.weight, None);
            assert!(result.advice_choices.is_empty());
            assert_eq!(
                result.advice,
                if requested {
                    AdviceStatus::NotApplicable
                } else {
                    AdviceStatus::NotRequested
                }
            );
        }
    }
}

#[test]
fn exact_input_bounds_work_and_oversized_inputs_refuse_before_content() {
    assert_eq!(MAX_ACTIONS, 64);
    assert_eq!(MAX_PROPOSALS, 256);
    let mut legal = (0..MAX_ACTIONS as u32)
        .map(|id| legal(id, ActionClass::Movement))
        .collect::<Vec<_>>();
    let mut proposals = (0..MAX_PROPOSALS)
        .map(|index| proposed((index % MAX_ACTIONS) as u32, Priority::Goal, 0, true))
        .collect::<Vec<_>>();
    let result = select(FRAME, &legal, &proposals, None).unwrap();
    assert_eq!(result.action, Some(ActionId(0)));
    assert_eq!(result.advice_choices.len(), MAX_ACTIONS);

    proposals.push(proposed(999, Priority::Goal, 0, false));
    assert_eq!(
        select(FRAME, &legal, &proposals, None).unwrap_err(),
        DecisionError::TooManyProposals
    );
    legal.push(LegalAction {
        id: ActionId(0),
        class: ActionClass::Privileged,
    });
    assert_eq!(
        select(FRAME, &legal, &proposals, None).unwrap_err(),
        DecisionError::TooManyActions
    );
}
