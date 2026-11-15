use banshee_bot_core::brain::{
    authority::*,
    formation::{Setting, Shape},
    orders::*,
    selection::Candidate,
};

fn fixture() -> (
    RequesterSnapshot,
    OrderSession,
    OrderCandidate<'static>,
    Scene,
) {
    let owner = RequesterSnapshot {
        actor_id: 7,
        kind: ActorKind::Human,
        current_session: true,
        generation: 3,
        party_uid: Some(12),
    };
    let session = OrderSession {
        generation: 3,
        in_zone: true,
        transition_pending: false,
        event_active: false,
        shutting_down: false,
        superseded: false,
        alive: true,
        zone: 100,
    };
    let bot = OrderCandidate {
        identity: Candidate {
            name: "Zoey",
            target: TargetSnapshot {
                actor_id: 8,
                kind: ActorKind::PopulationBot,
                registered_population: true,
                current_session: true,
                generation: 4,
                party_uid: Some(12),
                binding: Some(OwnerBinding {
                    owner: 7,
                    party_uid: 12,
                    revision: 15,
                }),
            },
        },
        session: Some(OrderSession {
            generation: 4,
            ..session
        }),
        control: Control::Open,
    };
    let scene = Scene {
        owner_target: Some(EngageTarget {
            actor_id: 99,
            zone: 100,
            hostile_mob: true,
            alive: true,
            claim: Claim::Unclaimed,
        }),
        main_tank: MainTank::None,
    };
    (owner, session, bot, scene)
}

fn one_plan(outcomes: Vec<TargetOutcome>) -> PreparedOrder {
    assert_eq!(outcomes.len(), 1);
    match outcomes.into_iter().next().unwrap() {
        TargetOutcome::Prepared(plan) => plan,
        other => panic!("unexpected {other:?}"),
    }
}

#[test]
fn execution_rechecks_claim_target_and_binding() {
    let (owner, session, mut bot, mut scene) = fixture();
    let plan = one_plan(prepare(&owner, Some(session), &Order::Attack, &[bot], &scene).unwrap());
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &Order::Attack, &bot, &scene),
        Ok(Directive::Engage { mob: 99 })
    );
    scene.owner_target.as_mut().unwrap().claim = Claim::Other;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &Order::Attack, &bot, &scene),
        Err(Refusal::TargetClaimed)
    );
    scene.owner_target.as_mut().unwrap().claim = Claim::Unclaimed;
    scene.owner_target.as_mut().unwrap().actor_id = 100;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &Order::Attack, &bot, &scene),
        Err(Refusal::StaleOrder)
    );
    bot.identity.target.binding.as_mut().unwrap().revision += 1;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &Order::Attack, &bot, &scene),
        Err(Refusal::Authority(Denial::StaleTicket))
    );
}

#[test]
fn role_metadata_retains_native_dead_and_other_zone_exception_but_not_fence_exception() {
    let (owner, session, mut bot, scene) = fixture();
    bot.session.as_mut().unwrap().alive = false;
    bot.session.as_mut().unwrap().zone = 101;
    let role = Order::Role {
        name: "Zoey".into(),
        role: Role::Healer,
    };
    let plan = one_plan(prepare(&owner, Some(session), &role, &[bot], &scene).unwrap());
    assert_eq!(plan.directive(), Directive::SetRole(Role::Healer));
    bot.control = Control::Closed;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &role, &bot, &scene),
        Err(Refusal::ControlClosed)
    );
    bot.session.as_mut().unwrap().event_active = true;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &role, &bot, &scene),
        Err(Refusal::EventActive)
    );
}

#[test]
fn assist_preserves_tank_target_and_never_invents_one() {
    let (owner, session, bot, mut scene) = fixture();
    assert_eq!(
        prepare(&owner, Some(session), &Order::Assist, &[bot], &scene),
        Err(PlanError::Requester(Refusal::NoMainTank))
    );
    scene.main_tank = MainTank::Member {
        actor_id: 8,
        party_uid: 12,
        engaged: scene.owner_target,
    };
    assert_eq!(
        prepare(&owner, Some(session), &Order::Assist, &[bot], &scene),
        Ok(vec![TargetOutcome::Refused {
            target: 8,
            reason: Refusal::IsMainTank
        }])
    );
    scene.main_tank = MainTank::Member {
        actor_id: 9,
        party_uid: 12,
        engaged: scene.owner_target,
    };
    let plan = one_plan(prepare(&owner, Some(session), &Order::Assist, &[bot], &scene).unwrap());
    assert_eq!(plan.directive(), Directive::Engage { mob: 99 });
    scene.main_tank = MainTank::Member {
        actor_id: 9,
        party_uid: 12,
        engaged: None,
    };
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &Order::Assist, &bot, &scene),
        Err(Refusal::MainTankIdle)
    );
}

#[test]
fn following_other_zone_is_only_a_plan_and_unavailable_owned_bots_remain_visible() {
    let (owner, session, mut bot, scene) = fixture();
    bot.session.as_mut().unwrap().zone = 101;
    let plan = one_plan(prepare(&owner, Some(session), &Order::Follow, &[bot], &scene).unwrap());
    assert_eq!(plan.directive(), Directive::Follow { leader: 7 });
    assert_eq!(
        prepare(&owner, Some(session), &Order::Attack, &[bot], &scene),
        Ok(vec![TargetOutcome::Refused {
            target: 8,
            reason: Refusal::OtherZone
        }])
    );
    bot.identity.target.current_session = false;
    assert_eq!(
        prepare(&owner, Some(session), &Order::Follow, &[bot], &scene),
        Ok(vec![TargetOutcome::Refused {
            target: 8,
            reason: Refusal::Authority(Denial::TargetUnavailable)
        }])
    );
}

#[test]
fn geometry_settings_select_all_owned_bots_and_keep_the_setting_readiness_exception() {
    let (owner, session, mut bot, mut scene) = fixture();
    bot.session.as_mut().unwrap().alive = false;
    bot.session.as_mut().unwrap().zone = 101;
    scene.owner_target = None;
    scene.main_tank = MainTank::Ambiguous;
    let mut second = bot;
    second.identity.name = "Jindrak";
    second.identity.target.actor_id = 9;
    let setting = Setting::Shape(Shape::Line);
    let order = Order::Geometry(setting);
    let outcomes = prepare(&owner, Some(session), &order, &[bot, second], &scene).unwrap();
    assert_eq!(outcomes.len(), 2);
    for (outcome, candidate) in outcomes.into_iter().zip([bot, second]) {
        let TargetOutcome::Prepared(plan) = outcome else {
            panic!("expected geometry plan")
        };
        assert_eq!(plan.directive(), Directive::Geometry(setting));
        assert_eq!(
            revalidate(&plan, &owner, Some(session), &order, &candidate, &scene),
            Ok(Directive::Geometry(setting))
        );
    }
}

#[test]
fn geometry_revalidates_control_session_binding_and_the_exact_setting() {
    let (owner, session, mut bot, scene) = fixture();
    let order = Order::Geometry(Setting::Spacing(30));
    let plan = one_plan(prepare(&owner, Some(session), &order, &[bot], &scene).unwrap());
    assert_eq!(
        revalidate(
            &plan,
            &owner,
            Some(session),
            &Order::Geometry(Setting::Distance(30)),
            &bot,
            &scene
        ),
        Err(Refusal::StaleOrder)
    );
    bot.session.as_mut().unwrap().alive = false;
    bot.control = Control::Closed;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &order, &bot, &scene),
        Err(Refusal::ControlClosed)
    );
    bot.session.as_mut().unwrap().event_active = true;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &order, &bot, &scene),
        Err(Refusal::EventActive)
    );
    bot.session.as_mut().unwrap().transition_pending = true;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &order, &bot, &scene),
        Err(Refusal::TransitionPending)
    );
    bot.identity.target.binding.as_mut().unwrap().revision += 1;
    assert_eq!(
        revalidate(&plan, &owner, Some(session), &order, &bot, &scene),
        Err(Refusal::Authority(Denial::StaleTicket))
    );
}
