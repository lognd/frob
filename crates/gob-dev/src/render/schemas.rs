//! `docs/schemas/*.json`: envelope, config and directive schemas.

use gob_config::{TableDescription, all_tables, schema};
use gob_directives::all_directives;
use serde_json::{Map, Value, json};

use super::json_file;
use crate::files::GenFile;

/// The directive schema document: one `$defs` entry per `namespace:verb`.
pub fn directives_schema() -> Value {
    let mut defs = Map::new();
    let mut metas: Vec<_> = all_directives().collect();
    metas.sort_by_key(|m| (m.namespace, m.verb));
    let mut one_of = Vec::new();
    for m in metas {
        let key = m.qualified();
        one_of.push(json!({ "$ref": format!("#/$defs/{key}") }));
        defs.insert(key, m.json_schema().into());
    }
    json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "frob directives",
        "oneOf": one_of,
        "$defs": defs,
    })
}

/// The three schema files for the global inventories.
pub fn generate() -> Vec<GenFile> {
    let tables: Vec<TableDescription> = {
        let mut t: Vec<_> = all_tables().collect();
        t.sort_by(|a, b| a.table.cmp(&b.table));
        t
    };
    let refs: Vec<&TableDescription> = tables.iter().collect();
    vec![
        GenFile {
            path: "docs/schemas/envelope.json".to_owned(),
            content: json_file("schemas", gob_diagnostics::envelope_schema()),
        },
        GenFile {
            path: "docs/schemas/config.json".to_owned(),
            content: json_file("schemas", schema(&refs)),
        },
        GenFile {
            path: "docs/schemas/directives.json".to_owned(),
            content: json_file("schemas", directives_schema()),
        },
    ]
}
