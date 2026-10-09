//! Shared command-line root for the goblins (cli.md sections 1 to 4).
//!
//! A product builds a [`Cli`] with [`Cli::new`], registers each verb type
//! with [`Cli::register`], and calls [`Cli::run`]. A verb is a type that
//! derives [`Command`](macro@Command) (metadata plus an `inventory` entry that
//! [`all_commands`] lists for reference generation) and implements the
//! [`Command`](trait@Command) trait. Global flags: `--format json|text|auto`
//! (`--json`, `--text` as aliases), `--quiet`, `-v`, `--color`, `--cwd`,
//! `--schema`, and `--dry-run` on verbs that opt in. Results are rendered as
//! the gob-diagnostics envelope (JSON) or a text view of it; the root returns
//! the exit code from the one table in cli.md section 2. Nothing in this
//! crate writes to stdout or stderr except `emit` in the private render
//! module.

mod cli;
mod command;
mod context;
mod error;
mod meta;
mod render;
mod schema_cmd;
mod serve;

// The derive expands to `::gob_cli::...`, which must resolve in this crate too.
extern crate self as gob_cli;

pub use clap;
pub use cli::{Cli, Guard, run_for_test};
pub use command::Command;
pub use context::{ColorMode, Context, FormatChoice};
pub use error::{CliError, FindingsFailure, Outcome, Payload};
pub use gob_diagnostics::{ExitCode, Refusal, RefusalClass};
pub use gob_macros::Command;
pub use inventory;
pub use meta::{
    CommandEntry, CommandMeta, Described, all_commands, dangling_deprecations, markdown_verbs,
};
pub use schema_cmd::{SchemaCmd, SchemaData};
pub use serve::{ServeCmd, ServeError};
