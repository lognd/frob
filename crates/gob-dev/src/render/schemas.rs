//! `docs/schemas/*.json`: envelope, config, directive and issue-projection schemas.

use gob_config::products;
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

/// Repo-relative path of `product`'s config schema.
pub fn schema_path(product: &str) -> String {
    if product == gob_config::DEFAULT_PRODUCT {
        "docs/schemas/config.json".to_owned()
    } else {
        format!("docs/schemas/{product}.json")
    }
}

/// The schema files for the global inventories.
pub fn generate(frob: &crate::products::FrobProduct) -> Vec<GenFile> {
    let mut files = vec![
        GenFile {
            path: "docs/schemas/envelope.json".to_owned(),
            content: json_file("schemas", gob_diagnostics::envelope_schema()),
        },
        GenFile {
            path: "docs/schemas/directives.json".to_owned(),
            content: json_file("schemas", directives_schema()),
        },
        // frob:ticket 01M3ZX836BNV9H9K9ZCKNMAEDB
        GenFile {
            path: "docs/schemas/issue-projection.json".to_owned(),
            content: json_file("schemas", (frob.issue_schema)()),
        },
    ];
    for product in products() {
        files.push(GenFile {
            path: schema_path(&product),
            content: json_file("schemas", gob_config::product_config_schema(&product)),
        });
    }
    files
}
