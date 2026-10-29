//! The dotenv-template adapter (fidelity F1): `KEY=value` entries and `#` comments.
//!
//! Only template files are claimed (`is_dotenv_template_path`): a real `.env` holds secrets and is
//! never read as source, so the path test requires an `.example`, `.sample` or `.template` suffix.
//!
//! # Mapping (rho)
//!
//! - The document is `unit(file, impl)`; each `KEY=value` line (optionally `export KEY=value`) is a
//!   `unit(entry, impl)` named by the key, spanning the line. The first definition of a key wins.
//! - Blank lines, `#` comments and lines that are not `KEY=value` are skipped.

// frob:ticket 01M4KHD7774ZV3YECPVCGE2RGD

use std::sync::Arc;

use gob_ir::{NodeSpec, Operator, ScopeGraph};
use gob_languages::{ParseLimits, UnresolvedReason};

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
    ParseStatus,
};
use crate::fold::{Cx, base_file, failed_file, file_root_spec};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, Naming};

/// Suffixes that mark a dotenv file as a template with placeholder values.
const TEMPLATE_SUFFIXES: [&str; 3] = [".example", ".sample", ".template"];

/// True for dotenv templates (`.env.example`, `.env.production.sample`, `app.env.template`); never a real `.env`.
#[must_use]
pub fn is_dotenv_template_path(path: &str) -> bool {
    let name = path.rsplit(['/', '\\']).next().unwrap_or(path);
    let lower = name.to_ascii_lowercase();
    let Some(suffix) = TEMPLATE_SUFFIXES.iter().find(|s| lower.ends_with(**s)) else {
        return false;
    };
    let stem = &lower[..lower.len() - suffix.len()];
    stem.starts_with(".env") || stem.rsplit('.').next() == Some("env")
}

/// The dotenv-template adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct DotenvAdapter;

impl Adapter for DotenvAdapter {
    fn language(&self) -> &'static str {
        "dotenv"
    }

    fn identity(&self) -> String {
        format!("gob-symbols/dotenv/v{EXTRACTOR_VERSION}")
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F1
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Dotenv)
    }

    fn parse(&self, text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Source(Arc::from(text))
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Source(text) => fold_text(text, input),
            _ => failed_file(input, "dotenv", UnresolvedReason::GrammarUnavailable),
        }
    }
}

/// One `KEY=value` line: the key and the byte extent of the line.
#[derive(Debug, PartialEq, Eq)]
struct Entry {
    key: String,
    start: usize,
    end: usize,
}

/// True when `key` is a plausible variable name (`[A-Za-z_][A-Za-z0-9_.]*`).
fn is_key(key: &str) -> bool {
    let mut chars = key.chars();
    chars
        .next()
        .is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '.')
}

/// Scans `text` for `KEY=value` entries, skipping comments, blanks and malformed lines.
fn entries(text: &str) -> Vec<Entry> {
    let mut out: Vec<Entry> = Vec::new();
    let mut offset = 0;
    for raw in text.split_inclusive('\n') {
        let start = offset;
        offset += raw.len();
        let line = raw.trim_end_matches(['\n', '\r']);
        let content = line.trim();
        if content.is_empty() || content.starts_with('#') {
            continue;
        }
        let content = content
            .strip_prefix("export ")
            .unwrap_or(content)
            .trim_start();
        let Some((key, _)) = content.split_once('=') else {
            tracing::trace!(line = start, "dotenv: line without `=` skipped");
            continue;
        };
        let key = key.trim();
        if !is_key(key) || out.iter().any(|e| e.key == key) {
            tracing::trace!(key, "dotenv: invalid or repeated key skipped");
            continue;
        }
        out.push(Entry {
            key: key.to_owned(),
            start,
            end: start + line.trim_end().len(),
        });
    }
    out
}

/// Folds a dotenv template into one `entry` unit per key.
fn fold_text(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, "dotenv", text);
    let found = entries(text);
    let mut units = Vec::new();
    for e in &found {
        let loc = cx.loc(e.start, e.end);
        let body = cx.add(
            NodeSpec::new(Operator::lit("text", &text[e.start..e.end]), loc.clone()),
            &[],
        )?;
        units.push(cx.add(
            NodeSpec::new(Operator::unit("entry", "impl"), loc).named(&e.key),
            &[body],
        )?);
    }
    let root = cx.add(file_root_spec(&cx, input.size as usize), &units)?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "dotenv");
    file.fidelity = Fidelity::F1;
    file.parse_status = ParseStatus::Complete;
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(path = input.path, entries = found.len(), "dotenv folded");
    Ok(Folded { term, scopes, file })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-symbols/src/dotenv.rs::is_dotenv_template_path
    #[test]
    fn claims_templates_only() {
        assert!(is_dotenv_template_path(".env.example"));
        assert!(is_dotenv_template_path("svc/.env.sample"));
        assert!(is_dotenv_template_path(".env.production.template"));
        assert!(is_dotenv_template_path("app.env.example"));
        assert!(!is_dotenv_template_path(".env"));
        assert!(!is_dotenv_template_path(".env.local"));
        assert!(!is_dotenv_template_path("notes.example"));
        assert!(!is_dotenv_template_path("README.md"));
    }

    // frob:tests crates/gob-symbols/src/dotenv.rs::entries
    #[test]
    fn reads_keys_and_skips_comments() {
        let e = entries(
            "# db\nDB_URL=postgres://user:pass@host/db\n\nexport API_KEY=changeme\nbad line\nDB_URL=again\n",
        );
        let keys: Vec<&str> = e.iter().map(|e| e.key.as_str()).collect();
        assert_eq!(keys, ["DB_URL", "API_KEY"]);
        assert_eq!(e[0].start, 5);
    }
}
