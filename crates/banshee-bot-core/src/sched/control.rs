//! Cancellation epochs, not elapsed time. Retain one clock for each registered
//! bot's whole map lifetime, including logout. Never reset it to revive work.
//! A token is only a cancellation identity: it grants no ownership or authority.

use std::num::NonZeroU64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Token {
    pub binding_revision: u64,
    pub epoch: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Operation {
    Gear,
    Summon,
    Dismiss,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Phase {
    #[default]
    Legacy,
    Active,
    Fenced(Operation),
    Detached,
    Invited,
    Exhausted,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Refusal {
    Required,
    Stale,
    Closed,
    WrongOperation,
    Exhausted,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Snapshot {
    pub phase: Phase,
    pub token: Option<Token>,
}

#[derive(Debug, Default)]
pub struct Clock {
    phase: Phase,
    identity: TokenState,
}

#[derive(Debug, Default)]
struct TokenState {
    revision: u64,
    epoch: u64,
}

impl Clock {
    /// New explicitly enrolled bot, without a binding or permission to act.
    pub fn initially_detached() -> Self {
        Self {
            phase: Phase::Detached,
            identity: TokenState {
                revision: 0,
                epoch: 1,
            },
        }
    }

    pub fn snapshot(&self) -> Snapshot {
        let token = match self.phase {
            Phase::Legacy => None,
            _ => Some(Token {
                binding_revision: self.identity.revision,
                epoch: self.identity.epoch,
            }),
        };
        Snapshot {
            phase: self.phase,
            token,
        }
    }

    fn change(&mut self, next: Phase, revision: u64) -> Result<Token, Refusal> {
        if self.phase == Phase::Exhausted {
            return Err(Refusal::Exhausted);
        }
        match self.identity.epoch.checked_add(1) {
            None => {
                self.phase = Phase::Exhausted;
                Err(Refusal::Exhausted)
            }
            Some(epoch) => {
                self.identity = TokenState { revision, epoch };
                self.phase = next;
                Ok(Token {
                    binding_revision: revision,
                    epoch,
                })
            }
        }
    }

    fn accepts_order(&self, binding: NonZeroU64) -> Result<(), Refusal> {
        match self.phase {
            Phase::Legacy => Ok(()),
            Phase::Active => {
                if binding.get() == self.identity.revision {
                    Ok(())
                } else {
                    Err(Refusal::Stale)
                }
            }
            Phase::Exhausted => Err(Refusal::Exhausted),
            _ => Err(Refusal::Closed),
        }
    }

    /// Pure preflight for an atomic multi-bot role change. The adapter must
    /// preflight the entire group before changing any clock, on one game thread.
    pub fn can_order(&self, binding: NonZeroU64) -> Result<(), Refusal> {
        self.accepts_order(binding)?;
        if self.identity.epoch == u64::MAX {
            Err(Refusal::Exhausted)
        } else {
            Ok(())
        }
    }

    /// Call only after native authority/readiness checks. Cancel previous queued
    /// work before mutating anything in the game.
    pub fn begin(&mut self, operation: Operation, binding: NonZeroU64) -> Result<Token, Refusal> {
        self.accepts_order(binding)?;
        self.change(Phase::Fenced(operation), binding.get())
    }

    /// Replace controlled work after native validation and queue cancellation.
    pub fn order(&mut self, binding: NonZeroU64) -> Result<Token, Refusal> {
        self.accepts_order(binding)?;
        self.change(Phase::Active, binding.get())
    }

    fn check_identity(&self, token: Token) -> Result<(), Refusal> {
        if self.phase == Phase::Exhausted {
            Err(Refusal::Exhausted)
        } else if self.snapshot().token == Some(token) {
            Ok(())
        } else {
            Err(Refusal::Stale)
        }
    }

    fn check_operation(&self, token: Token, operation: Operation) -> Result<(), Refusal> {
        self.check_identity(token)?;
        if self.phase == Phase::Fenced(operation) {
            Ok(())
        } else {
            Err(Refusal::WrongOperation)
        }
    }

    fn finish_bound(&mut self, token: Token, operation: Operation) -> Result<Token, Refusal> {
        self.check_operation(token, operation)?;
        if self.identity.revision == 0 {
            return Err(Refusal::Closed);
        }
        self.change(Phase::Active, self.identity.revision)
    }

    /// Actual arrival and execution readiness must have been observed natively.
    pub fn summon_arrived(&mut self, attempt: Token) -> Result<Token, Refusal> {
        self.finish_bound(attempt, Operation::Summon)
    }

    /// Same readiness proof as arrival; a queued transfer is insufficient.
    pub fn summon_reconciled(&mut self, attempt: Token) -> Result<Token, Refusal> {
        self.finish_bound(attempt, Operation::Summon)
    }

    /// Native commit plus refresh, or proven rollback. Unknown outcomes remain fenced.
    pub fn gear_finished(&mut self, attempt: Token) -> Result<Token, Refusal> {
        self.finish_bound(attempt, Operation::Gear)
    }

    /// Reconciliation uses the CURRENT binding/token. It never resumes old work.
    pub fn summon_abandoned(&mut self, current: Token) -> Result<Token, Refusal> {
        self.check_operation(current, Operation::Summon)?;
        let next = if self.identity.revision == 0 {
            Phase::Detached
        } else {
            Phase::Active
        };
        self.change(next, self.identity.revision)
    }

    /// Native leave and party event processing must both have succeeded.
    pub fn dismiss_completed(&mut self, attempt: Token) -> Result<Token, Refusal> {
        self.check_operation(attempt, Operation::Dismiss)?;
        self.change(Phase::Detached, 0)
    }

    /// Preserve legacy behavior and unchanged bindings. A changed binding
    /// invalidates pending work without opening an in-flight operation's fence.
    pub fn binding_changed(
        &mut self,
        actual: Option<NonZeroU64>,
    ) -> Result<Option<Token>, Refusal> {
        match self.phase {
            Phase::Legacy => return Ok(None),
            Phase::Exhausted => return Err(Refusal::Exhausted),
            _ => {}
        }
        let revision = actual.map_or(0, NonZeroU64::get);
        if revision == self.identity.revision {
            return Ok(None);
        }
        let next = match self.phase {
            Phase::Fenced(op) => Phase::Fenced(op),
            _ if revision == 0 => Phase::Detached,
            _ => Phase::Active,
        };
        self.change(next, revision).map(Some)
    }

    /// Validated human invitation; native invite identity is a separate check.
    pub fn human_invitation(&mut self) -> Result<Token, Refusal> {
        match self.phase {
            Phase::Detached => self.change(Phase::Invited, 0),
            Phase::Exhausted => Err(Refusal::Exhausted),
            _ => Err(Refusal::Closed),
        }
    }

    /// Report actual acceptance/refusal/expiry, using a newly established binding.
    pub fn invitation_finished(
        &mut self,
        invitation: Token,
        binding: Option<NonZeroU64>,
    ) -> Result<Token, Refusal> {
        self.check_identity(invitation)?;
        if self.phase != Phase::Invited {
            return Err(Refusal::Closed);
        }
        let revision = binding.map_or(0, NonZeroU64::get);
        self.change(
            if revision == 0 {
                Phase::Detached
            } else {
                Phase::Active
            },
            revision,
        )
    }

    /// Check at both enqueue and execution. Derive `party_accept` from the actual
    /// intent, never from a supplied permission flag. Lifecycle has native checks.
    pub fn admit(&self, token: Option<Token>, party_accept: bool) -> Result<(), Refusal> {
        if self.phase == Phase::Legacy {
            return if token.is_some() {
                Err(Refusal::Stale)
            } else {
                Ok(())
            };
        }
        self.check_identity(token.ok_or(Refusal::Required)?)?;
        match (self.phase, party_accept) {
            (Phase::Active, _) | (Phase::Invited, true) => Ok(()),
            _ => Err(Refusal::Closed),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn binding() -> NonZeroU64 {
        NonZeroU64::new(7).unwrap()
    }

    #[test]
    fn rebind_during_summon_requires_current_reconciliation() {
        let mut clock = Clock::default();
        let attempt = clock.begin(Operation::Summon, binding()).unwrap();
        let unbound = clock.binding_changed(None).unwrap().unwrap();
        assert_eq!(clock.summon_arrived(attempt), Err(Refusal::Stale));
        assert_eq!(clock.summon_arrived(unbound), Err(Refusal::Closed));
        let detached = clock.summon_abandoned(unbound).unwrap();
        assert_eq!(clock.admit(Some(detached), true), Err(Refusal::Closed));
        let invite = clock.human_invitation().unwrap();
        assert_eq!(clock.admit(Some(invite), false), Err(Refusal::Closed));
        assert_eq!(clock.admit(Some(invite), true), Ok(()));
        let joined = clock.invitation_finished(invite, Some(binding())).unwrap();
        assert_eq!(clock.admit(Some(joined), false), Ok(()));
        assert_eq!(clock.admit(Some(attempt), false), Err(Refusal::Stale));
    }

    #[test]
    fn overflow_preflight_does_not_mutate_and_transition_permanently_closes() {
        let mut clock = Clock::default();
        clock.order(binding()).unwrap();
        clock.identity.epoch = u64::MAX;
        let before = clock.snapshot();
        assert_eq!(clock.can_order(binding()), Err(Refusal::Exhausted));
        assert_eq!(clock.snapshot(), before);
        assert_eq!(clock.order(binding()), Err(Refusal::Exhausted));
        assert_eq!(clock.snapshot().phase, Phase::Exhausted);
        assert_eq!(clock.admit(before.token, false), Err(Refusal::Exhausted));
        assert_eq!(clock.admit(None, false), Err(Refusal::Required));
        assert_eq!(clock.binding_changed(None), Err(Refusal::Exhausted));
        assert_eq!(clock.snapshot().token, before.token);
    }

    #[test]
    fn dismiss_and_gear_fences_invalidate_old_work() {
        let mut clock = Clock::default();
        assert_eq!(clock.admit(None, false), Ok(()));
        let work = clock.order(binding()).unwrap();
        let gear = clock.begin(Operation::Gear, binding()).unwrap();
        assert_eq!(clock.admit(Some(work), false), Err(Refusal::Stale));
        assert_eq!(clock.admit(Some(gear), false), Err(Refusal::Closed));
        assert_eq!(clock.dismiss_completed(gear), Err(Refusal::WrongOperation));
        clock.gear_finished(gear).unwrap();
        let dismiss = clock.begin(Operation::Dismiss, binding()).unwrap();
        assert_eq!(clock.order(binding()), Err(Refusal::Closed));
        let detached = clock.dismiss_completed(dismiss).unwrap();
        assert_eq!(clock.admit(Some(detached), true), Err(Refusal::Closed));
    }
}
