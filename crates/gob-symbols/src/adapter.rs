//! The adapter contract of universal-model.md 3.1: `parse`, `fold` (rho and
//! bind), `capabilities` and `fidelity`.
//!
//! An adapter turns one artifact into a concrete tree ([`Adapter::parse`], total:
//! it never fails), then into a [`gob_ir::Term`] plus a [`gob_ir::ScopeGraph`]
//! ([`Adapter::fold`]). Everything the rest of this crate exposes (the
//! [`crate::SymbolRecord`] view, the call graph) is computed from those terms.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::sync::Arc;

use gob_ir::{ScopeGraph, Term, TermError};
use gob_languages::{ParseLimits, ParsedTree, UnresolvedReason};
use serde::{Deserialize, Serialize};

use crate::model::FileSymbols;

pub use gob_caps::{Capability, Fidelity, Lang, Precision};

/// The capability declaration `cap_L`: a precision per capability.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct CapabilityDecl {
    entries: Vec<(Capability, Precision)>,
}

impl CapabilityDecl {
    /// The declaration of `lang`: a read of its row in [`gob_caps::MATRIX`], the one source.
    pub fn for_lang(lang: Lang) -> Self {
        let row = gob_caps::row(lang);
        Self {
            entries: Capability::ALL.iter().map(|&c| (c, row.cell(c))).collect(),
        }
    }

    /// Declares `cap` at `precision`, replacing an earlier declaration.
    #[must_use]
    pub fn with(mut self, cap: Capability, precision: Precision) -> Self {
        self.entries.retain(|(c, _)| *c != cap);
        self.entries.push((cap, precision));
        self
    }

    /// The precision of `cap`; [`Precision::None`] when undeclared.
    pub fn precision(&self, cap: Capability) -> Precision {
        self.entries
            .iter()
            .find(|(c, _)| *c == cap)
            .map_or(Precision::None, |(_, p)| *p)
    }

    /// Every languages-page capability with its precision, in table order.
    pub fn rows(&self) -> Vec<(Capability, Precision)> {
        Capability::PAGE
            .iter()
            .map(|&c| (c, self.precision(c)))
            .collect()
    }
}

/// How completely a file parsed; the answer to the `parse_status` query (G11).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
pub enum ParseStatus {
    /// The tree has no error nodes.
    Complete,
    /// A tree exists but `holes` parts of it are errors or missing tokens.
    Partial {
        /// Number of `hole` nodes in the term.
        holes: u32,
    },
    /// No tree could be produced (too large, timed out, no grammar).
    Failed {
        /// Why, spelled like the underlying reason.
        reason: String,
    },
    /// The language has no adapter; the file is one opaque unit.
    #[default]
    NotParsed,
}

impl ParseStatus {
    /// True only for [`ParseStatus::Complete`].
    pub fn is_complete(&self) -> bool {
        matches!(self, Self::Complete)
    }
}

/// The result of [`Adapter::parse`]: total, never an error.
#[derive(Debug, Clone)]
pub enum ConcreteTree {
    /// A tree-sitter tree (it may contain error nodes).
    Parsed(ParsedTree),
    /// No tree could be produced.
    Unparsed(UnresolvedReason),
    /// The constant one-leaf tree of an adapter-less file.
    Leaf,
    /// The source text itself, for adapters whose hand-written parser runs in `fold`.
    Source(Arc<str>),
}

/// The facts about one artifact that every adapter needs from the walker.
#[derive(Debug, Clone, Copy)]
pub struct FileInput<'a> {
    /// Repo-relative path.
    pub path: &'a str,
    /// Hex digest of the file content.
    pub digest: &'a str,
    /// Size in bytes.
    pub size: u32,
}

/// The output of [`Adapter::fold`].
#[derive(Debug)]
pub struct Folded {
    /// The sorted term of the artifact.
    pub term: Term,
    /// The scope graph of the artifact (lexical view plus adapter edges).
    pub scopes: ScopeGraph,
    /// The compatibility view computed from the term (the cached payload).
    pub file: FileSymbols,
}

/// A failure of [`Adapter::fold`]; always an adapter bug.
#[derive(Debug, thiserror::Error)]
pub enum FoldError {
    /// The adapter built an ill-formed term.
    #[error("adapter built an ill-formed term: {0}")]
    Term(#[from] TermError),
}

/// A language adapter `A_L = (parse, rho, bind, cap)` over U.
pub trait Adapter: Send + Sync {
    /// Stable lowercase language tag (`rust`, `markdown`, `opaque`).
    fn language(&self) -> &'static str;

    /// Adapter name, version and grammar identity: the cache key component.
    fn identity(&self) -> String;

    /// The fidelity this adapter claims (checked by `tests/corpus`).
    fn fidelity(&self) -> Fidelity;

    /// The capability declaration with precisions.
    fn capabilities(&self) -> CapabilityDecl;

    /// Parses `text`; total: failures are [`ConcreteTree::Unparsed`].
    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree;

    /// Folds a concrete tree into a term and scope graph.
    ///
    /// # Errors
    ///
    /// [`FoldError`] when the adapter builds an ill-formed term (a bug).
    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError>;
}
