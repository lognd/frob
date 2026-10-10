//! Automatic garbage collection (~BZXZK29): a throttled pass that keeps build output,
//! ticket worktrees, caches and evidence blobs under budget.
//!
//! The pass runs inside verbs that already run often and are about to need disk
//! (`frob work` before it builds a worktree, `frob land` after it removes one) and
//! unthrottled from `frob doctor --fix`. It never fails the verb: [`pass::run`]
//! returns a [`pass::Report`] and every error inside is a warning in it.
//!
//! Safety is structural, not a convention:
//!
//! - every path is admitted through a [`jail::Jail`] before anything touches it: the
//!   roots are the repository's own target dirs, frob's own state under the git common
//!   dir and the worktree parent frob created; containment is decided on path
//!   components, never string prefixes, and a symlink is never followed out of a root;
//! - a worktree is removed only through plain `git worktree remove` (no `--force`),
//!   after frob has itself checked for a live lease, uncommitted changes and, for an
//!   open ticket, commits that exist nowhere else;
//! - build output goes through a [`adapter::BuildAdapter`] (Cargo first), whose plan
//!   never lists the latest build's artifacts or the configured binaries.
//!
//! Layout: [`config`] is the `[gc]` table, [`jail`] the path discipline, [`scan`]
//! sizes trees without following links, [`adapter`] and [`cargo`] plan build output,
//! [`worktrees`], [`caches`] and [`artifacts`] collect frob-owned data, [`stamp`] is the
//! throttle and last-pass record, [`pass`] orchestrates them and [`glue`] wires a pass to the ledger and leases for verbs.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

pub mod adapter;
pub mod artifacts;
pub mod caches;
pub mod cargo;
pub mod config;
pub mod free;
pub mod git;
pub mod glue;
pub mod jail;
pub mod pass;
pub mod removing;
pub mod scan;
pub mod stamp;
pub mod worktrees;

pub use config::GcConfig;
pub use pass::{Env, Mode, Report, TicketOracle, TicketState, report_only, run};
