//! `frob land`: synchronous land of a leased ticket branch (tickets.md section 10, cli.md, D25).
//!
//! [`land()`] checks the preconditions (leased, the holder's worktree, clean,
//! base merged, ticket-scoped check green, close guards), takes the land lock
//! (`<common_dir>/frob/land.lock`, [`LandLock`]), fast-forwards the base
//! branch, writes a `land` event, closes the ticket, releases the lease and
//! removes the worktree. Everything runs in the foreground; `--wait` bounds
//! the lock acquisition and the retries of a stale base (`E-LAND-STALE`). [`register`] adds the verb to a product root.

pub mod base_ci;
pub mod batch_size;
pub mod bisect;
pub mod candidate;
pub mod divergence;
pub mod error;
pub mod events;
mod git;
pub mod hostland;
pub mod hunk_presence;
pub mod land;
mod land_view;
pub mod lock;
mod lockfile;
pub mod plan;
mod ratchet;
pub mod relaunch;
pub mod train;
pub mod train_check;
pub mod train_close;
pub mod train_state;
pub mod verb;

pub use base_ci::{CiReader, GhCli, LandConfig};
pub use error::LandError;
pub use land::land;
pub use lock::{HolderRecord, LandLock, LockOptions, LockStatus, StallAction};
pub use plan::{LandOptions, LandOutcome, RetryPolicy, StageTiming};
pub use ratchet::FindingNote;
#[doc(hidden)]
pub use ratchet::{base_findings, cache_key, code_tree_key};
pub use train::{
    Enqueued, TrainDropReport, TrainOptions, TrainRunReport, TrainStatusReport, enqueue,
    land_train, train_drain, train_drop, train_run, train_status,
};

/// Register `land` on a product root.
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<verb::Land>()
        .register::<verb::TrainStatus>()
        .register::<verb::TrainRun>()
        .register::<verb::TrainDrain>()
        .register::<verb::TrainDrop>()
}
