//! The code side of binding: every walked file folded into a U term and scope graph.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::collections::BTreeMap;
use std::path::Path;

use gob_ir::{NodeId, Operator, Term, Universal};
use gob_symbols::{Fidelity, Folded, adapter_for};
use gob_walk::{FileEntry, LanguageHint, WalkResult};
use rayon::prelude::*;

/// The tag of a file no adapter claims.
pub const OPAQUE: &str = "opaque";

/// One walked file with what folding it produced.
#[derive(Debug)]
pub struct CodeFile {
    /// Repo-relative path.
    pub path: String,
    /// The walk's language guess.
    pub hint: LanguageHint,
    /// The adapter language tag, or [`OPAQUE`].
    pub language: String,
    /// The fidelity the file was folded at (F0 for an adapter-less file).
    pub fidelity: Fidelity,
    /// True when the file could not be read or folded: all of it is an unseen remainder.
    pub unreadable: bool,
    /// The term, scope graph and symbol view; `None` for an unreadable file.
    pub folded: Option<Folded>,
    /// The text, kept only for a file that mentions `grimble:binds`.
    pub text: Option<String>,
}

/// One unit of a term: its symref text, node and unit kind.
#[derive(Clone, Debug)]
pub struct Unit {
    /// The symref spelled as text (the identity key).
    pub symref: String,
    /// The `unit` or `anon` node.
    pub node: NodeId,
    /// The unit kind (`module`, `function`, ...).
    pub kind: String,
}

impl CodeFile {
    /// True when the file is an adapter-less F0 opaque unit.
    pub fn is_opaque(&self) -> bool {
        self.language == OPAQUE
    }

    /// The units of the file in document order (empty when unreadable).
    pub fn units(&self) -> Vec<Unit> {
        let Some(f) = &self.folded else {
            return Vec::new();
        };
        f.term
            .units()
            .into_iter()
            .map(|u| Unit {
                symref: u.symref.to_string(),
                node: u.node,
                kind: unit_kind(&f.term, u.node),
            })
            .collect()
    }

    /// True when the term holds an opaque region, a hole or an unexpanded phase.
    pub fn has_unseen(&self) -> bool {
        let Some(f) = &self.folded else { return true };
        let t = &f.term;
        t.ids().any(|id| match t.operator(id) {
            op if op.is_opaque() || op.is_hole() => true,
            Operator::Universal(Universal::Phase { .. }) => t.children(id).len() < 2,
            _ => false,
        })
    }
}

/// The unit kind of `node` (`anon` units answer their anon kind).
pub fn unit_kind(term: &Term, node: NodeId) -> String {
    match term.operator(node) {
        Operator::Universal(Universal::Unit { kind, .. } | Universal::Anon { kind }) => {
            kind.clone()
        }
        _ => String::new(),
    }
}

/// Every walked file, folded, plus the walk as `gob-walk` selectors want it.
#[derive(Debug, Default)]
pub struct Code {
    /// Files sorted by path.
    pub files: Vec<CodeFile>,
    /// The walk (sorted, nothing oversized: the check core drops those).
    pub walk: WalkResult,
    by_path: BTreeMap<String, usize>,
}

impl Code {
    /// Fold every entry of `entries` under `root` (in parallel).
    pub fn build(root: &Path, entries: &[FileEntry]) -> Self {
        let mut files: Vec<CodeFile> = entries.par_iter().map(|e| fold_entry(root, e)).collect();
        files.sort_by(|a, b| a.path.cmp(&b.path));
        let mut sorted: Vec<FileEntry> = entries.to_vec();
        sorted.sort_by(|a, b| a.path.cmp(&b.path));
        let by_path = files
            .iter()
            .enumerate()
            .map(|(i, f)| (f.path.clone(), i))
            .collect();
        tracing::info!(files = files.len(), "code folded for binding");
        Self {
            files,
            walk: WalkResult {
                files: sorted,
                oversized: Vec::new(),
            },
            by_path,
        }
    }

    /// The file at `path`.
    pub fn file(&self, path: &str) -> Option<&CodeFile> {
        self.by_path.get(path).map(|&i| &self.files[i])
    }
}

fn fold_entry(root: &Path, e: &FileEntry) -> CodeFile {
    let adapter = adapter_for(&e.language);
    let language = adapter.map_or(OPAQUE, |a| a.language()).to_owned();
    let text = if adapter.is_some() {
        match std::fs::read_to_string(root.join(&e.path)) {
            Ok(t) => Some(t),
            Err(err) => {
                tracing::warn!(path = %e.path, %err, "file unreadable; all of it is unseen");
                return unreadable(e, language);
            }
        }
    } else {
        None
    };
    match gob_symbols::fold_file(e, text.as_deref().unwrap_or("")) {
        Ok(folded) => CodeFile {
            path: e.path.clone(),
            hint: e.language.clone(),
            language,
            fidelity: folded.file.fidelity,
            unreadable: false,
            folded: Some(folded),
            text: text.filter(|t| t.contains("grimble:binds")),
        },
        Err(err) => {
            tracing::error!(path = %e.path, %err, "adapter bug: fold failed");
            unreadable(e, language)
        }
    }
}

fn unreadable(e: &FileEntry, language: String) -> CodeFile {
    CodeFile {
        path: e.path.clone(),
        hint: e.language.clone(),
        language,
        fidelity: Fidelity::F0,
        unreadable: true,
        folded: None,
        text: None,
    }
}
