//! `graph`: the model graph export (entities, bindings, planning edges and obligations).
//!
//! The payload is the `GraphDocument` of the strict sibling schema (`grimble.graph/1`); planning
//! entities carry `status`, `status_hi` and `level`, and `obligations` lists the PLAN backlog.

// frob:ticket 01M4FDBBXG990QVX35HERF5VCQ

use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::{CheckOptions, graph_document};
use serde_json::Value;

use crate::workspace::{check_error, locate_root};

/// Export the model graph with design status and obligations.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "graph",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Graph;

impl Command for Graph {
    type Data = Value;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<Value> {
        let root = locate_root(&ctx.cwd);
        let run = grimble_check::run(&root, &CheckOptions::default()).map_err(check_error)?;
        let doc = graph_document(&run);
        let count = |k: &str| doc[k].as_array().map_or(0, Vec::len);
        let text = format!(
            "{} entities, {} edges, {} obligations",
            count("entities"),
            count("edges"),
            count("obligations")
        );
        tracing::info!(entities = count("entities"), "graph exported");
        Ok(Payload::new(doc).with_rendered(vec![text]))
    }
}
