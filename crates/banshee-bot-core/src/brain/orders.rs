//! Existing FFXI order grammar and pure preparation/revalidation contracts.
//! All facts come from the authenticated native game thread. Results are plans,
//! never execution or arrival receipts; the adapter remains the only writer.

use super::authority::{self, Denial, Mutation, MutationTicket, RequesterSnapshot};
use super::command;
use super::selection::{self, Candidate, SelectionError, MAX_CANDIDATES};
pub use crate::roles::Role;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Order {
    Follow,
    Stay,
    Rest,
    Attack,
    Pull,
    Assist,
    Role { name: String, role: Role },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParseError {
    Grammar(command::ParseError),
    MissingArgument,
    InvalidRole,
}

/// Preserve first-slice ownership of its successes AND argument errors.
/// No chat, model output or parsed name is evidence of authority.
pub fn parse(input: &[u8]) -> Result<Option<Order>, ParseError> {
    use command::ParseError as Grammar;
    match command::parse(input) {
        Err(Grammar::UnknownSubcommand) => {}
        Err(error @ (Grammar::TooLong | Grammar::InvalidText)) => {
            return Err(ParseError::Grammar(error))
        }
        _ => return Ok(None),
    }
    let words: Vec<_> = input
        .split(|b| *b == b' ')
        .filter(|s| !s.is_empty())
        .collect();
    let verb = words[1].to_ascii_lowercase();
    let simple = match verb.as_slice() {
        b"follow" => Some(Order::Follow),
        b"stay" => Some(Order::Stay),
        b"rest" => Some(Order::Rest),
        b"attack" => Some(Order::Attack),
        b"pull" => Some(Order::Pull),
        b"assist" => Some(Order::Assist),
        _ => None,
    };
    if let Some(order) = simple {
        return if words.len() == 2 {
            Ok(Some(order))
        } else {
            Err(ParseError::Grammar(Grammar::TooManyArguments))
        };
    }
    if verb != b"role" {
        return Err(ParseError::Grammar(Grammar::UnknownSubcommand));
    }
    if words.len() < 4 {
        return Err(ParseError::MissingArgument);
    }
    if words.len() > 4 {
        return Err(ParseError::Grammar(Grammar::TooManyArguments));
    }
    let name = words[2];
    if !command::valid_name(name) || name.eq_ignore_ascii_case(b"all") {
        return Err(ParseError::Grammar(Grammar::InvalidName));
    }
    let role = match words[3].to_ascii_lowercase().as_slice() {
        b"tank" => Role::Tank,
        b"healer" => Role::Healer,
        b"dps" => Role::Dps,
        b"puller" => Role::Puller,
        _ => return Err(ParseError::InvalidRole),
    };
    Ok(Some(Order::Role {
        name: String::from_utf8_lossy(name).into_owned(),
        role,
    }))
}

/// A coherent native observation, not client-supplied session fields.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OrderSession {
    pub generation: u64,
    pub in_zone: bool,
    pub transition_pending: bool,
    pub event_active: bool,
    pub shutting_down: bool,
    pub superseded: bool,
    pub alive: bool,
    pub zone: u16,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Control {
    Open,
    Closed,
}

#[derive(Clone, Copy, Debug)]
pub struct OrderCandidate<'a> {
    pub identity: Candidate<'a>,
    pub session: Option<OrderSession>,
    pub control: Control,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Claim {
    Unclaimed,
    OwnerParty,
    Other,
}

/// Native hostility and claim decisions; this contract cannot widen game rules.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EngageTarget {
    pub actor_id: u32,
    pub zone: u16,
    pub hostile_mob: bool,
    pub alive: bool,
    pub claim: Claim,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MainTank {
    None,
    Ambiguous,
    Member {
        actor_id: u32,
        party_uid: u64,
        engaged: Option<EngageTarget>,
    },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Scene {
    pub owner_target: Option<EngageTarget>,
    pub main_tank: MainTank,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Directive {
    Follow { leader: u32 },
    Stay,
    Rest,
    Engage { mob: u32 },
    SetRole(Role),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Refusal {
    Authority(Denial),
    Unavailable,
    StaleSession,
    ClosingSession,
    TransitionPending,
    EventActive,
    Dead,
    OtherZone,
    ControlClosed,
    NoTarget,
    TargetNotHostile,
    TargetDead,
    TargetOtherZone,
    TargetClaimed,
    NoMainTank,
    AmbiguousMainTank,
    MainTankNotInParty,
    MainTankIdle,
    IsMainTank,
    StaleOrder,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PlanError {
    Selection(SelectionError),
    Requester(Refusal),
}

/// Ephemeral plan bound to native identity; it contains no mutation authority
/// beyond that established and freshly rechecked by the owning adapter.
#[derive(Debug, PartialEq, Eq)]
pub struct PreparedOrder {
    ticket: MutationTicket,
    directive: Directive,
}

impl PreparedOrder {
    pub fn ticket(&self) -> &MutationTicket {
        &self.ticket
    }
    pub fn directive(&self) -> Directive {
        self.directive
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum TargetOutcome {
    Prepared(PreparedOrder),
    Refused { target: u32, reason: Refusal },
}

fn first_failure(checks: &[(bool, Refusal)]) -> Result<(), Refusal> {
    match checks.iter().find(|(failed, _)| *failed) {
        Some((_, refusal)) => Err(*refusal),
        None => Ok(()),
    }
}

fn session_ready(
    observation: Option<OrderSession>,
    generation: u64,
) -> Result<OrderSession, Refusal> {
    let current = observation.ok_or(Refusal::Unavailable)?;
    first_failure(&[
        (
            current.generation == 0 || current.generation != generation,
            Refusal::StaleSession,
        ),
        (
            current.shutting_down || current.superseded,
            Refusal::ClosingSession,
        ),
        (
            !current.in_zone || current.transition_pending || current.zone == 0,
            Refusal::TransitionPending,
        ),
        (current.event_active, Refusal::EventActive),
    ])?;
    Ok(current)
}

fn target_ready(observation: Option<EngageTarget>, zone: u16) -> Result<u32, Refusal> {
    let mob = observation.ok_or(Refusal::NoTarget)?;
    first_failure(&[
        (
            mob.actor_id == 0 || !mob.hostile_mob,
            Refusal::TargetNotHostile,
        ),
        (!mob.alive, Refusal::TargetDead),
        (mob.zone != zone, Refusal::TargetOtherZone),
        (mob.claim == Claim::Other, Refusal::TargetClaimed),
    ])?;
    Ok(mob.actor_id)
}

struct GroupDecision {
    directive: Directive,
    exclude_tank: Option<u32>,
}

fn group_decision(
    order: &Order,
    requester: &RequesterSnapshot,
    owner: OrderSession,
    scene: &Scene,
) -> Result<GroupDecision, Refusal> {
    let mut exclude_tank = None;
    let directive = match order {
        Order::Follow => Directive::Follow {
            leader: requester.actor_id,
        },
        Order::Stay => Directive::Stay,
        Order::Rest => Directive::Rest,
        Order::Role { role, .. } => Directive::SetRole(*role),
        Order::Attack | Order::Pull => Directive::Engage {
            mob: target_ready(scene.owner_target, owner.zone)?,
        },
        Order::Assist => {
            let (actor_id, party_uid, engaged) = match scene.main_tank {
                MainTank::None => return Err(Refusal::NoMainTank),
                MainTank::Ambiguous => return Err(Refusal::AmbiguousMainTank),
                MainTank::Member {
                    actor_id,
                    party_uid,
                    engaged,
                } => (actor_id, party_uid, engaged),
            };
            if actor_id == 0 || requester.party_uid != Some(party_uid) {
                return Err(Refusal::MainTankNotInParty);
            }
            let mob = engaged.ok_or(Refusal::MainTankIdle)?;
            exclude_tank = Some(actor_id);
            Directive::Engage {
                mob: target_ready(Some(mob), owner.zone)?,
            }
        }
    };
    Ok(GroupDecision {
        directive,
        exclude_tank,
    })
}

fn candidate_ready(
    candidate: &OrderCandidate<'_>,
    owner: OrderSession,
    decision: &GroupDecision,
) -> Result<(), Refusal> {
    let current = session_ready(candidate.session, candidate.identity.target.generation)?;
    if candidate.control == Control::Closed {
        return Err(Refusal::ControlClosed);
    }
    if matches!(decision.directive, Directive::SetRole(_)) {
        return Ok(());
    }
    first_failure(&[
        (!current.alive, Refusal::Dead),
        (
            matches!(decision.directive, Directive::Engage { .. }) && current.zone != owner.zone,
            Refusal::OtherZone,
        ),
        (
            decision.exclude_tank == Some(candidate.identity.target.actor_id),
            Refusal::IsMainTank,
        ),
    ])
}

/// Preserve batch failure ordering and one outcome per selected owned bot.
/// Planning cannot enqueue, change roles, claim a target or move a player.
pub fn prepare(
    requester: &RequesterSnapshot,
    owner_session: Option<OrderSession>,
    order: &Order,
    candidates: &[OrderCandidate<'_>],
    scene: &Scene,
) -> Result<Vec<TargetOutcome>, PlanError> {
    authority::validate_requester(requester)
        .map_err(|e| PlanError::Selection(SelectionError::Unauthorized(e)))?;
    if candidates.len() > MAX_CANDIDATES {
        return Err(PlanError::Selection(SelectionError::TooManyCandidates));
    }
    let identities: Vec<_> = candidates.iter().map(|c| c.identity).collect();
    let target = match order {
        Order::Role { name, .. } => command::Target::Name(name.clone()),
        _ => command::Target::All,
    };
    let indices =
        selection::select_owned(requester, &target, &identities).map_err(PlanError::Selection)?;
    let owner = session_ready(owner_session, requester.generation).map_err(PlanError::Requester)?;
    let decision = group_decision(order, requester, owner, scene).map_err(PlanError::Requester)?;
    Ok(indices
        .into_iter()
        .map(|index| {
            let candidate = &candidates[index];
            let ready = || {
                let ticket =
                    authority::issue_ticket(Mutation::Order, requester, &candidate.identity.target)
                        .map_err(Refusal::Authority)?;
                candidate_ready(candidate, owner, &decision)?;
                Ok(PreparedOrder {
                    ticket,
                    directive: decision.directive,
                })
            };
            match ready() {
                Ok(prepared) => TargetOutcome::Prepared(prepared),
                Err(reason) => TargetOutcome::Refused {
                    target: candidate.identity.target.actor_id,
                    reason,
                },
            }
        })
        .collect())
}

/// Call in the native execution critical section with freshly read facts, the
/// retained original order and an uncancelled clock token. Success mutates nothing.
pub fn revalidate(
    prepared: &PreparedOrder,
    requester: &RequesterSnapshot,
    owner_session: Option<OrderSession>,
    order: &Order,
    candidate: &OrderCandidate<'_>,
    scene: &Scene,
) -> Result<Directive, Refusal> {
    authority::validate_ticket(&prepared.ticket, requester, &candidate.identity.target)
        .map_err(Refusal::Authority)?;
    let owner = session_ready(owner_session, requester.generation)?;
    let decision = group_decision(order, requester, owner, scene)?;
    candidate_ready(candidate, owner, &decision)?;
    if decision.directive == prepared.directive {
        Ok(decision.directive)
    } else {
        Err(Refusal::StaleOrder)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn compatibility_precedence_and_scope() {
        for unrelated in [
            b"/fbar".as_slice(),
            b"/fb summon Bad2",
            b"/fb list all",
            b"/fb help",
        ] {
            assert_eq!(parse(unrelated), Ok(None));
        }
        assert_eq!(
            parse(b"\t/fb follow"),
            Err(ParseError::Grammar(command::ParseError::InvalidText))
        );
        assert_eq!(
            parse(b"/fb follow all"),
            Err(ParseError::Grammar(command::ParseError::TooManyArguments))
        );
        assert_eq!(
            parse(b"/fb role All tank"),
            Err(ParseError::Grammar(command::ParseError::InvalidName))
        );
        assert_eq!(
            parse(b"/fb role Zoey support"),
            Err(ParseError::InvalidRole)
        );
        assert_eq!(
            parse(b" /FB  ROLE Zoey Healer "),
            Ok(Some(Order::Role {
                name: "Zoey".into(),
                role: Role::Healer
            }))
        );
        let mut padded = b"/fb pull".to_vec();
        padded.resize(200, b' ');
        assert_eq!(parse(&padded), Ok(Some(Order::Pull)));
        padded.push(0);
        assert_eq!(
            parse(&padded),
            Err(ParseError::Grammar(command::ParseError::TooLong))
        );
    }
}
