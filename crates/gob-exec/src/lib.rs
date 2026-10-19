//! Bounded process execution for every goblin.
//!
//! `gob-exec` (with `gob-git`) is the only crate allowed to reference
//! `std::process`; the [`proc001`] scan enforces that. Every spawn goes
//! through a [`Runner`], which bounds concurrency with a semaphore, logs
//! the argv, duration and exit under an `exec.spawn` span, kills the whole
//! process group on timeout, caps captured output, redacts stdout and stderr (stdout also raw, for payload parsing) with
//! [`gob_log::redact`], and counts spawns (see [`SpawnCount`]). A caller that needs only
//! specific variables passes an [`EnvPolicy::Scrub`] allowlist to [`Runner::run_with_env`]; a
//! secret-shaped name is never inherited, only added explicitly per spawn.
//! Design: `git-io.md` section 3, `architecture.md` section 9.
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

mod cmdline;
mod counter;
mod discover;
mod env;
mod error;
mod pack;
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
// frob:ticket 01M4M52WKHGXADHPQ08J1AS8BJ
pub use gob_fs::{
    Style, canonical, has_dot_component, path_has_dot_component, path_strictly_inside,
    simplify_verbatim, strictly_inside,
};
// frob:ticket 01M3ZX7VPGRERTZNVS5VR437JY
pub use pack::{PACK_ENV, ProcessPack, digest_file, resolve_pack};
pub use program::Program;
pub use runner::{DEFAULT_OUTPUT_CAP, Limits, Outcome, Output, Runner, Spec};
