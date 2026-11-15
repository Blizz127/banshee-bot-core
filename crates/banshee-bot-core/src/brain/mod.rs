//! Pure control contracts. Native adapters supply authenticated current facts
//! and retain every gameplay mutation and execution readiness check.
//! Future strategy ordering: safety, owner order, role, goals, optional advice.
pub mod advice_window;
pub mod authority;
pub mod command;
pub mod decision;
pub mod formation;
pub mod orders;
pub mod selection;
pub mod strategy;
