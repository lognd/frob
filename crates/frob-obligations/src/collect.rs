//! Standalone input collection: graph and lock through `frob-ack`, plus every directive.

use std::path::Path;

use frob_ack::{AckError, Inputs};
use gob_directives::{DirectiveRecord, ScanConfig, Scanner};
use gob_languages::Language;
use gob_lock::LockFile;
use gob_symbols::{SymbolGraph, extract_file};
use gob_text::FileInterner;
use gob_walk::{WalkConfig, walk};

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
    let mut directives = Vec::new();
    for entry in &walked.files {
        let Some(lang) = Language::detect(&entry.path) else {
            continue;
        };
        let Ok(text) = std::fs::read_to_string(root.join(&entry.path)) else {
            tracing::debug!(path = %entry.path, "unreadable file not scanned for directives");
            continue;
        };
        let symbols = extract_file(entry, &text);
        let file = files.intern(&entry.path);
        directives.extend(scanner.scan_in(file, lang, &text, &symbols).directives);
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
    })
}
