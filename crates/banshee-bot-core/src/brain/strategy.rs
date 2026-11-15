//! Bounded strategy evaluation over an adapter-supplied snapshot.
//!
//! Preparation freezes declarations for optional advice; it grants no execution
//! authority. The adapter must supply a stable snapshot and fresh frame identity,
//! then revalidate native legality before execution. Callbacks are trusted adapter
//! code: count/output limits do not impose CPU deadlines or prevent side effects
//! hidden behind interior mutability. This module performs no game or network I/O.

use super::decision::{
    select, ActionId, Advice, Decision, DecisionError, FrameId, LegalAction, Priority, Proposal,
    MAX_PROPOSALS,
};

pub const MAX_STRATEGIES: usize = 32;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StrategyId(pub u32);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum StrategyFailure {
    Unavailable,
    InvalidSnapshot,
    Refused,
}

/// Implementations evaluate triggers against the supplied snapshot and emit
/// candidate IDs. They must not execute an action while preparing a frame.
pub trait Strategy<W> {
    fn evaluate(
        &self,
        snapshot: &W,
        output: &mut ProposalWriter<'_>,
    ) -> Result<(), StrategyFailure>;
}

/// The adapter assigns each strategy its priority; emitted proposals cannot
/// promote themselves to another priority through the writer.
pub struct StrategyBinding<'a, W> {
    pub id: StrategyId,
    pub priority: Priority,
    pub strategy: &'a dyn Strategy<W>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PlanError {
    Input(DecisionError),
    TooManyStrategies,
    DuplicateStrategy(StrategyId),
    Proposal {
        strategy: StrategyId,
        error: DecisionError,
    },
    Strategy {
        strategy: StrategyId,
        reason: StrategyFailure,
    },
}

/// A callback's bounded output channel. The first invalid emission stays an
/// error even if callback code ignores the returned Result or emits again.
pub struct ProposalWriter<'a> {
    legal: &'a [LegalAction],
    proposals: &'a mut Vec<Proposal>,
    priority: Priority,
    error: Option<DecisionError>,
}

impl ProposalWriter<'_> {
    pub fn emit(
        &mut self,
        action: ActionId,
        weight: i32,
        triggered: bool,
    ) -> Result<(), DecisionError> {
        if let Some(error) = self.error {
            return Err(error);
        }
        let error = if self.proposals.len() >= MAX_PROPOSALS {
            Some(DecisionError::TooManyProposals)
        } else if !self.legal.iter().any(|entry| entry.id == action) {
            Some(DecisionError::UnknownProposal)
        } else {
            None
        };
        if let Some(error) = error {
            self.error = Some(error);
            return Err(error);
        }
        self.proposals.push(Proposal {
            action,
            priority: self.priority,
            weight,
            triggered,
        });
        Ok(())
    }
}

/// Immutable declarations from one completed preparation. They may be stale by
/// execution time; this object is not an authority token or a world-state lock.
#[derive(Debug)]
pub struct PreparedFrame {
    legal: Vec<LegalAction>,
    proposals: Vec<Proposal>,
    fallback: Decision,
}

impl PreparedFrame {
    pub fn fallback(&self) -> &Decision {
        &self.fallback
    }

    pub fn proposals(&self) -> &[Proposal] {
        &self.proposals
    }

    pub fn legal_actions(&self) -> &[LegalAction] {
        &self.legal
    }

    /// Apply the existing advice restrictions to these frozen declarations.
    /// This never calls a strategy or reads the world snapshot again.
    pub fn resolve(&self, advice: Option<Advice<'_>>) -> Result<Decision, DecisionError> {
        select(self.fallback.frame, &self.legal, &self.proposals, advice)
    }
}

/// Validate all inputs before evaluating strategies, then visit bindings once
/// in their supplied order. Legal-set errors precede binding errors. A writer
/// error precedes a callback's explicit failure. Any failure discards the whole
/// preparation; no partial fallback or lower-priority action is returned.
pub fn prepare<W>(
    frame: FrameId,
    legal: &[LegalAction],
    snapshot: &W,
    bindings: &[StrategyBinding<'_, W>],
) -> Result<PreparedFrame, PlanError> {
    select(frame, legal, &[], None).map_err(PlanError::Input)?;
    if bindings.len() > MAX_STRATEGIES {
        return Err(PlanError::TooManyStrategies);
    }
    for (index, binding) in bindings.iter().enumerate() {
        if bindings[..index]
            .iter()
            .any(|earlier| earlier.id == binding.id)
        {
            return Err(PlanError::DuplicateStrategy(binding.id));
        }
    }

    let mut proposals = Vec::new();
    for binding in bindings {
        let mut output = ProposalWriter {
            legal,
            proposals: &mut proposals,
            priority: binding.priority,
            error: None,
        };
        let result = binding.strategy.evaluate(snapshot, &mut output);
        if let Some(error) = output.error {
            return Err(PlanError::Proposal {
                strategy: binding.id,
                error,
            });
        }
        result.map_err(|reason| PlanError::Strategy {
            strategy: binding.id,
            reason,
        })?;
    }
    let fallback = select(frame, legal, &proposals, None).map_err(PlanError::Input)?;
    Ok(PreparedFrame {
        legal: legal.to_vec(),
        proposals,
        fallback,
    })
}
