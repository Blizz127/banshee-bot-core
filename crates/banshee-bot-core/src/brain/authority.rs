//! Pure checks over facts supplied by the native game thread. These snapshots
//! are not client input: the adapter must obtain them from authenticated sessions,
//! the population roster and the current party/binding records.
//!
//! Bindings identify an accepted invitation's lifetime, not party leadership.
//! The native owner allocates nonzero revisions without reuse, retains them
//! through zoning/leadership changes and ends them on the actual leave lifecycle.
//! No function here stores state, executes gameplay or grants GM authority.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ActorKind {
    Human,
    PopulationBot,
    PersonaBot,
    SocketlessActor,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RequesterSnapshot {
    pub actor_id: u32,
    pub kind: ActorKind,
    pub current_session: bool,
    pub generation: u64,
    pub party_uid: Option<u64>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OwnerBinding {
    pub owner: u32,
    pub party_uid: u64,
    pub revision: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TargetSnapshot {
    pub actor_id: u32,
    pub kind: ActorKind,
    /// Membership verified against the native population roster, never a name prefix.
    pub registered_population: bool,
    pub current_session: bool,
    pub generation: u64,
    pub party_uid: Option<u64>,
    pub binding: Option<OwnerBinding>,
}

/// Accepted means the native accept handler already inserted the member. A
/// pending invitation or a queued acceptance must not be represented as Accepted.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InvitationOutcome {
    Pending,
    Declined,
    Refused,
    Accepted {
        inviter: u32,
        invitee: u32,
        party_uid: u64,
    },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Denial {
    InvalidRequester,
    NotInParty,
    NotPopulationBot,
    WrongParty,
    Unbound,
    WrongOwner,
    InvalidBinding,
    TargetUnavailable,
    InvitationNotAccepted,
    InvitationMismatch,
    AlreadyBound,
    StaleTicket,
}

fn current_party(requester: &RequesterSnapshot) -> Result<u64, Denial> {
    let valid = requester.actor_id != 0
        && requester.kind == ActorKind::Human
        && requester.current_session
        && requester.generation != 0;
    if !valid {
        return Err(Denial::InvalidRequester);
    }
    match requester.party_uid {
        Some(party) if party != 0 => Ok(party),
        _ => Err(Denial::NotInParty),
    }
}

fn require_population(target: &TargetSnapshot) -> Result<(), Denial> {
    match (target.actor_id, target.kind, target.registered_population) {
        (id, ActorKind::PopulationBot, true) if id != 0 => Ok(()),
        _ => Err(Denial::NotPopulationBot),
    }
}

fn require_session(target: &TargetSnapshot) -> Result<(), Denial> {
    if target.current_session && target.generation != 0 {
        Ok(())
    } else {
        Err(Denial::TargetUnavailable)
    }
}

/// Run even for an empty roster; it does not authorize any particular target.
pub fn validate_requester(requester: &RequesterSnapshot) -> Result<(), Denial> {
    current_party(requester).map(|_| ())
}

/// Check the native acceptance receipt before constructing a binding. The
/// caller supplies its newly allocated revision; this function does not advance
/// counters or overwrite an existing binding.
pub fn binding_from_accepted_invitation(
    outcome: InvitationOutcome,
    inviter: &RequesterSnapshot,
    invitee: &TargetSnapshot,
    revision: u64,
) -> Result<OwnerBinding, Denial> {
    let receipt = match outcome {
        InvitationOutcome::Accepted {
            inviter,
            invitee,
            party_uid,
        } => (inviter, invitee, party_uid),
        _ => return Err(Denial::InvitationNotAccepted),
    };
    let party = current_party(inviter)?;
    require_population(invitee)?;
    require_session(invitee)?;
    if receipt != (inviter.actor_id, invitee.actor_id, party) {
        return Err(Denial::InvitationMismatch);
    }
    if invitee.party_uid != Some(party) || invitee.actor_id == inviter.actor_id {
        return Err(Denial::WrongParty);
    }
    if invitee.binding.is_some() {
        return Err(Denial::AlreadyBound);
    }
    if revision == 0 {
        return Err(Denial::InvalidBinding);
    }
    Ok(OwnerBinding {
        owner: inviter.actor_id,
        party_uid: party,
        revision,
    })
}

fn checked_binding(
    requester: &RequesterSnapshot,
    target: &TargetSnapshot,
) -> Result<OwnerBinding, Denial> {
    let party = current_party(requester)?;
    require_population(target)?;
    if target.actor_id == requester.actor_id || target.party_uid != Some(party) {
        return Err(Denial::WrongParty);
    }
    let binding = match target.binding {
        Some(binding) => binding,
        None => return Err(Denial::Unbound),
    };
    if binding.owner != requester.actor_id {
        return Err(Denial::WrongOwner);
    }
    if binding.party_uid != party || binding.revision == 0 {
        return Err(Denial::InvalidBinding);
    }
    Ok(binding)
}

/// An unavailable owned bot may still be selected for availability feedback.
/// Mutation additionally needs a current session when issuing/checking a ticket.
pub fn authorize_owned_bot(
    requester: &RequesterSnapshot,
    target: &TargetSnapshot,
) -> Result<(), Denial> {
    checked_binding(requester, target).map(|_| ())
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mutation {
    Summon,
    Dismiss,
    Order,
    Gear,
}

/// Opaque, process-local identity for a proposed mutation. The native executor
/// owns consumption and must freshly revalidate this identity plus its event,
/// instance, zone, control-fence and action-specific requirements before acting.
/// Copying a ticket is not permission to replay an action; it is not serialized.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MutationTicket {
    mutation: Mutation,
    owner: u32,
    owner_generation: u64,
    target: u32,
    target_generation: u64,
    party_uid: u64,
    ownership_revision: u64,
}

impl MutationTicket {
    pub fn mutation(&self) -> Mutation {
        self.mutation
    }
    pub fn owner(&self) -> u32 {
        self.owner
    }
    pub fn target(&self) -> u32 {
        self.target
    }
}

pub fn issue_ticket(
    mutation: Mutation,
    requester: &RequesterSnapshot,
    target: &TargetSnapshot,
) -> Result<MutationTicket, Denial> {
    let binding = checked_binding(requester, target)?;
    require_session(target)?;
    Ok(MutationTicket {
        mutation,
        owner: requester.actor_id,
        owner_generation: requester.generation,
        target: target.actor_id,
        target_generation: target.generation,
        party_uid: binding.party_uid,
        ownership_revision: binding.revision,
    })
}

/// Supply freshly read snapshots in the native execution critical section.
/// Reusing the old snapshots would defeat the generation/lifetime checks.
pub fn validate_ticket(
    ticket: &MutationTicket,
    requester: &RequesterSnapshot,
    target: &TargetSnapshot,
) -> Result<(), Denial> {
    let current = issue_ticket(ticket.mutation, requester, target)?;
    if current == *ticket {
        Ok(())
    } else {
        Err(Denial::StaleTicket)
    }
}
