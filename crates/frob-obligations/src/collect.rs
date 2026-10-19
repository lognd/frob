//! Standalone input collection: graph and lock through `frob-ack`, plus every directive.

use std::collections::BTreeMap;
use std::path::Path;

use frob_ack::{AckError, Inputs};
use gob_directives::{DirectiveRecord, ScanConfig, Scanner};
use gob_languages::Language;
use gob_lock::LockFile;
use gob_rules::RuleId;
use gob_symbols::{SymbolGraph, extract_file};
use gob_text::FileInterner;
use gob_walk::{Roles, WalkConfig, walk};

use crate::ObligationInputs;
use crate::config::InvariantsConfig;

/// Why collecting inputs failed.
#[derive(Debug, thiserror::Error)]
pub enum CollectError {
    /// The graph, lock or walk of `frob-ack` failed.
    #[error(transparent)]
    Ack(#[from] AckError),
    /// The repository walk for directives failed.
    #[error("E-OBL-WALK: {0}")]
    Walk(#[from] gob_walk::WalkError),
}

/// Owned graph, lock, directives and interner of one repository state.
pub struct Collected {
    /// The symbol graph.
    pub graph: SymbolGraph,
    /// The current `frob.lock` (empty when absent).
    pub lock: LockFile,
    /// Every well-formed directive of the honoured namespaces, in file then source order.
    pub directives: Vec<DirectiveRecord>,
    /// Resolves the `FileId`s inside the directive spans.
    pub files: FileInterner,
    /// Tool ids bound to frob rules by the repository's `[[check.tool]]` stages.
    pub tool_ids: BTreeMap<String, RuleId>,
    /// The UTC day `until=` dates are compared with, read once when collecting.
    pub today: gob_time::Day,
}

impl Collected {
    /// Borrow as evaluation inputs for the repository at `root`.
    pub fn inputs<'a>(
        &'a self,
        root: &'a Path,
        ledger: Option<&'a frob_ledger::Ledger>,
        config: &'a InvariantsConfig,
    ) -> ObligationInputs<'a> {
        ObligationInputs {
            root,
            graph: &self.graph,
            directives: &self.directives,
            lock: &self.lock,
            ledger,
            files: &self.files,
            config,
            today: self.today,
            tool_ids: &self.tool_ids,
        }
    }
}

/// Collect everything the rules read for the repository at `root`.
///
/// The graph, lock and interner come from [`frob_ack::Inputs::collect`] (the
/// `.frob/` cache serves the graph); the directives are scanned here because
/// `frob-ack` keeps only `frob:doc`. `frob check` builds the same inputs from
/// its own cached pipeline and does not call this.
///
/// # Errors
///
/// [`CollectError`] when the walk fails or `frob.lock` is malformed.
pub fn collect(root: &Path) -> Result<Collected, CollectError> {
    let Inputs {
        graph,
        lock,
        mut files,
        ..
    } = Inputs::collect(root)?;
    let config = WalkConfig {
        exclude: vec!["/.frob/".to_owned(), "/target/".to_owned()],
        ..WalkConfig::default()
    };
    let walked = walk(root, &config)?;
    let scanner = Scanner::new(&ScanConfig::default());
    let roles = Roles::new(&gob_config::ledger_dir(root));
    let content = gob_walk::ContentSource::locate(root);
    let mut directives = Vec::new();
    for entry in &walked.files {
        // frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
        if !roles.role(&entry.path).scans_directives() {
            continue;
        }
        let lang = Language::detect(&entry.path);
        let Ok(text) = content.with_reader(|r| r.read_text(&entry.path)) else {
            tracing::debug!(path = %entry.path, "unreadable file not scanned for directives");
            continue;
        };
        let symbols = extract_file(entry, &text);
        let file = files.intern(&entry.path);
        // No grammar: still scanned, lexically (same split as frob-check).
        let result = match lang {
            Some(lang) => scanner.scan_in(file, lang, &text, &symbols),
            None => scanner.scan_unparsed_in(file, &text, &symbols),
        };
        directives.extend(result.directives);
    }
    tracing::info!(
        directives = directives.len(),
        symbols = graph.node_count(),
        "obligation inputs collected"
    );
    Ok(Collected {
        graph,
        lock,
        directives,
        files,
        tool_ids: crate::tool_bound_ids(root),
        today: gob_time::Clock::today(&gob_time::SystemClock::pin()),
    })
}

#[cfg(test)]
mod tests {
    use super::collect;

    // frob:ticket 01M5B3C8ZKMG5N6TMP07NG0ESV
    // frob:tests crates/frob-obligations/src/collect.rs::collect
    #[test]
    fn collect_scans_directives_in_files_without_a_grammar() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("conf/site.caddy");
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(&path, "# frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB\nroute\n").expect("write");
        let collected = collect(dir.path()).expect("collect");
        assert_eq!(collected.directives.len(), 1, "{:?}", collected.directives);
    }
}
