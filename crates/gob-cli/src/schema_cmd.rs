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

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
/// A product's own config schema, merged into the `config` document of `schema`.
///
/// For tables that are not `ConfigTable`s (crunk's `crunk.toml` tables are typed
/// by the spec crate). The schema's `properties` join the config properties and
/// its `$defs` join the document's `$defs`.
pub struct SchemaExtension {
    render: fn() -> serde_json::Value,
}

impl SchemaExtension {
    /// Wrap the function that renders the extra JSON Schema (an object schema with `properties`).
    pub const fn new(render: fn() -> serde_json::Value) -> Self {
        Self { render }
    }
}

inventory::collect!(SchemaExtension);

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
/// Copy the object under `key` of `extra` into the object under `key` of `config`.
fn merge_object(
    config: &mut serde_json::Map<String, serde_json::Value>,
    extra: &serde_json::Value,
    key: &str,
) {
    let Some(from) = extra.get(key).and_then(serde_json::Value::as_object) else {
        return;
    };
    let slot = config
        .entry(key.to_owned())
        .or_insert_with(|| serde_json::Value::Object(serde_json::Map::new()));
    if let Some(into) = slot.as_object_mut() {
        for (k, v) in from {
            into.entry(k.clone()).or_insert_with(|| v.clone());
        }
    }
}

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
/// Merge every registered [`SchemaExtension`] into the `config` schema document.
pub(crate) fn extend_config(config: &mut serde_json::Value) {
    let Some(map) = config.as_object_mut() else {
        return;
    };
    for ext in inventory::iter::<SchemaExtension> {
        let extra = (ext.render)();
        tracing::debug!("schema extension merged");
        merge_object(map, &extra, "properties");
        merge_object(map, &extra, "$defs");
    }
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
        // frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
        let mut config = gob_config::schema(&refs);
        extend_config(&mut config);
        Ok(Payload::new(SchemaData {
            envelope: envelope_schema(),
            config,
        })
        .with_already(false))
    }
}
