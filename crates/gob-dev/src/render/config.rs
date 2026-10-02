//! `docs/reference/config.md`: one section per config table.

use gob_config::{TableDescription, all_tables};

use super::{cell, md_header};
use crate::files::GenFile;

/// Render the config reference from `tables`.
pub fn render(tables: &[TableDescription]) -> String {
    let mut sorted: Vec<&TableDescription> = tables.iter().collect();
    sorted.sort_by(|a, b| a.table.cmp(&b.table));
    let mut out = md_header("config");
    out.push_str(
        "\n# Configuration reference\n\n\
         Knobs marked `enforcement` change what the tool enforces. Tables marked \
         materialized must be written out with their defaults in the product config \
         file (`config sync` adds missing knobs; rule CFG001 flags absent ones).\n",
    );
    for t in sorted {
        out.push_str(&format!("\n## `[{}]`\n\n", t.table));
        if !t.doc.trim().is_empty() {
            out.push_str(&format!("{}\n\n", t.doc.trim()));
        }
        out.push_str(&format!(
            "Materialized: {}.\n\n",
            if t.materialize { "yes" } else { "no" }
        ));
        out.push_str("| Key | Type | Default | Enforcement | Doc |\n|---|---|---|---|---|\n");
        let mut fields: Vec<_> = t.fields.iter().collect();
        fields.sort_by(|a, b| a.key.cmp(&b.key));
        for f in fields {
            out.push_str(&format!(
                "| `{}` | `{}` | `{}` | {} | {} |\n",
                f.key,
                f.type_name.replace('|', "\\|"),
                cell(&f.default_toml),
                if f.enforcement { "yes" } else { "no" },
                cell(&f.doc),
            ));
        }
    }
    out
}

/// The config reference for the global inventory.
pub fn generate() -> Vec<GenFile> {
    let tables: Vec<TableDescription> = all_tables().collect();
    vec![GenFile {
        path: "docs/reference/config.md".to_owned(),
        content: render(&tables),
    }]
}
