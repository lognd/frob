//! Live answers for the incompleteness corpus: the real adapters fill the observed column.
//!
//! `docs/design/testing.md` section 8. [`live_verdict`] folds a case's probe source with the
//! registered adapter and reads the capability's answer off the resulting symbol graph;
//! [`live_column`] does so for a whole corpus in corpus order; [`diff_column`] compares it with
//! the committed column and [`rewrite_observed`] regenerates that column in the TOML text,
//! keeping comments and probe sources byte for byte.

// frob:ticket 01M5HGCQ5CDB7HEEFGTRVP9DA6

use std::collections::BTreeMap;
use std::fmt::Write as _;

use gob_symbols::{
    Capability, EdgeKind, FileSymbols, ParseStatus, Status, SymbolGraph, Visibility,
    adapter_for_path, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

use crate::incompleteness::{OracleCase, Verdict};

/// Why a live answer could not be produced (a broken case or an unavailable adapter, never a verdict).
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum LiveError {
    /// The case lacks `file`, `source` or `query`, so no adapter can be asked.
    #[error("E-INCOMPLETE-LIVE-PROBE: case `{0}` needs `file`, `source` and `query`")]
    MissingProbe(String),
    /// No adapter claims the case's file, so the live answer would be a silent Unknown.
    #[error("E-INCOMPLETE-LIVE-ADAPTER: case `{0}`: no adapter claims file `{1}`")]
    NoAdapter(String, String),
    /// The adapter's language differs from the case's `language`.
    #[error("E-INCOMPLETE-LIVE-LANGUAGE: case `{0}`: file `{1}` is read as `{2}`, not `{3}`")]
    LanguageMismatch(String, String, String, String),
    /// The source did not parse at all (too large, timed out, no grammar): not a verdict.
    #[error("E-INCOMPLETE-LIVE-PARSE: case `{0}`: the adapter produced no tree: {1}")]
    ParseFailed(String, String),
    /// The case names a capability the live probe has no reading for.
    #[error("E-INCOMPLETE-LIVE-CAPABILITY: case `{0}`: no live probe for capability `{1}`")]
    NoProbeFor(String, String),
}

/// One committed-versus-live disagreement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Mismatch {
    /// The case id.
    pub id: String,
    /// The answer committed in the corpus.
    pub committed: Verdict,
    /// The answer the real adapter gave now.
    pub live: Verdict,
}

fn probe_of(c: &OracleCase) -> Result<(&str, &str, &str), LiveError> {
    match (&c.file, &c.source, &c.query) {
        (Some(f), Some(s), Some(q)) => Ok((f, s, q)),
        _ => Err(LiveError::MissingProbe(c.id.clone())),
    }
}

/// Whether the last path segment of a symbol or callee spelling equals `query`.
fn names(spelled: &str, query: &str) -> bool {
    spelled == query || spelled.rsplit(['.', ':', '/', '#']).next() == Some(query)
}

fn visibility_verdict(file: &FileSymbols, query: &str) -> Verdict {
    match file
        .symbols
        .iter()
        .find(|r| names(&r.symref.to_string(), query))
        .map(|r| r.visibility)
    {
        Some(Visibility::Public) => Verdict::Yes,
        Some(Visibility::Crate | Visibility::Private) => Verdict::No,
        None => Verdict::Unknown,
    }
}

fn imports_verdict(file: &FileSymbols, query: &str) -> Verdict {
    if !file.parse_status.is_complete() {
        return Verdict::Unknown;
    }
    if file.imports.iter().any(|i| names(&i.target, query)) {
        Verdict::Yes
    } else {
        Verdict::No
    }
}

/// A reference resolves (Yes) only when the graph proves a single target; May and Unknown edges
/// are not decided, and an unbound name may merely be external, so none is ever No.
fn resolve_verdict(file: FileSymbols, query: &str) -> Verdict {
    let graph = SymbolGraph::from_files(vec![file]);
    let proven = graph.edges_with_status().iter().any(|e| {
        e.kind == EdgeKind::Calls
            && e.status == Status::Must
            && e.to.as_ref().is_some_and(|t| names(&t.to_string(), query))
    });
    if proven {
        Verdict::Yes
    } else {
        Verdict::Unknown
    }
}

/// The answer the real adapter gives for one case.
///
/// A capability the adapter's language does not provide is Unknown, as the matrix declares.
///
/// # Errors
/// `MissingProbe`, `NoAdapter`, `LanguageMismatch`, `ParseFailed` or `NoProbeFor`.
pub fn live_verdict(c: &OracleCase) -> Result<Verdict, LiveError> {
    let (path, source, query) = probe_of(c)?;
    let adapter = adapter_for_path(path)
        .ok_or_else(|| LiveError::NoAdapter(c.id.clone(), path.to_owned()))?;
    if adapter.language() != c.language {
        return Err(LiveError::LanguageMismatch(
            c.id.clone(),
            path.to_owned(),
            adapter.language().to_owned(),
            c.language.clone(),
        ));
    }
    let cap = Capability::ALL
        .iter()
        .copied()
        .find(|k| k.name() == c.capability)
        .ok_or_else(|| LiveError::NoProbeFor(c.id.clone(), c.capability.clone()))?;
    let entry = FileEntry {
        path: path.to_owned(),
        size: source.len() as u64,
        digest: Digest::of(source.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let file = extract_file(&entry, source);
    if let ParseStatus::Failed { reason } = &file.parse_status {
        tracing::error!(case = %c.id, %reason, "adapter produced no tree");
        return Err(LiveError::ParseFailed(c.id.clone(), reason.clone()));
    }
    if !adapter.capabilities().precision(cap).is_provided() {
        tracing::debug!(case = %c.id, capability = cap.name(), "capability not provided: Unknown");
        return Ok(Verdict::Unknown);
    }
    let verdict = match cap {
        Capability::Visibility => visibility_verdict(&file, query),
        Capability::Imports => imports_verdict(&file, query),
        Capability::ResolveRef => resolve_verdict(file, query),
        // The corpus asks apply_targets of adapters that do not provide it; a provider needs a probe.
        _ => return Err(LiveError::NoProbeFor(c.id.clone(), c.capability.clone())),
    };
    tracing::debug!(case = %c.id, ?verdict, "live answer");
    Ok(verdict)
}

/// The live answer of every case, in corpus order.
///
/// # Errors
/// The first case's [`LiveError`].
pub fn live_column(cases: &[OracleCase]) -> Result<Vec<(String, Verdict)>, LiveError> {
    cases
        .iter()
        .map(|c| live_verdict(c).map(|v| (c.id.clone(), v)))
        .collect()
}

/// Every case whose committed `observed` differs from its live answer, in corpus order.
pub fn diff_column(cases: &[OracleCase], live: &[(String, Verdict)]) -> Vec<Mismatch> {
    let live: BTreeMap<&str, Verdict> = live.iter().map(|(i, v)| (i.as_str(), *v)).collect();
    cases
        .iter()
        .filter_map(|c| {
            let now = *live.get(c.id.as_str())?;
            (now != c.observed).then(|| Mismatch {
                id: c.id.clone(),
                committed: c.observed,
                live: now,
            })
        })
        .collect()
}

fn spelled(v: Verdict) -> &'static str {
    match v {
        Verdict::Yes => "yes",
        Verdict::No => "no",
        Verdict::Unknown => "unknown",
    }
}

/// Rewrites each case's `observed = ".."` line in the corpus TOML `text` to its live answer.
///
/// Lines inside a `'''` probe source are never touched; comments and layout are kept.
pub fn rewrite_observed(text: &str, live: &[(String, Verdict)]) -> String {
    let live: BTreeMap<&str, Verdict> = live.iter().map(|(i, v)| (i.as_str(), *v)).collect();
    let mut out = String::with_capacity(text.len());
    let (mut id, mut in_literal) = (None::<String>, false);
    for line in text.split_inclusive('\n') {
        if in_literal {
            out.push_str(line);
        } else if let Some(v) = line.strip_prefix("id = \"") {
            id = v.split('"').next().map(str::to_owned);
            out.push_str(line);
        } else if line.starts_with("observed = ")
            && let Some(v) = id.as_deref().and_then(|i| live.get(i))
        {
            let _ = writeln!(out, "observed = \"{}\"", spelled(*v));
        } else {
            out.push_str(line);
        }
        if line.matches("'''").count() % 2 == 1 {
            in_literal = !in_literal;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(id: &str, x: Verdict) -> (String, Verdict) {
        (id.to_owned(), x)
    }

    // frob:tests crates/gob-check/src/incompleteness_live.rs::rewrite_observed
    #[test]
    fn rewrite_changes_observed_lines_only_and_skips_probe_sources() {
        let text = "# keep\n[[case]]\nid = \"a\"\nsource = '''\nobserved = \"yes\"\n'''\nobserved = \"yes\"\n";
        let out = rewrite_observed(text, &[v("a", Verdict::No)]);
        assert_eq!(
            out,
            "# keep\n[[case]]\nid = \"a\"\nsource = '''\nobserved = \"yes\"\n'''\nobserved = \"no\"\n"
        );
    }

    // frob:tests crates/gob-check/src/incompleteness_live.rs::diff_column
    #[test]
    fn diff_lists_only_disagreements_in_corpus_order() {
        let mk = |id: &str, o| OracleCase {
            id: id.to_owned(),
            language: "rust".to_owned(),
            capability: "visibility".to_owned(),
            oracle: Verdict::Yes,
            observed: o,
            file: None,
            source: None,
            query: None,
        };
        let cases = [mk("b", Verdict::Yes), mk("a", Verdict::Yes)];
        let live = [v("a", Verdict::No), v("b", Verdict::Yes)];
        let d = diff_column(&cases, &live);
        assert_eq!(
            d,
            [Mismatch {
                id: "a".to_owned(),
                committed: Verdict::Yes,
                live: Verdict::No
            }]
        );
    }

    // frob:tests crates/gob-check/src/incompleteness_live.rs::live_verdict
    #[test]
    fn a_case_without_a_probe_is_an_error_not_a_verdict() {
        let c = OracleCase {
            id: "x".to_owned(),
            language: "rust".to_owned(),
            capability: "visibility".to_owned(),
            oracle: Verdict::Yes,
            observed: Verdict::Yes,
            file: None,
            source: None,
            query: None,
        };
        assert_eq!(
            live_verdict(&c),
            Err(LiveError::MissingProbe("x".to_owned()))
        );
    }
}
