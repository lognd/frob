//! `frob work [--here]` (hidden alias `start`) and `frob requeue` (tickets.md section 3, cli.md sections 3 and 5).
//!
//! [`Workspace::work`] takes the scope lease ([`frob_lease`]), creates a linked
//! worktree on branch `ticket/<handle>` from the base branch (`[tickets] ref`),
//! merges the base, and appends the `in-progress` transition carrying the
//! lease summary. It is idempotent for the same holder (actor plus worktree
//! path) and refuses everyone else with `E-LEASE-HELD`. [`Workspace::start`] is
//! the same without a worktree, [`Workspace::requeue`] undoes both. The
//! worktree directory comes from the `[worktree] dir` knob
//! ([`WorktreeConfig`], default `../<repo>-wt`).
//!
//! [`register`] adds the three verbs to a product root.

pub mod activity;
pub mod anyway;
pub mod claim;
pub mod claim_evict;
pub mod claim_hold;
pub mod claim_restore;
pub mod config;
pub mod cycle_gate;
pub mod error;
pub mod evict;
pub mod gc;
pub mod next;
pub(crate) mod pathtext;
pub mod verbs;
pub mod wip;
pub mod work;

pub use config::{WorktreeConfig, ledger_config};
pub use error::WorktreeError;
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
pub use gc::GcConfig;
pub use work::{Requeued, Started, WorkOptions, Workspace, normalize_mtimes, seed_caches};

/// Register `work`, `start`, `requeue`, `claim restore`, `claim evict`, `claim hold` and `claim resume` on a product root.
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<verbs::Work>()
        .register::<verbs::Start>()
        .register::<verbs::Requeue>()
        .register::<verbs::ClaimRestore>()
        .register::<verbs::ClaimEvict>()
        .register::<verbs::ClaimHold>()
        .register::<verbs::ClaimResume>()
}
