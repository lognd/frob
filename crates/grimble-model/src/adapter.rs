//! The F4 adapter `A_grmb` for gob-symbols (grmb-spec 9, universal-model.md 3.1).
//!
//! [`GrmbAdapter::parse`] returns the text as [`ConcreteTree::Source`] (the parser is
//! hand-written, so there is no tree-sitter tree) and [`GrmbAdapter::fold`] parses and
//! folds it; [`fold_text`] is the direct entry point. The adapter registers itself with
//! gob-symbols through [`gob_symbols::AdapterEntry`], so any binary linking this crate
//! sees `grmb` at F4 in [`gob_symbols::fidelity_report`].

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3
// frob:ticket 01M3ZEH3S0PG61C2AEBM691F69

use std::sync::Arc;

use gob_ir::{Location, NodeSpec, Operator, ScopeGraph, TermBuilder};
use gob_languages::ParseLimits;
use gob_symbols::{
    Adapter, AdapterEntry, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FileSymbols,
    FoldError, Folded, Lang, ParseStatus, model_symbols,
};
use gob_text::FileInterner;

use crate::ast::FileStatus;
use crate::fold::{LANG, fold_file};
use crate::parse::parse_file;

/// Bump when the encoding of grmb-spec 9.2 changes for the same input; part of the cache key.
pub const ADAPTER_VERSION: u32 = 1;

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

fn file_symbols(
    input: &FileInput<'_>,
    status: ParseStatus,
    term: Option<&gob_ir::Term>,
) -> FileSymbols {
    let (symbols, extras) = term.map_or_else(Default::default, |t| model_symbols(t, input.path));
    FileSymbols {
        symbols,
        extras,
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
    let file = file_symbols(input, status, Some(&folded.term));
    Ok(Folded {
        term: folded.term,
        scopes: folded.scopes,
        file,
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
            None,
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
        gob_caps::lang_fidelity(Lang::Grmb)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Grmb)
    }

    fn parse(&self, text: &str, limits: &ParseLimits) -> ConcreteTree {
        if text.len() as u64 > limits.max_bytes {
            return ConcreteTree::Unparsed(gob_languages::UnresolvedReason::TooLarge {
                size: text.len() as u64,
                cap: limits.max_bytes,
            });
        }
        ConcreteTree::Source(Arc::from(text))
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Unparsed(r) => failed(input, &r.to_string()),
            ConcreteTree::Parsed(_) => failed(input, "not a grmb tree"),
            ConcreteTree::Leaf => failed(input, "no source text"),
            ConcreteTree::Source(text) => fold_text(text.as_bytes(), input, ""),
        }
    }
}

inventory::submit! {
    AdapterEntry {
        language_name: LANG,
        extensions: &["grmb"],
        construct: || Box::new(GrmbAdapter),
    }
}
