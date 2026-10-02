//! `docs/reference/cli/<product>.md`: verb tables from the command inventory.

use std::collections::BTreeMap;

use gob_cli::{CommandMeta, ExitCode, all_commands};

use super::{cell, md_header};
use crate::files::GenFile;

/// `code name` for an exit code, for example `1 negative`.
fn exit_label(e: ExitCode) -> String {
    let name = match e {
        ExitCode::Ok => "ok",
        ExitCode::Negative => "negative",
        ExitCode::Usage => "usage",
        ExitCode::Refused => "refused",
        ExitCode::Internal => "internal",
    };
    format!("{} {name}", e.code())
}

/// Render one product's verb table.
pub fn render_product(product: &str, verbs: &[&CommandMeta]) -> String {
    let mut sorted = verbs.to_vec();
    sorted.sort_by_key(|m| m.verb);
    let mut out = md_header("cli");
    out.push_str(&format!("\n# `{product}` commands\n\n"));
    out.push_str("| Verb | Idempotent | Dry run | Exits | Summary |\n|---|---|---|---|---|\n");
    for m in sorted {
        let exits: Vec<String> = m.exits.iter().map(|e| exit_label(*e)).collect();
        out.push_str(&format!(
            "| `{}` | {} | {} | {} | {} |\n",
            m.verb,
            if m.idempotent { "yes" } else { "no" },
            if m.dry_run { "yes" } else { "no" },
            cell(&exits.join(", ")),
            cell(m.summary),
        ));
    }
    out
}

/// One page per product for the global inventory.
pub fn generate() -> Vec<GenFile> {
    let mut by_product: BTreeMap<&str, Vec<&CommandMeta>> = BTreeMap::new();
    for m in all_commands() {
        by_product.entry(m.product).or_default().push(m);
    }
    by_product
        .into_iter()
        .map(|(product, verbs)| GenFile {
            path: format!("docs/reference/cli/{product}.md"),
            content: render_product(product, &verbs),
        })
        .collect()
}
