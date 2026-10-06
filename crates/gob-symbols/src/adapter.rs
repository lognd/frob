//! The adapter contract of universal-model.md 3.1: `parse`, `fold` (rho and
//! bind), `capabilities` and `fidelity`.
//!
//! An adapter turns one artifact into a concrete tree ([`Adapter::parse`], total:
//! it never fails), then into a [`gob_ir::Term`] plus a [`gob_ir::ScopeGraph`]
//! ([`Adapter::fold`]). Everything the rest of this crate exposes (the
//! [`crate::SymbolRecord`] view, the call graph) is computed from those terms.

// frob:ticket 01M3Z713F6VY15YSMS15033RN1

use std::fmt;
use std::sync::Arc;

use gob_ir::{ScopeGraph, Term, TermError};
use gob_languages::{ParseLimits, ParsedTree, UnresolvedReason};
use serde::{Deserialize, Serialize};

use crate::model::FileSymbols;

/// Fidelity of an adapter (universal-model.md 3.3), checked by its corpus.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Default, Serialize, Deserialize,
)]
pub enum Fidelity {
    /// Opaque only: locations and whole-artifact digests.
    #[default]
    F0,
    /// Units, roles and containment.
    F1,
    /// F1 plus binders, references and a lexical scope graph with Must edges.
    F2,
    /// F2 plus `apply` edges resolved to the adapter's declared status.
    F3,
    /// F3 plus attributes, comments bound to targets, regions and phases.
    F4,
}

impl fmt::Display for Fidelity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::F0 => "F0",
            Self::F1 => "F1",
            Self::F2 => "F2",
            Self::F3 => "F3",
            Self::F4 => "F4",
        })
    }
}

/// A capability an adapter may declare (universal-model.md 4.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Capability {
    /// Resolving a reference to its declarations.
    ResolveRef,
    /// The targets of an application (call graph).
    ApplyTargets,
    /// Whether a unit is visible outside its container.
    Visibility,
    /// Effects of a region.
    Effects,
    /// Which units are tests.
    TestItems,
    /// The imports of an artifact.
    Imports,
    /// Expansion of a phase (macro).
    Expand,
    /// Evaluation order of a group.
    Order,
    /// Packages, their dependencies, path aliases and entry files (language-engines.md section 2).
    ProjectModel,
}

impl Capability {
    /// Every capability in table order.
    pub const ALL: [Self; 9] = [
        Self::ResolveRef,
        Self::ApplyTargets,
        Self::Visibility,
        Self::Effects,
        Self::TestItems,
        Self::Imports,
        Self::Expand,
        Self::Order,
        Self::ProjectModel,
    ];

    /// The spelling used in universal-model.md and `frob doctor --languages`.
    pub const fn name(self) -> &'static str {
        match self {
            Self::ResolveRef => "resolve_ref",
            Self::ApplyTargets => "apply_targets",
            Self::Visibility => "visibility",
            Self::Effects => "effects",
            Self::TestItems => "test_items",
            Self::Imports => "imports",
            Self::Expand => "expand",
            Self::Order => "order",
            Self::ProjectModel => "project_model",
        }
    }
}

/// How precisely a capability is answered (one rung of its ladder).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Precision {
    /// Not provided: the answer is Unknown.
    None,
    /// The language has no such concept: the answer is `NotApplicable`.
    NotApplicable,
    /// Lexical scoping only.
    Lexical,
    /// Lexical scoping plus `use` imports resolved inside the crate.
    LexicalImports,
    /// Resolution by name inside the crate; ambiguous names give May sets.
    ByNameInCrate,
    /// Resolution of link targets against the project's anchors.
    LinkTargets,
    /// Read from a keyword or modifier.
    Keyword,
    /// Read from the syntax alone.
    Syntactic,
    /// Declared by the source, not inferred.
    Declared,
    /// Read from the build manifests (`Cargo.toml`, `.csproj`, `package.json`, `tsconfig.json`).
    Manifest,
}

impl Precision {
    /// The label printed by `frob doctor --languages`.
    pub const fn label(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::NotApplicable => "not-applicable",
            Self::Lexical => "lexical",
            Self::LexicalImports => "lexical+imports",
            Self::ByNameInCrate => "by-name-in-crate (May)",
            Self::LinkTargets => "link-targets",
            Self::Keyword => "keyword",
            Self::Syntactic => "syntactic",
            Self::Declared => "declared",
            Self::Manifest => "manifest",
        }
    }
}

/// The capability declaration `cap_L`: a precision per capability.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct CapabilityDecl {
    entries: Vec<(Capability, Precision)>,
}

impl CapabilityDecl {
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

    /// Every capability with its precision, in table order.
    pub fn rows(&self) -> Vec<(Capability, Precision)> {
        Capability::ALL
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
