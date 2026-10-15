//! `map`: the project's style inventory, bucketed by the org layout, plus strays.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

use crunk_query::rows::MapData;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload};

use crate::query::load;

/// Inventory every stylesheet and JSX style module by org bucket.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "map",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Map;

impl Command for Map {
    type Data = MapData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<MapData> {
        let loaded = load("map", ctx)?;
        let data = loaded.model().map();
        let lines: Vec<String> = data
            .buckets
            .0
            .iter()
            .map(|(bucket, entries)| format!("{bucket}: {} entr(ies)", entries.len()))
            .chain(std::iter::once(format!("strays: {}", data.strays.len())))
            .collect();
        tracing::info!(strays = data.strays.len(), "map built");
        Ok(Payload::new(data).with_rendered(lines))
    }
}
