//! In-process bot primitives. This crate has no network, database or game runtime.
//! Adapters own authentication, authoritative snapshots, queues and all mutations.
//! C1 extracts cancellation identities and the existing FFXI command vocabulary;
//! it does not replace the native authority, order planner or executor.

#![forbid(unsafe_code)]

pub mod brain;
pub mod chat;
pub mod economy;
pub mod goals;
pub mod nav;
pub mod persona;
pub mod roles;
pub mod sched;

/// Hot-loaded by an adapter on its game thread. Default enables no new behavior.
/// Turning off must hand control back to that adapter's original implementation.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct FeatureFlags {
    pub shared_control: bool,
    pub companions: bool,
    pub population: bool,
    pub economy: bool,
    pub generated_chat: bool,
}
