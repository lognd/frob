//! The reasoned-divergence list: which replayed steps may differ from the Python golden, and why.

use serde::Deserialize;

use crate::replay::{Diff, Field};

/// One class of difference: the steps it covers, the field, and the reason.
#[derive(Debug, Deserialize)]
pub struct Entry {
    /// A short name for the class.
    pub id: String,
    /// The field that differs.
    pub field: Field,
    /// Step ids (`<group>/<scenario>#<NN>`).
    pub steps: Vec<String>,
    /// Why the Rust crunk differs.
    pub reason: String,
}

#[derive(Deserialize)]
struct File {
    divergence: Vec<Entry>,
}

/// Every divergence entry, parsed from `divergences.toml`.
pub fn load() -> Vec<Entry> {
    let file: File = toml::from_str(include_str!("divergences.toml")).expect("divergences.toml");
    file.divergence
}

/// Problems for `scenario`: differences not listed, and listed differences that did not occur.
pub fn judge(scenario: &str, diffs: &[Diff]) -> Vec<String> {
    let entries = load();
    let mut problems = Vec::new();
    for diff in diffs {
        let listed = entries
            .iter()
            .any(|e| e.field == diff.field && e.steps.contains(&diff.id));
        if !listed {
            problems.push(format!(
                "unlisted {} difference at {} ({})",
                diff.field.name(),
                diff.id,
                diff.what
            ));
        }
    }
    let prefix = format!("{scenario}#");
    for entry in &entries {
        for step in entry.steps.iter().filter(|s| s.starts_with(&prefix)) {
            if !diffs
                .iter()
                .any(|d| &d.id == step && d.field == entry.field)
            {
                problems.push(format!(
                    "stale divergence {} at {step}: no {} difference any more",
                    entry.id,
                    entry.field.name()
                ));
            }
        }
    }
    problems
}
