//! Fix engine: edits, tiers, deterministic overlap resolution, dry-run diff, atomic apply.
//!
//! Applicability itself lives in `gob-rules` ([`Applicability`], D90); this crate only
//! consumes it, so the type exists in exactly one place.

// frob:ticket 01M43ARX0JB4A8E1YW329MKDDF

mod apply;
mod plan;

pub use apply::{
    ApplyReport, FileDiff, FileOutcome, FixError, JournalEntry, Mode, Snapshot, Validator, apply,
    apply_validated,
};
pub use gob_rules::Applicability;
pub use plan::{DropReason, Dropped, Edit, Fix, Plan, Tier, plan};
