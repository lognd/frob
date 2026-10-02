//! `docs/reference/directives.md`: one section per `namespace:verb`.

use gob_directives::{ArgKind, ArgMeta, DirectiveMeta, all_directives};

use super::{cell, md_header};
use crate::files::GenFile;

/// Human name of an argument kind.
fn kind_name(k: ArgKind) -> &'static str {
    match k {
        ArgKind::Str => "string",
        ArgKind::U32 => "integer",
        ArgKind::Bool => "boolean",
    }
}

/// How an argument is written in a directive.
fn form(a: &ArgMeta) -> String {
    let name = a.key.unwrap_or(a.name);
    match (a.positional, a.list) {
        (true, true) => format!("`<{name}>...`"),
        (true, false) => format!("`<{name}>`"),
        (false, true) => format!("`{name}=<v>` (repeatable)"),
        (false, false) => format!("`{name}=<v>`"),
    }
}

/// Render the directive reference from `metas`.
pub fn render(metas: &[&DirectiveMeta]) -> String {
    let mut sorted: Vec<&DirectiveMeta> = metas.to_vec();
    sorted.sort_by_key(|m| (m.namespace, m.verb));
    let mut out = md_header("directives");
    out.push_str("\n# Directives\n");
    for m in sorted {
        out.push_str(&format!(
            "\n## `{}`\n\n{}\n",
            m.qualified(),
            m.summary.trim()
        ));
        if m.args.is_empty() {
            out.push_str("\nTakes no arguments.\n");
            continue;
        }
        out.push_str("\n| Argument | Form | Type | Required | Summary |\n|---|---|---|---|---|\n");
        for a in m.args {
            out.push_str(&format!(
                "| {} | {} | {} | {} | {} |\n",
                a.name,
                form(a),
                kind_name(a.kind),
                if a.optional || a.list { "no" } else { "yes" },
                cell(a.summary),
            ));
        }
    }
    out
}

/// The directive reference for the global inventory.
pub fn generate() -> Vec<GenFile> {
    let metas: Vec<&DirectiveMeta> = all_directives().collect();
    vec![GenFile {
        path: "docs/reference/directives.md".to_owned(),
        content: render(&metas),
    }]
}
