//! C, C++ and Java call resolution for the symbol graph.
//!
//! Neither language has Rust's crate and module paths, so these calls never go through the
//! Rust resolver. A bare call `f()` names the function or method called `f` in the caller's own
//! file (one is Must, several overloads are May); failing that it names every such definition of
//! the repository by name alone (extern linkage, an inherited method). A member or qualified call
//! cannot be typed without a checker, so it names every definition of that name (May,
//! `NameOnly`). A name nothing defines (`printf`, `System.out.println`) is an external Unbound gap.

// frob:ticket 01M7BSMQWJ77EENS87BQBQWFB4

use std::collections::HashMap;

use petgraph::graph::NodeIndex;

use super::{GapReason, Outcome, SymbolGraph};
use crate::model::{CallSite, FileSymbols, SymbolKind};
use gob_ir::Status;

/// True when `path` is a C or C++ source or header.
pub(super) fn is_c_family(path: &str) -> bool {
    crate::c::is_c_path(path) || crate::c::is_cpp_path(path)
}

/// True when `path` is a Java source file.
pub(super) fn is_java(path: &str) -> bool {
    crate::java::is_java_path(path)
}

/// Lookup tables over the functions and methods of one language's files.
#[derive(Debug, Default)]
pub(super) struct FlatIndex {
    /// (file path, name) to the definitions so named in that file.
    in_file: HashMap<(String, String), Vec<NodeIndex>>,
    /// Name to every definition so named, in any file.
    by_name: HashMap<String, Vec<NodeIndex>>,
}

impl FlatIndex {
    /// Indexes the functions and methods of every file in `files` whose path satisfies `keep`.
    pub(super) fn build(g: &SymbolGraph, files: &[FileSymbols], keep: fn(&str) -> bool) -> Self {
        let mut ix = Self::default();
        for f in files.iter().filter(|f| keep(&f.path)) {
            for s in &f.symbols {
                if !matches!(s.kind, SymbolKind::Function | SymbolKind::Method) {
                    continue;
                }
                let (Some(&node), Some(name)) = (g.index.get(&s.symref), s.symref.name()) else {
                    continue;
                };
                // A method is named `Type.name` or `Type::name`: its callable name is the last part.
                let simple = name.rsplit(['.', ':']).next().unwrap_or(name).to_owned();
                ix.in_file
                    .entry((f.path.clone(), simple.clone()))
                    .or_default()
                    .push(node);
                ix.by_name.entry(simple).or_default().push(node);
            }
        }
        tracing::debug!(
            in_file = ix.in_file.len(),
            names = ix.by_name.len(),
            "flat index built"
        );
        ix
    }
}

impl SymbolGraph {
    /// Resolves a C, C++ or Java call by file (bare) or by name alone (member or qualified).
    pub(super) fn resolve_flat(ix: &FlatIndex, call: &CallSite) -> Outcome {
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        let by_name = || match ix.by_name.get(&call.callee) {
            Some(nodes) if !nodes.is_empty() => Outcome::NameOnly(nodes.clone()),
            _ => Outcome::Gap(GapReason::Unbound),
        };
        if call.method || !call.qual_path.is_empty() {
            return by_name();
        }
        let key = (call.caller.path().to_owned(), call.callee.clone());
        match ix.in_file.get(&key).map(Vec::as_slice) {
            Some([one]) => Outcome::Hit(vec![*one], Status::Must),
            Some(many) if !many.is_empty() => Outcome::Hit(many.to_vec(), Status::May),
            _ => by_name(),
        }
    }
}
