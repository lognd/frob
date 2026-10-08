//! Bounded process execution for every goblin.
//!
//! `gob-exec` (with `gob-git`) is the only crate allowed to reference
//! `std::process`; the [`proc001`] scan enforces that. Every spawn goes
//! through a [`Runner`], which bounds concurrency with a semaphore, logs
//! the argv, duration and exit under an `exec.spawn` span, kills the whole
//! process group on timeout, caps and redacts captured output with
//! [`gob_log::redact`], and counts spawns (see [`SpawnCount`]).
//! Design: `git-io.md` section 3, `architecture.md` section 9.

mod cmdline;
mod counter;
mod discover;
mod env;
mod error;
mod path;
pub mod proc001;
mod program;
mod runner;
mod semaphore;

pub use cmdline::{Arg, Shell, command_line};
pub use counter::{SpawnCount, assert_spawns};
pub use discover::{
    Origin, Platform, Sibling, beside_dirs, executable_names, find_sibling, plan, tool_env_dirs,
    tool_env_roots,
};
pub use env::{BASELINE, EnvPolicy, is_secret_shaped};
pub use error::ExecError;
pub use path::{
    Style, canonical, has_dot_component, path_has_dot_component, path_strictly_inside,
    simplify_verbatim, strictly_inside,
};
pub use program::Program;
pub use runner::{DEFAULT_OUTPUT_CAP, Limits, Outcome, Output, Runner, Spec};
