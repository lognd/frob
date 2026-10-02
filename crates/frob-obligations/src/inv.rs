//! INV001 (invariant documents without an anchor) and INV002 (forbidden imports).

use std::collections::BTreeSet;
use std::path::Path;

use globset::Glob;
use gob_directives::DirectiveRecord;
use gob_rules::{Finding, Severity};
use gob_symbols::{ImportEdge, SymbolGraph, Target};
use gob_text::{FileInterner, Span};

use crate::config::{ForbidImport, InvariantsConfig};
use crate::rules::{Inv001, Inv002};
use crate::todo::range;
use crate::util::{finding, rule_id};

/// The slug of `invariants/<slug>.md`, when `path` has that shape.
fn invariant_slug(path: &str) -> Option<&str> {
    let name = path.strip_prefix("invariants/")?;
    (!name.contains('/')).then_some(())?;
    name.strip_suffix(".md")
}

/// INV001 over the repo: invariant documents no `frob:invariant` directive names.
pub(crate) fn inv001(
    graph: &SymbolGraph,
    directives: &[DirectiveRecord],
    files: &mut FileInterner,
) -> Vec<Finding> {
    let named: BTreeSet<&str> = directives
        .iter()
        .filter(|d| d.namespace == "frob" && d.verb == "invariant")
        .filter_map(|d| d.args.positional.first().map(|t| t.value.as_str()))
        .collect();
    let mut out = Vec::new();
    for rec in graph
        .records()
        .filter(|r| matches!(r.symref.target(), Target::File))
    {
        let path = rec.symref.path();
        let Some(slug) = invariant_slug(path) else {
            continue;
        };
        if named.contains(slug) {
            continue;
        }
        let file = files.intern(path);
        out.push(finding(
            &Inv001,
            Some(Span::new(file, range(0, 0))),
            format!("invariant `{slug}` has no `frob:invariant {slug}` directive in code"),
            path,
        ));
    }
    out
}

/// `-` and `_` are equivalent in crate names.
fn norm(s: &str) -> String {
    s.replace('-', "_")
}

/// True when import `target` equals `to` or lies under it (`::` boundary).
fn under(target: &str, to: &str) -> bool {
    let (t, p) = (norm(target), norm(to));
    t == p || t.strip_prefix(&p).is_some_and(|r| r.starts_with("::"))
}

/// True when `from` is a bare crate directory name rather than a glob.
fn is_crate_name(from: &str) -> bool {
    !from.contains(['/', '*', '?', '[', '{'])
}

/// A compiled `from` matcher.
enum Matcher {
    /// A directory named so anywhere in the path.
    Crate(String),
    /// A path glob.
    Glob(globset::GlobMatcher),
}

impl Matcher {
    fn compile(from: &str) -> Result<Self, globset::Error> {
        if is_crate_name(from) {
            return Ok(Self::Crate(from.to_owned()));
        }
        Ok(Self::Glob(Glob::new(from)?.compile_matcher()))
    }

    fn matches(&self, path: &str) -> bool {
        match self {
            Self::Crate(name) => path.split('/').rev().skip(1).any(|c| c == name),
            Self::Glob(g) => g.is_match(path),
        }
    }
}

/// The byte range of the first `use` line of `text` that mentions both ends of `target`.
fn locate(text: &str, target: &str) -> (usize, usize) {
    let first = target.split("::").next().unwrap_or(target);
    let last = target.rsplit("::").next().unwrap_or(target);
    let mut offset = 0;
    for line in text.split_inclusive('\n') {
        let t = line.trim_start();
        let lead = line.len() - t.len();
        if (t.starts_with("use ") || t.starts_with("pub use "))
            && t.contains(first)
            && (last == "*" || t.contains(last))
        {
            return (offset + lead, t.trim_end().len());
        }
        offset += line.len();
    }
    (0, 0)
}

/// INV002 over the repo: imports matching a `forbid_imports` entry.
pub(crate) fn inv002(
    root: &Path,
    graph: &SymbolGraph,
    config: &InvariantsConfig,
    files: &mut FileInterner,
) -> Vec<Finding> {
    let mut out = Vec::new();
    let mut rules: Vec<(&ForbidImport, Matcher)> = Vec::new();
    for (i, entry) in config.forbid_imports.iter().enumerate() {
        match Matcher::compile(&entry.from) {
            Ok(m) => rules.push((entry, m)),
            Err(err) => {
                tracing::warn!(index = i, from = %entry.from, %err, "forbid_imports glob invalid");
                out.push(Finding::new(
                    rule_id(&Inv002),
                    Severity::Unresolved,
                    None,
                    format!(
                        "[invariants] forbid_imports entry {i}: `from = {}` is not a valid glob ({err})",
                        entry.from
                    ),
                    &format!("forbid_imports[{i}]"),
                ));
            }
        }
    }
    let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
    for ImportEdge { from_file, target } in graph.imports() {
        for (entry, from) in &rules {
            if !from.matches(from_file) || !under(target, &entry.to) {
                continue;
            }
            if !seen.insert((from_file.clone(), target.clone())) {
                continue;
            }
            let (start, len) = std::fs::read_to_string(root.join(from_file))
                .map_or((0, 0), |t| locate(&t, target));
            let file = files.intern(from_file);
            tracing::debug!(file = %from_file, import = %target, "forbidden import");
            out.push(finding(
                &Inv002,
                Some(Span::new(file, range(start, len))),
                format!(
                    "`{from_file}` imports `{target}`, forbidden by [invariants] ({}): {}",
                    entry.to, entry.reason
                ),
                &format!("{from_file}->{target}"),
            ));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugs_only_for_top_level_invariant_documents() {
        assert_eq!(invariant_slug("invariants/INV-1.md"), Some("INV-1"));
        assert_eq!(invariant_slug("invariants/sub/a.md"), None);
        assert_eq!(invariant_slug("docs/a.md"), None);
    }

    #[test]
    fn prefixes_respect_boundaries_and_hyphens() {
        assert!(under("gob_rules::Finding", "gob-rules"));
        assert!(under("gob_rules", "gob-rules"));
        assert!(!under("gob_rules_extra::x", "gob-rules"));
    }

    #[test]
    fn crate_names_match_directories_not_files() {
        let m = Matcher::compile("gob-text").unwrap();
        assert!(m.matches("crates/gob-text/src/a.rs"));
        assert!(!m.matches("crates/other/gob-text"));
        let g = Matcher::compile("crates/*/src/**").unwrap();
        assert!(g.matches("crates/x/src/a.rs"));
    }
}
