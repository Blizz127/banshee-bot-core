//! Roles preserve the current FFXI order vocabulary. Game job IDs stay in adapters.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Role {
    Tank,
    Healer,
    Dps,
    Puller,
}

/// Broader policy classification for future adapters. This does not add a new
/// accepted FFXI command or change an existing rotation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PolicyRole {
    Tank,
    Healer,
    Damage,
    Support,
    Puller,
}

impl From<Role> for PolicyRole {
    fn from(role: Role) -> Self {
        match role {
            Role::Tank => Self::Tank,
            Role::Healer => Self::Healer,
            Role::Dps => Self::Damage,
            Role::Puller => Self::Puller,
        }
    }
}
