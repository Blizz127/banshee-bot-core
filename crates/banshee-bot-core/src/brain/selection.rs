//! Bounded target selection over one authoritative party snapshot. Names are
//! selectors, not ownership claims. Returned indices belong to this exact
//! snapshot; execution still needs freshly checked native facts and a ticket.

use super::authority::{
    authorize_owned_bot, validate_requester, Denial, RequesterSnapshot, TargetSnapshot,
};
use super::command::{self, Command, Target};

/// FFXI compatibility limit, counting the entire supplied party snapshot.
pub const MAX_CANDIDATES: usize = 6;

#[derive(Clone, Copy, Debug)]
pub struct Candidate<'a> {
    pub target: TargetSnapshot,
    pub name: &'a str,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SelectionError {
    Unauthorized(Denial),
    TooManyCandidates,
    InvalidSelector,
    InvalidName,
    DuplicateActor,
    AmbiguousName,
    NotFound,
}

fn checked_selector(selector: &Target) -> Result<(), SelectionError> {
    let Target::Name(name) = selector else {
        return Ok(());
    };
    if !command::valid_name(name.as_bytes()) || name.eq_ignore_ascii_case("all") {
        return Err(SelectionError::InvalidSelector);
    }
    let expected = Command::Summon(Target::Name(name.clone()));
    if command::parse(format!("/fb summon {name}").as_bytes()) != Ok(Some(expected)) {
        return Err(SelectionError::InvalidSelector);
    }
    Ok(())
}

/// Exact case-insensitive names or explicit All, retaining native snapshot order.
/// Unauthorized rows are ignored before looking at names or duplicate IDs, so
/// foreign rows cannot leak name errors or create ambiguity for an owned target.
pub fn select_owned(
    requester: &RequesterSnapshot,
    selector: &Target,
    candidates: &[Candidate<'_>],
) -> Result<Vec<usize>, SelectionError> {
    validate_requester(requester).map_err(SelectionError::Unauthorized)?;
    if candidates.len() > MAX_CANDIDATES {
        return Err(SelectionError::TooManyCandidates);
    }
    checked_selector(selector)?;

    let mut ids = Vec::with_capacity(candidates.len());
    let mut selected = Vec::new();
    for (index, candidate) in candidates.iter().enumerate() {
        if authorize_owned_bot(requester, &candidate.target).is_err() {
            continue;
        }
        if ids.contains(&candidate.target.actor_id) {
            return Err(SelectionError::DuplicateActor);
        }
        ids.push(candidate.target.actor_id);
        if !command::valid_name(candidate.name.as_bytes()) {
            return Err(SelectionError::InvalidName);
        }
        let include = match selector {
            Target::All => true,
            Target::Name(name) => name.eq_ignore_ascii_case(candidate.name),
        };
        if include {
            selected.push(index);
        }
    }
    match (selector, selected.len()) {
        (Target::Name(_), 0) => Err(SelectionError::NotFound),
        (Target::Name(_), 2..) => Err(SelectionError::AmbiguousName),
        _ => Ok(selected),
    }
}
