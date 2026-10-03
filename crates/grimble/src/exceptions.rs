//! `exceptions list`: every exception written in the model and how many findings it parked.

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::{CheckOptions, exceptions_json};
use schemars::JsonSchema;
use serde::Serialize;
use serde_json::Value;

use crate::workspace::{check_error, locate_root};

/// List the `accept`, `defer` and `hotfix` exceptions of the model with their suppress counts.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "exceptions list",
    product = "grimble",
    exits(ok, refused, usage, internal)
)]
pub struct ExceptionsList;

/// Output of `exceptions list`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ExceptionsData {
    /// Number of exceptions.
    pub count: usize,
    /// The records, in the shape of the sibling document's `exceptions` array.
    pub exceptions: Vec<Value>,
}

impl Command for ExceptionsList {
    type Data = ExceptionsData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<ExceptionsData> {
        let root = locate_root(&ctx.cwd);
        let run = grimble_check::run(&root, &CheckOptions::default()).map_err(check_error)?;
        let exceptions = exceptions_json(&run);
        tracing::info!(count = exceptions.len(), "exceptions listed");
        Ok(Payload::new(ExceptionsData {
            count: exceptions.len(),
            exceptions,
        }))
    }
}
