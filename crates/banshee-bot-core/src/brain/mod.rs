//! Pure control contracts. Native adapters supply authenticated current facts
//! and retain every gameplay mutation and execution readiness check.
//! Future strategy ordering: safety, owner order, role, goals, optional advice.
pub mod authority;
pub mod command;
pub mod orders;
pub mod selection;
