//! Milestones and cycles as event-sourced ledger objects (design:
//! `releases.md` section 6a, `tickets.md` sections 2a and 3,
//! `pm-enforcement.md` section 4).
//!
//! # Storage
//!
//! Both kinds live below the ledger's tickets directory, one directory per
//! object named by a ULID: `_milestones/<ULID>/milestone.md` and
//! `_cycles/<ULID>/cycle.md` (TOML frontmatter between `+++` fences) plus
//! `events/<ULID>.toml`, one append-only file per change ([`event`]). The
//! frontmatter is a cache of [`fold::fold`] over the events, exactly as for
//! tickets, so two branches that each append events merge without losing any
//! ([`merge`]). A milestone's alias is its version, a cycle's the dates
//! (`START..END`). Membership (epics of a milestone, tickets of a cycle) is a
//! `member` event on the object and never a field of the ticket.
//!
//! # Writes
//!
//! [`store::PmStore`] appends through the ledger's generic object path
//! (`Ledger::commit_files`): event files and re-folded frontmatter in one CAS
//! commit on the ledger ref. Exit criteria bind to evidence by the ticket
//! rule (`frob_ledger::fold::evidence_passes`, remapped through criterion
//! removals). `doctor` ([`doctor`]) re-folds everything and reports drift.
//!
//! # Compatibility
//!
//! Ticket reads only accept `tickets/<ULID>/ticket.md`, so a binary without
//! this crate ignores `_milestones/` and `_cycles/` entirely.

pub mod config;
pub mod doctor;
pub mod error;
pub mod event;
pub mod fold;
pub mod merge;
pub mod milestone;
pub mod model;
pub mod rules;
pub mod store;

pub use config::{
    DoneRequirement, PmClassesTable, PmConfig, PmTable, PmWipTable, Pull, ReadyRequirement,
};
pub use error::{PmError, Result};
pub use model::{Cycle, Day, Milestone, Object, ObjectId, ObjectKind, State};
pub use store::{Applied, NewObject, PmStore};
