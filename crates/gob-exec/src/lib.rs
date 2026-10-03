//! Bounded process execution for every goblin.
//!
//! `gob-exec` (with `gob-git`) is the only crate allowed to reference
//! `std::process`; the [`proc001`] scan enforces that. Every spawn goes
//! through a [`Runner`], which bounds concurrency with a semaphore, logs
//! the argv, duration and exit under an `exec.spawn` span, kills the whole
//! process group on timeout, caps and redacts captured output with
//! [`gob_log::redact`], and counts spawns (see [`SpawnCount`]).
//! Design: `git-io.md` section 3, `architecture.md` section 9.

mod counter;
mod error;
pub mod proc001;
mod program;
mod runner;
mod semaphore;

pub use counter::{SpawnCount, assert_spawns};
pub use error::ExecError;
pub use program::Program;
pub use runner::{DEFAULT_OUTPUT_CAP, Limits, Outcome, Output, Runner, Spec};
