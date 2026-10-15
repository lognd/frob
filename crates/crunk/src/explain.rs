//! `explain NAME`: everything that defines or touches one design token.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use crunk_query::rows::ExplainRow;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::query::load;

/// Explain a token: value, group, where defined, every use site and utilities.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "explain",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Explain {
    name: String,
}

/// Output of `explain`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ExplainData {
    /// The explained token (one row).
    pub results: Vec<ExplainRow>,
}

/// `Explain` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct ExplainArgs {
    #[arg(
        value_name = "NAME",
        help = "The token name, with or without the leading --"
    )]
    name: String,
}

impl Command for Explain {
    type Data = ExplainData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<ExplainArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<ExplainArgs>(m)?;
        Ok(Self { name: a.name })
    }

    fn run(&self, ctx: &Context) -> Outcome<ExplainData> {
        let loaded = load("explain", ctx)?;
        let defined_in = loaded.spec.tokens_path();
        let row = loaded
            .model()
            .explain(&self.name, Some(defined_in.as_path()))
            .map_err(|close| {
                let mut message = format!(
                    "explain: token name not found among the project's exported tokens: '{}'",
                    self.name
                );
                if !close.is_empty() {
                    message.push_str("\ndid you mean: ");
                    message.push_str(&close.join(", "));
                }
                CliError::Usage(message)
            })?;
        let mut lines = vec![
            format!("{} = {}", row.name, row.value.as_deref().unwrap_or("-")),
            format!("group: {}", row.group),
        ];
        lines.extend(row.sites.iter().map(|s| format!("  {}:{}", s.path, s.line)));
        tracing::info!(name = %row.name, sites = row.sites.len(), "explained");
        Ok(Payload::new(ExplainData { results: vec![row] }).with_rendered(lines))
    }
}
