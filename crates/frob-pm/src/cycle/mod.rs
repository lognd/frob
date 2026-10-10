//! Cycle rules the verbs share: window defaults, overlap, `new` idempotency, the close plan and the fill plan.
//!
//! Pure functions over folded [`crate::Cycle`]s and a snapshot of their member
//! tickets, so the CLI layer only gathers facts and maps the typed
//! [`lifecycle::CycleError`] to a refusal; nothing here touches the ledger.

pub mod assign;
pub mod history;
pub mod lifecycle;
pub mod plan;
pub mod velocity;
