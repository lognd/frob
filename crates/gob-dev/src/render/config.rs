//! Config reference pages: `docs/reference/config.md` for frob, `docs/<product>/config.md` for each other product.
// frob:ticket 01M43MPG53JR8TP0E15394FZ5T

use gob_config::{TableDescription, product_entry, product_tables, products};

use super::{cell, md_header};
use crate::files::GenFile;

/// The product whose page lives at the historic `docs/reference/config.md`.
const FRONT_PRODUCT: &str = gob_config::DEFAULT_PRODUCT;

/// Repo-relative path of `product`'s config reference page.
pub fn page_path(product: &str) -> String {
    if product == FRONT_PRODUCT {
        "docs/reference/config.md".to_owned()
    } else {
        format!("docs/{product}/config.md")
    }
}

/// Section heading of a table: `[x]`, or `[[x]]` for an array of tables.
fn heading(t: &TableDescription) -> String {
    if t.array {
        format!("[[{}]]", t.table)
    } else {
        format!("[{}]", t.table)
    }
}

/// Render the config reference of `product` from its `tables`.
pub fn render(product: &str, tables: &[TableDescription]) -> String {
    let front = product == FRONT_PRODUCT;
    let mut sorted: Vec<&TableDescription> = tables.iter().collect();
    sorted.sort_by(|a, b| a.table.cmp(&b.table));
    let mut out = md_header("config");
    if front {
        out.push_str(
            "\n# Configuration reference\n\n\
             Knobs marked `enforcement` change what the tool enforces. Tables marked \
             materialized must be written out with their defaults in the product config \
             file (`config sync` adds missing knobs; rule CFG001 flags absent ones).\n",
        );
    } else {
        let entry = product_entry(product);
        let title = entry.map_or_else(|| format!("{product}.toml"), |e| e.title.to_owned());
        out.push_str(&format!("\n# {title} reference\n\n"));
        if let Some(entry) = entry {
            out.push_str(entry.intro.trim());
            out.push('\n');
        }
    }
    for t in sorted {
        out.push_str(&format!("\n## `{}`\n\n", heading(t)));
        if !t.doc.trim().is_empty() {
            out.push_str(&format!("{}\n\n", t.doc.trim()));
        }
        if front {
            out.push_str(&format!(
                "Materialized: {}.\n\n",
                if t.materialize { "yes" } else { "no" }
            ));
            out.push_str("| Key | Type | Default | Enforcement | Doc |\n|---|---|---|---|---|\n");
        } else {
            out.push_str("| Key | Type | Required | Default | Doc |\n|---|---|---|---|---|\n");
        }
        let mut fields: Vec<_> = t.fields.iter().collect();
        fields.sort_by(|a, b| a.key.cmp(&b.key));
        for f in fields {
            let ty = f.type_name.replace('|', "\\|");
            if front {
                out.push_str(&format!(
                    "| `{}` | `{ty}` | `{}` | {} | {} |\n",
                    f.key,
                    cell(&f.default_toml),
                    if f.enforcement { "yes" } else { "no" },
                    cell(&f.doc),
                ));
            } else {
                let default = if f.default_toml.is_empty() {
                    "-".to_owned()
                } else {
                    format!("`{}`", cell(&f.default_toml))
                };
                out.push_str(&format!(
                    "| `{}` | `{ty}` | {} | {default} | {} |\n",
                    f.key,
                    if f.required { "yes" } else { "no" },
                    cell(&f.doc),
                ));
            }
        }
        if let Some(rest) = &t.rest {
            out.push_str(&format!(
                "| any other key | `{}` | no | - | {} |\n",
                rest.type_name.replace('|', "\\|"),
                cell(&rest.doc),
            ));
        }
    }
    out
}

/// One config reference page per product that registered tables.
pub fn generate() -> Vec<GenFile> {
    products()
        .into_iter()
        .map(|product| {
            let tables: Vec<TableDescription> = product_tables(&product).collect();
            tracing::debug!(%product, tables = tables.len(), "rendering config page");
            GenFile {
                path: page_path(&product),
                content: render(&product, &tables),
            }
        })
        .collect()
}
