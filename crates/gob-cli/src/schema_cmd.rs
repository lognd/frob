//! The built-in `schema` verb: envelope and config schemas.

use clap::ArgMatches;
use gob_config::all_tables;
use gob_diagnostics::envelope_schema;
use schemars::JsonSchema;
use serde::Serialize;

use crate::{CliError, Command, Context, Outcome, Payload};

/// Print the JSON schemas of the output envelope and every config table.
#[derive(Debug, Clone, Copy, Default, crate::Command)]
#[command(
    verb = "schema",
    product = "any",
    idempotent = true,
    read_only,
    exits(ok, usage, internal)
)]
pub struct SchemaCmd;

/// Output of `schema`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct SchemaData {
    /// JSON Schema of the output envelope (opaque `data`).
    pub envelope: serde_json::Value,
    /// JSON Schema of every registered config table.
    pub config: serde_json::Value,
}

impl Command for SchemaCmd {
    type Data = SchemaData;

    fn from_matches(_matches: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, _ctx: &Context) -> Outcome<SchemaData> {
        let mut tables: Vec<_> = all_tables().collect();
        tables.sort_by(|a, b| a.table.cmp(&b.table));
        let refs: Vec<_> = tables.iter().collect();
        tracing::debug!(tables = refs.len(), "schema assembled");
        Ok(Payload::new(SchemaData {
            envelope: envelope_schema(),
            config: gob_config::schema(&refs),
        })
        .with_already(false))
    }
}
