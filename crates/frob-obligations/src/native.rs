//! EXC017: native suppressions of rules bound through a `[[check.tool]]` stage.

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4

use std::collections::BTreeMap;
use std::path::Path;

use gob_check::{CheckTable, ToolStage};
use gob_languages::Language;
use gob_rules::{BoundException, ExceptionCtx, Finding, RuleId};
use gob_symbols::{SymbolGraph, Target};
use gob_text::{FileInterner, Span};

use crate::rules::Exc017;
use crate::todo::range;
use crate::util::finding;

/// Largest file `EXC017` reads; bigger files are skipped as generated.
const MAX_BYTES: u64 = 2 * 1024 * 1024;

/// The tool id to frob rule id pairs that the `id_map` of `stages` bind.
fn bound_ids(stages: &[ToolStage]) -> BTreeMap<String, RuleId> {
    let mut out = BTreeMap::new();
    for stage in stages.iter().map(ToolStage::resolved) {
        for (tool_id, target) in &stage.id_map {
            match target.parse::<RuleId>() {
                Ok(rule) => {
                    out.insert(tool_id.clone(), rule);
                }
                Err(err) => {
                    tracing::warn!(stage = %stage.name, tool_id, %err, "id_map target is not a rule id");
                }
            }
        }
    }
    out
}

/// The tool-bound ids of the `[check]` table of the repository at `root`, empty when it cannot be read.
///
/// Only ids a stage names in its `id_map` count as bound; a parser's built-in
/// map is private to `gob-check` and is not consulted.
pub fn tool_bound_ids(root: &Path) -> BTreeMap<String, RuleId> {
    match CheckTable::load(root, "frob") {
        Ok(table) => bound_ids(&table.tool),
        Err(err) => {
            tracing::warn!(%err, "[check] unreadable; EXC017 has no bound tool ids");
            BTreeMap::new()
        }
    }
}

/// One native suppression comment or attribute and the tool ids it names.
#[derive(Debug, PartialEq, Eq)]
struct Suppression {
    /// Byte offset of the start of the line.
    offset: usize,
    /// Length of the line in bytes.
    len: usize,
    /// The tool ids the suppression names.
    ids: Vec<String>,
}

/// The ids in the first `open ... close` group of `text` after `marker`, split on commas.
fn group<'t>(text: &'t str, marker: &str, open: char, close: char) -> Option<Vec<&'t str>> {
    let rest = &text[text.find(marker)? + marker.len()..];
    let rest = rest.strip_prefix(open)?;
    let inner = &rest[..rest.find(close)?];
    Some(
        inner
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty() && !s.contains('='))
            .collect(),
    )
}

/// The ids an `eslint-disable` comment lists (before any `--` reason).
fn eslint_ids(line: &str) -> Vec<&str> {
    let Some(at) = line.find("eslint-disable") else {
        return Vec::new();
    };
    let rest = &line[at + "eslint-disable".len()..];
    let rest = rest
        .strip_prefix("-next-line")
        .or_else(|| rest.strip_prefix("-line"))
        .unwrap_or(rest);
    let rest = rest.split("--").next().unwrap_or(rest);
    let rest = rest.split("*/").next().unwrap_or(rest);
    rest.split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect()
}

/// Every native suppression in `text`, one per line, in source order.
fn scan(text: &str) -> Vec<Suppression> {
    let mut out = Vec::new();
    let mut offset = 0;
    for raw in text.split_inclusive('\n') {
        let line = raw.trim_end_matches(['\n', '\r']);
        let t = line.trim_start();
        let ids: Vec<&str> = if t.starts_with("#[") || t.starts_with("#![") {
            ["allow", "expect"]
                .iter()
                .find_map(|k| group(t, k, '(', ')'))
                .unwrap_or_default()
        } else if let Some(i) = line.find("zizmor: ignore") {
            group(&line[i..], "zizmor: ignore", '[', ']').unwrap_or_default()
        } else if line.contains("eslint-disable") {
            eslint_ids(line)
        } else {
            Vec::new()
        };
        if !ids.is_empty() {
            out.push(Suppression {
                offset,
                len: line.len(),
                ids: ids.into_iter().map(str::to_owned).collect(),
            });
        }
        offset += raw.len();
    }
    out
}

/// True when `b` of the mapped rule binds to the item that starts right below the suppression line `s`.
///
/// An attribute sits above its item and may fall outside the item's bound range, so an
/// exception whose range starts after the line, with only attribute or blank lines between, guards it.
fn guards_next_item(
    b: &BoundException,
    rule: &RuleId,
    path: &str,
    s: &Suppression,
    text: &str,
) -> bool {
    let (Some(r), true) = (&b.range, b.path == path && b.exception.rule == *rule) else {
        return false;
    };
    let end = s.offset + s.len;
    r.start >= end
        && text.get(end..r.start).is_some_and(|gap| {
            gap.lines()
                .all(|l| l.trim().is_empty() || l.trim_start().starts_with("#["))
        })
}

/// EXC017 over the repository: suppressions of `bound` ids with no covering exception in `exceptions`.
pub(crate) fn exc017(
    root: &Path,
    graph: &SymbolGraph,
    files: &mut FileInterner,
    bound: &BTreeMap<String, RuleId>,
    exceptions: &[BoundException],
) -> Vec<Finding> {
    if bound.is_empty() {
        return Vec::new();
    }
    let paths: Vec<String> = graph
        .records()
        .filter(|r| matches!(r.symref.target(), Target::File))
        .map(|r| r.symref.path().to_owned())
        .collect();
    let mut out = Vec::new();
    for path in paths {
        if Language::detect(&path).is_none()
            || Path::new(&path)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("md"))
        {
            continue;
        }
        let full = root.join(&path);
        if std::fs::metadata(&full).map_or(true, |m| m.len() > MAX_BYTES) {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&full) else {
            continue;
        };
        let file = files.intern(&path);
        for s in scan(&text) {
            for id in &s.ids {
                let Some(rule) = bound.get(id) else { continue };
                let probe = Finding::new(
                    rule.clone(),
                    gob_rules::Severity::Warn,
                    Some(Span::new(file, range(s.offset, s.len))),
                    "probe",
                    &path,
                );
                let ctx = ExceptionCtx { files };
                if exceptions
                    .iter()
                    .any(|b| b.covers(&probe, &ctx) || guards_next_item(b, rule, &path, &s, &text))
                {
                    continue;
                }
                tracing::debug!(path, id, %rule, "native suppression without exception");
                out.push(finding(
                    &Exc017,
                    probe.span,
                    format!(
                        "native suppression of `{id}` hides {rule} from frob; add `frob:accept {rule} because=\"...\"` or `frob:defer {rule}` at this site"
                    ),
                    &format!("{path}:{id}"),
                ));
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/frob-obligations/src/native.rs::scan
    #[test]
    fn finds_rust_zizmor_and_eslint_suppressions() {
        let text = "#[allow(clippy::a, reason = \"x\")]\nfn f() {}\n  # zizmor: ignore[unpinned-uses, artipacked]\n// eslint-disable-next-line no-eval, no-var -- why\nlet x = 1; // plain\n";
        let found = scan(text);
        let ids: Vec<Vec<&str>> = found
            .iter()
            .map(|s| s.ids.iter().map(String::as_str).collect())
            .collect();
        assert_eq!(
            ids,
            vec![
                vec!["clippy::a"],
                vec!["unpinned-uses", "artipacked"],
                vec!["no-eval", "no-var"]
            ]
        );
        assert_eq!(found[1].offset, text.find("  # zizmor").unwrap());
    }

    #[test]
    fn only_id_map_targets_are_bound() {
        let mut stage = ToolStage {
            name: "x".to_owned(),
            def: None,
            command: "x".to_owned(),
            args: Vec::new(),
            timeout_secs: 5,
            fail_on_nonzero: true,
            parser: gob_check::ToolParser::None,
            labels: Vec::new(),
            id_map: BTreeMap::new(),
            min_version: None,
            max_version: None,
            version_args: None,
            optional: false,
            inputs: Vec::new(),
            tier: gob_check::ToolTier::Ticket,
            unscoped_packages: Vec::new(),
        };
        stage.id_map.insert("a".into(), "CI001".into());
        stage.id_map.insert("b".into(), "not a rule".into());
        let bound = bound_ids(&[stage]);
        assert_eq!(bound.len(), 1);
        assert_eq!(bound["a"].as_str(), "CI001");
    }
}
