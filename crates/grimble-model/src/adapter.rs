//! The F4 adapter `A_grmb` for gob-symbols (grmb-spec 9, universal-model.md 3.1).
//!
//! `gob_symbols::ConcreteTree` can only carry a tree-sitter tree, an unparsed reason or
//! the adapter-less leaf, and `Adapter::fold` receives no source text, so a hand-written
//! parser has nowhere to put its result. [`GrmbAdapter::parse`] therefore parks the text
//! of the file it was just given on the calling thread and [`GrmbAdapter::fold`] takes it
//! back; the gob-symbols pipeline always calls the two back to back on one thread. The
//! robust fix is a `ConcreteTree::Source` variant in gob-symbols (decision-log proposal in
//! the G08 report); [`fold_text`] is the direct, thread-free entry point.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::cell::RefCell;

use gob_ir::{Location, NodeSpec, Operator, ScopeGraph, TermBuilder};
use gob_languages::ParseLimits;
use gob_symbols::{
    Adapter, Capability, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FileSymbols, FoldError,
    Folded, ParseStatus, Precision,
};
use gob_text::FileInterner;

use crate::ast::FileStatus;
use crate::fold::{LANG, fold_file};
use crate::parse::parse_file;

/// Bump when the encoding of grmb-spec 9.2 changes for the same input; part of the cache key.
pub const ADAPTER_VERSION: u32 = 1;

thread_local! {
    static PENDING: RefCell<Option<String>> = const { RefCell::new(None) };
}

/// The grimble-model grammar identity: the hand-written parser has no grammar crate, so it
/// is the crate version plus the language major it reads.
pub fn grammar_identity() -> String {
    format!(
        "grmb:grimble-model@{}:major{}",
        env!("CARGO_PKG_VERSION"),
        crate::parse::SUPPORTED_MAJOR
    )
}

/// The .grmb adapter (fidelity F4).
#[derive(Debug, Clone, Copy, Default)]
pub struct GrmbAdapter;

fn status_of(f: &crate::ast::ParsedFile) -> ParseStatus {
    match &f.status {
        FileStatus::Opaque(r) | FileStatus::Refused(r) => ParseStatus::Failed {
            reason: (*r).to_owned(),
        },
        FileStatus::Parsed if f.holes > 0 => ParseStatus::Partial {
            holes: u32::try_from(f.holes).unwrap_or(u32::MAX),
        },
        FileStatus::Parsed => ParseStatus::Complete,
    }
}

fn file_symbols(input: &FileInput<'_>, status: ParseStatus) -> FileSymbols {
    FileSymbols {
        path: input.path.to_owned(),
        file_digest: input.digest.to_owned(),
        size: input.size,
        language: LANG.to_owned(),
        fidelity: Fidelity::F4,
        degraded: matches!(status, ParseStatus::Failed { .. }),
        parse_status: status,
        ..FileSymbols::default()
    }
}

/// Folds `text` directly (no thread-local hand-off), mounted under `mount`.
///
/// # Errors
///
/// [`FoldError`] only when the fold builds an ill-formed term (a bug).
pub fn fold_text(text: &[u8], input: &FileInput<'_>, mount: &str) -> Result<Folded, FoldError> {
    let parsed = parse_file(input.path, text);
    let status = status_of(&parsed);
    let folded = fold_file(&parsed, mount)?;
    tracing::debug!(path = input.path, ?status, "grmb adapter fold");
    Ok(Folded {
        term: folded.term,
        scopes: folded.scopes,
        file: file_symbols(input, status),
    })
}

fn failed(input: &FileInput<'_>, why: &str) -> Result<Folded, FoldError> {
    let mut files = FileInterner::new();
    let fid = files.intern(input.path);
    let mut b = TermBuilder::new(input.path, LANG);
    let loc = Location::text(fid, 0, input.size);
    let hole = b.node(
        NodeSpec::new(Operator::hole("parse-failed"), loc.clone()),
        &[],
    )?;
    let root = b.node(
        NodeSpec::new(Operator::unit("module", "declaration"), loc),
        &[hole],
    )?;
    let term = b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    tracing::warn!(path = input.path, why, "grmb file folded as one hole");
    Ok(Folded {
        term,
        scopes,
        file: file_symbols(
            input,
            ParseStatus::Failed {
                reason: why.to_owned(),
            },
        ),
    })
}

impl Adapter for GrmbAdapter {
    fn language(&self) -> &'static str {
        LANG
    }

    fn identity(&self) -> String {
        format!("grimble-model/v{ADAPTER_VERSION}/{}", grammar_identity())
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F4
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
            .with(Capability::ResolveRef, Precision::Lexical)
            .with(Capability::ApplyTargets, Precision::Declared)
            .with(Capability::Imports, Precision::Syntactic)
            .with(Capability::Order, Precision::Declared)
            .with(Capability::Visibility, Precision::NotApplicable)
            .with(Capability::Effects, Precision::NotApplicable)
            .with(Capability::TestItems, Precision::NotApplicable)
            .with(Capability::Expand, Precision::NotApplicable)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        if text.len() as u64 > limits.max_bytes {
            return ConcreteTree::Unparsed(gob_languages::UnresolvedReason::TooLarge {
                size: text.len() as u64,
                cap: limits.max_bytes,
            });
        }
        PENDING.with(|p| *p.borrow_mut() = Some(text.to_owned()));
        ConcreteTree::Leaf
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Unparsed(r) => failed(input, &r.to_string()),
            ConcreteTree::Parsed(_) => failed(input, "not a grmb tree"),
            ConcreteTree::Leaf => {
                let text = PENDING.with(|p| p.borrow_mut().take());
                match text {
                    Some(t) if t.len() == input.size as usize => fold_text(t.as_bytes(), input, ""),
                    _ => failed(input, "no text was parked by parse"),
                }
            }
        }
    }
}
