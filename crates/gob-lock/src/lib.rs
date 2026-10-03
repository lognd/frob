//! The ack lock file shared by every product (D28): `frob.lock`,
//! `grimble.lock`.
//!
//! A [`LockFile`] has a format `version` and a `digest_scheme` (the gob-ir
//! facet scheme the digests were computed under), then typed entries:
//! `[[symbol]]` ([`LockEntry`]: identity, symref, the five facet digests,
//! who, when, reason, bound doc sections as [`LockTarget`]) and `[[flow]]`
//! ([`FlowEntry`]: flow key, producer and consumer identity with Contract
//! digest, plus the optional `shape_contract` digest of the flow's contract shape, which SYS006
//! compares against the live shape). `[[ack_log]]` ([`AckLogEntry`]) is the append-only record of
//! decisions the entries do not show, today `rename`. The file is TOML, entries sorted, so two saves of the same
//! content are byte-identical and diffs stay small.
//!
//! A file of another version or scheme loads, but [`LockFile::reattest`] lists
//! every entry: nothing is silently accepted, and only [`plan`] with `all` and a
//! reason rewrites the header. [`plan`] is the product-neutral ack planner.
//! This crate knows nothing about git, symbols or products beyond
//! [`file_name`]: callers decide what to acknowledge and commit the bytes.
//!
//! ```
//! use gob_lock::{LockEntry, LockFile};
//! let mut lock = LockFile::default();
//! lock.entries.insert("a.rs::f".to_owned(), LockEntry::new("s", "b", "d", "me", "2026-10-02T00:00:00Z"));
//! let text = lock.to_toml().unwrap();
//! assert_eq!(LockFile::from_toml(&text).unwrap(), lock);
//! ```

mod diff;
mod file;
mod plan;

pub use diff::{Facet, LockDiff, diff};
pub use file::{
    AckLogEntry, AckLogKind, DIGEST_SCHEME, EntryKind, FlowEnd, FlowEntry, LOCK_VERSION, LockEntry,
    LockError, LockFile, LockTarget, Reattest, file_name,
};
pub use plan::{Current, CurrentFlow, CurrentSymbol, FacetSet, Plan, PlanError, PlanOptions, plan};
