//! Reads the `model` text of a GRL example into node rows, for gob-plan's example runner.
//!
//! gob-plan sits below `grimble-model`, so this crate (which has both) supplies the reader and
//! the grimble binary installs it at startup.

// frob:ticket 01M5FRCMBS9DHQ223JWGN6RNW7
use gob_plan::examples::ModelNodeRow;
use grimble_model::ast::{ClauseKind, EntityKind, Item};

/// The path an example `model` text is read as.
const EXAMPLE_MODEL_PATH: &str = "example.grmb";
/// The version header and module line an example `model` without one is read under.
const MODEL_HEADER: &str = "grimble = \"2\";\nmodule example;";
/// The kind of a model node that declares none.
const DEFAULT_NODE_KIND: &str = "component";

/// Pushes the node rows of `items`, namespaces joined with `.`.
fn model_items(items: &[Item], ns: &str, rows: &mut Vec<ModelNodeRow>) {
    for item in items {
        match item {
            Item::Namespace(n) => {
                let inner = format!("{ns}{}.", n.name.text);
                model_items(&n.items, &inner, rows);
            }
            Item::Entity(e) if e.kind == EntityKind::Node && !e.extension => {
                let kind = e
                    .clauses
                    .iter()
                    .find_map(|c| match &c.kind {
                        ClauseKind::Kind(k) => Some(k.text.as_str()),
                        _ => None,
                    })
                    .unwrap_or(DEFAULT_NODE_KIND);
                let selectors = e
                    .clauses
                    .iter()
                    .filter_map(|c| match &c.kind {
                        ClauseKind::Owns(sel) => Some(sel.text.clone()),
                        _ => None,
                    })
                    .collect();
                let grants = e
                    .clauses
                    .iter()
                    .filter_map(|c| match &c.kind {
                        ClauseKind::May(m) if m.at.is_none() => Some(m.atom.name.clone()),
                        _ => None,
                    })
                    .collect();
                let excuses = e
                    .clauses
                    .iter()
                    .filter_map(|c| match &c.kind {
                        ClauseKind::Excuses(x) => Some(x.atom.name.clone()),
                        _ => None,
                    })
                    .collect();
                rows.push(ModelNodeRow {
                    name: format!("{ns}{}", e.name.text),
                    kind: kind.to_owned(),
                    path: EXAMPLE_MODEL_PATH.to_owned(),
                    selectors,
                    grants,
                    excuses,
                });
            }
            _ => {}
        }
    }
}

/// Reads an example's grmb `model` text (the version header is supplied unless the text has
/// one) into node rows.
///
/// # Errors
/// The first syntax diagnostic's message when the text does not parse.
pub fn read_example_model(text: &str) -> Result<Vec<ModelNodeRow>, String> {
    let full = if text.trim_start().starts_with("grimble") {
        text.to_owned()
    } else {
        format!("{MODEL_HEADER}\n{text}")
    };
    let file = grimble_model::parse_file(EXAMPLE_MODEL_PATH, full.as_bytes());
    if file.holes > 0 || !file.diags.is_empty() {
        let first = file
            .diags
            .first()
            .map_or("syntax error", |d| d.message.as_str());
        return Err(first.to_owned());
    }
    let mut rows = Vec::new();
    model_items(&file.items, "", &mut rows);
    Ok(rows)
}
