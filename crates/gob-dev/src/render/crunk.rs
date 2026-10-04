//! `docs/crunk/config.md` and `docs/schemas/crunk.json`: the `crunk.toml` reference and schema.
//!
//! Both come from `crunk-spec`'s TOML-shaped table types, which are deliberately not registered
//! in the global config inventory: `crunk.toml` keys have no business in frob's reference.

use super::{json_file, md_header};
use crate::files::GenFile;

/// The `crunk.toml` reference page.
pub fn generate_config() -> Vec<GenFile> {
    let mut content = md_header("config");
    content.push_str(&crunk_spec::schema::reference());
    vec![GenFile {
        path: "docs/crunk/config.md".to_owned(),
        content,
    }]
}

/// The `crunk.toml` JSON Schema.
pub fn generate_schemas() -> Vec<GenFile> {
    vec![GenFile {
        path: "docs/schemas/crunk.json".to_owned(),
        content: json_file("schemas", crunk_spec::schema::schema()),
    }]
}
