//! `graph`: the model graph export (entities, bindings, planning edges and obligations).
//!
//! The payload is the `GraphDocument` of the strict sibling schema (`grimble.graph/1`); planning
//! entities carry `status`, `status_hi` and `level`, and `obligations` lists the PLAN backlog.
//! With `--mermaid` the payload is instead `{"mermaid": "..."}`: a sequence and an activity
//! diagram per scenario and a use-case diagram per system (grmb-spec 17.7).

// frob:ticket 01M4FDBBXG990QVX35HERF5VCQ
// frob:ticket 01M4FDBG95B8D1NERFERXC0PXF

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use grimble_check::{CheckOptions, graph_document};
use serde_json::{Value, json};

use crate::workspace::{check_error, locate_root};

/// Export the model graph with design status and obligations.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "graph",
    product = "grimble",
    idempotent = true,
    exits(ok, usage, internal)
)]
pub struct Graph {
    mermaid: bool,
}

/// `Graph` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct GraphArgs {
    #[arg(
        long,
        help = "Print mermaid sequence, activity and use-case diagrams of the planning model"
    )]
    mermaid: bool,
}

impl Command for Graph {
    type Data = Value;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<GraphArgs>(cmd)
    }

    fn from_matches(matches: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<GraphArgs>(matches)?;
        Ok(Self { mermaid: a.mermaid })
    }

    fn run(&self, ctx: &Context) -> Outcome<Value> {
        let root = locate_root(&ctx.cwd);
        if self.mermaid {
            let text = grimble_check::mermaid::render_repo(&root).map_err(check_error)?;
            tracing::info!(bytes = text.len(), "graph mermaid rendered");
            let lines = text.lines().map(str::to_owned).collect();
            return Ok(Payload::new(json!({ "mermaid": text })).with_rendered(lines));
        }
        // A read-only export: it must not leave telemetry or precision history in the repository.
        let options = CheckOptions {
            skip_telemetry: true,
            ..CheckOptions::default()
        };
        let run = grimble_check::run(&root, &options).map_err(check_error)?;
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
