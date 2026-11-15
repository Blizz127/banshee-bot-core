//! Nonblocking optional advice over one frozen strategy frame. The adapter
//! supplies monotonic milliseconds; this module reads no clock and starts no
//! timer, thread, model request or game action. Selection is not execution.

use super::decision::{ActionId, Advice, Decision, DecisionError, FrameId};
use super::strategy::PreparedFrame;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AdviceRequest<'a> {
    pub frame: FrameId,
    pub choices: &'a [ActionId],
    pub deadline_ms: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reply<'a> {
    Ranking(Advice<'a>),
    /// A model timeout, service refusal or parse failure for this frame.
    Unavailable {
        frame: FrameId,
    },
}

impl Reply<'_> {
    fn frame(self) -> FrameId {
        match self {
            Self::Ranking(advice) => advice.frame,
            Self::Unavailable { frame } => frame,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PendingReason {
    AwaitingReply,
    StaleReply,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Resolution {
    NoAdviceChoices,
    Deadline,
    /// Decision.advice says whether the ranking was applied or rejected.
    Ranking,
    Unavailable,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Outcome {
    Pending(PendingReason),
    Ready {
        decision: Decision,
        reason: Resolution,
    },
    Closed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WindowError {
    DeadlineOverflow,
    /// The adapter's clock moved backward; the frame is discarded.
    ClockRegressed,
    Decision(DecisionError),
}

/// Owns one prepared frame and yields at most one decision. Not Clone, resettable
/// or resumable. Frame identity and scope still belong to the native adapter;
/// equality of IDs is not authentication or proof of current game legality.
pub struct AdviceWindow {
    frame: Option<PreparedFrame>,
    last_now_ms: u64,
    deadline_ms: u64,
}

impl AdviceWindow {
    /// `max_wait_ms` is the adapter's explicit budget, not a core default. Zero
    /// requests immediate fallback. Overflow refuses construction without a pick.
    pub fn new(frame: PreparedFrame, now_ms: u64, max_wait_ms: u64) -> Result<Self, WindowError> {
        let deadline_ms = now_ms
            .checked_add(max_wait_ms)
            .ok_or(WindowError::DeadlineOverflow)?;
        Ok(Self {
            frame: Some(frame),
            last_now_ms: now_ms,
            deadline_ms,
        })
    }

    /// Frozen request data, not a model call. No request exists for an immediate
    /// fallback or closed window. The caller must poll using current time before
    /// dispatching; this getter does not read a clock or extend the deadline.
    pub fn request(&self) -> Option<AdviceRequest<'_>> {
        let fallback = self.frame.as_ref()?.fallback();
        if fallback.advice_choices.is_empty() || self.last_now_ms >= self.deadline_ms {
            return None;
        }
        Some(AdviceRequest {
            frame: fallback.frame,
            choices: &fallback.advice_choices,
            deadline_ms: self.deadline_ms,
        })
    }

    /// Poll once on the adapter's existing loop. No eligible advice means an
    /// immediate fallback, including safety/owner decisions and economy ties.
    /// At or after the deadline, fallback wins even over a supplied ranking.
    /// Before it, replies for another frame leave this window pending.
    pub fn poll(&mut self, now_ms: u64, reply: Option<Reply<'_>>) -> Result<Outcome, WindowError> {
        let Some(frame) = &self.frame else {
            return Ok(Outcome::Closed);
        };
        if now_ms < self.last_now_ms {
            self.cancel();
            return Err(WindowError::ClockRegressed);
        }
        self.last_now_ms = now_ms;
        if frame.fallback().advice_choices.is_empty() {
            return self.finish(None, Resolution::NoAdviceChoices);
        }
        if now_ms >= self.deadline_ms {
            return self.finish(None, Resolution::Deadline);
        }
        match reply {
            Some(reply) if reply.frame() != frame.fallback().frame => {
                Ok(Outcome::Pending(PendingReason::StaleReply))
            }
            Some(Reply::Ranking(advice)) => self.finish(Some(advice), Resolution::Ranking),
            Some(Reply::Unavailable { .. }) => self.finish(None, Resolution::Unavailable),
            None => Ok(Outcome::Pending(PendingReason::AwaitingReply)),
        }
    }

    /// Drop stale planning work without a fallback action. The adapter must call
    /// this on relevant world/ownership/order/flag changes before using a result.
    pub fn cancel(&mut self) -> bool {
        self.frame.take().is_some()
    }

    fn finish(
        &mut self,
        advice: Option<Advice<'_>>,
        reason: Resolution,
    ) -> Result<Outcome, WindowError> {
        let Some(frame) = self.frame.take() else {
            return Ok(Outcome::Closed);
        };
        let decision = frame.resolve(advice).map_err(WindowError::Decision)?;
        Ok(Outcome::Ready { decision, reason })
    }
}
