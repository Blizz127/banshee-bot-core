//! Bounded, deterministic arbitration over actions supplied by an adapter.
//!
//! This module is architecture groundwork with no runtime integration. Legal
//! actions and frame identities are caller declarations, not authority proofs.
//! A selected action must still pass native execution revalidation against
//! current permissions, ownership, world state and game rules. Nothing here
//! performs actions, changes economy state, creates capabilities or uses a network.

pub const MAX_ACTIONS: usize = 64;
pub const MAX_PROPOSALS: usize = 256;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ActionId(pub u32);

/// Adapter-supplied freshness identity; equality does not authenticate a frame.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FrameId(pub u64);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ActionClass {
    Movement,
    Combat,
    Social,
    Economy,
    Privileged,
}

/// An adapter's declaration that an action is legal in this frame. The core
/// cannot verify the declaration or grant permission to execute the action.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LegalAction {
    pub id: ActionId,
    pub class: ActionClass,
}

/// Higher layers take precedence regardless of weights in lower layers.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Priority {
    Goal,
    Role,
    OwnerOrder,
    Safety,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Proposal {
    pub action: ActionId,
    pub priority: Priority,
    pub weight: i32,
    pub triggered: bool,
}

/// A proposed ordering of every exposed choice for the same frame.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Advice<'a> {
    pub frame: FrameId,
    pub ranking: &'a [ActionId],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AdviceRejection {
    StaleFrame,
    InvalidLength,
    DuplicateAction,
    IneligibleAction,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AdviceStatus {
    NotRequested,
    NotApplicable,
    Applied,
    Rejected(AdviceRejection),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecisionError {
    TooManyActions,
    TooManyProposals,
    DuplicateAction,
    PrivilegedAction,
    UnknownProposal,
}

/// A proposed action, never an execution or success receipt. Frame freshness
/// and all native execution constraints must be checked again by the adapter.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Decision {
    pub frame: FrameId,
    pub action: Option<ActionId>,
    pub priority: Option<Priority>,
    pub weight: Option<i32>,
    pub advice: AdviceStatus,
    /// Eligible tied IDs in first-triggered proposal order. Advice cannot add
    /// choices, change their score or priority, or choose economy actions.
    pub advice_choices: Vec<ActionId>,
}

fn validate_inputs(legal: &[LegalAction], proposals: &[Proposal]) -> Result<(), DecisionError> {
    if legal.len() > MAX_ACTIONS {
        return Err(DecisionError::TooManyActions);
    }
    if proposals.len() > MAX_PROPOSALS {
        return Err(DecisionError::TooManyProposals);
    }
    for (index, action) in legal.iter().enumerate() {
        if legal[..index].iter().any(|earlier| earlier.id == action.id) {
            return Err(DecisionError::DuplicateAction);
        }
        if action.class == ActionClass::Privileged {
            return Err(DecisionError::PrivilegedAction);
        }
    }
    if proposals
        .iter()
        .any(|proposal| !legal.iter().any(|action| action.id == proposal.action))
    {
        return Err(DecisionError::UnknownProposal);
    }
    Ok(())
}

fn validate_advice(
    frame: FrameId,
    choices: &[ActionId],
    advice: Advice<'_>,
) -> Result<(), AdviceRejection> {
    if advice.frame != frame {
        return Err(AdviceRejection::StaleFrame);
    }
    if advice.ranking.len() != choices.len() {
        return Err(AdviceRejection::InvalidLength);
    }
    for (index, action) in advice.ranking.iter().enumerate() {
        if advice.ranking[..index].contains(action) {
            return Err(AdviceRejection::DuplicateAction);
        }
    }
    if advice
        .ranking
        .iter()
        .any(|action| !choices.contains(action))
    {
        return Err(AdviceRejection::IneligibleAction);
    }
    Ok(())
}

/// Choose the highest triggered priority, then weight, then the earliest
/// proposal. Inactive proposals still undergo input validation.
///
/// Validation checks bounds first, then legal entries in order (duplicate ID
/// before privileged class), then every proposal reference. Repeated proposals
/// for an action are allowed; repeated legal action IDs are rejected.
///
/// Advice can reorder only distinct Role/Goal actions tied on both winning
/// priority and weight. A tie containing any economy action exposes no choices.
/// With fewer than two eligible IDs, supplied advice is NotApplicable. Otherwise
/// advice must be a full permutation for the same frame; rejection precedence
/// is frame, length, duplicate, then membership. Rejection retains the base pick.
pub fn select(
    frame: FrameId,
    legal: &[LegalAction],
    proposals: &[Proposal],
    advice: Option<Advice<'_>>,
) -> Result<Decision, DecisionError> {
    validate_inputs(legal, proposals)?;

    let mut winner: Option<&Proposal> = None;
    for proposal in proposals.iter().filter(|proposal| proposal.triggered) {
        if winner.map_or(true, |current| {
            (proposal.priority, proposal.weight) > (current.priority, current.weight)
        }) {
            winner = Some(proposal);
        }
    }

    let mut decision = Decision {
        frame,
        action: winner.map(|proposal| proposal.action),
        priority: winner.map(|proposal| proposal.priority),
        weight: winner.map(|proposal| proposal.weight),
        advice: AdviceStatus::NotRequested,
        advice_choices: Vec::new(),
    };
    if let Some(winner) = winner {
        if matches!(winner.priority, Priority::Role | Priority::Goal) {
            for proposal in proposals.iter().filter(|proposal| {
                proposal.triggered
                    && proposal.priority == winner.priority
                    && proposal.weight == winner.weight
            }) {
                if legal.iter().any(|action| {
                    action.id == proposal.action && action.class == ActionClass::Economy
                }) {
                    decision.advice_choices.clear();
                    break;
                }
                if !decision.advice_choices.contains(&proposal.action) {
                    decision.advice_choices.push(proposal.action);
                }
            }
            if decision.advice_choices.len() < 2 {
                decision.advice_choices.clear();
            }
        }
    }

    if let Some(advice) = advice {
        decision.advice = if decision.advice_choices.is_empty() {
            AdviceStatus::NotApplicable
        } else {
            match validate_advice(frame, &decision.advice_choices, advice) {
                Ok(()) => {
                    // Validation requires a permutation of at least two IDs.
                    decision.action = Some(advice.ranking[0]);
                    AdviceStatus::Applied
                }
                Err(reason) => AdviceStatus::Rejected(reason),
            }
        };
    }
    Ok(decision)
}
