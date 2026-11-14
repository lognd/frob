//! Go call resolution for the symbol graph.
//!
//! A Go package is a directory, so a bare call `f()` names the free functions called `f` in the
//! caller's directory: one is Must, several (build-tag variants) are May. A selector call `x.m()`
//! cannot be typed without a checker, so it names every Go method `m` and every free function `m`
//! of the repository by name alone (May, `NameOnly`). A name nothing defines (`len`, `fmt.Println`)
//! is an external Unbound gap.

// frob:ticket 01M7AV38DKR1SA56E17SY378XX

use std::collections::HashMap;

use petgraph::graph::NodeIndex;

use super::{GapReason, Outcome, SymbolGraph};
use crate::model::{CallSite, FileSymbols, SymbolKind};
use gob_ir::Status;

/// True when `path` is a Go source file.
pub(super) fn is_go(path: &str) -> bool {
    crate::go::is_go_path(path)
}

/// The directory (the Go package) of `path`.
fn package_dir(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// Lookup tables over the repository's Go files.
#[derive(Debug, Default)]
pub(super) struct GoIndex {
    /// (package directory, name) to the free functions so named.
    funcs: HashMap<(String, String), Vec<NodeIndex>>,
    /// Name to every Go function or method so named, in any package.
    by_name: HashMap<String, Vec<NodeIndex>>,
}

impl GoIndex {
    /// Indexes the functions and methods of every Go file in `files`.
    pub(super) fn build(g: &SymbolGraph, files: &[FileSymbols]) -> Self {
        let mut ix = Self::default();
        for f in files.iter().filter(|f| is_go(&f.path)) {
            for s in &f.symbols {
                let (Some(&node), Some(name)) = (g.index.get(&s.symref), s.symref.name()) else {
                    continue;
                };
                // A method is named `Recv.name`: its callable name is the last segment.
                let simple = name.rsplit('.').next().unwrap_or(name).to_owned();
                match s.kind {
                    SymbolKind::Function => {
                        ix.funcs
                            .entry((package_dir(&f.path).to_owned(), simple.clone()))
                            .or_default()
                            .push(node);
                        ix.by_name.entry(simple).or_default().push(node);
                    }
                    SymbolKind::Method => ix.by_name.entry(simple).or_default().push(node),
                    _ => {}
                }
            }
        }
        tracing::debug!(
            functions = ix.funcs.len(),
            names = ix.by_name.len(),
            "go index built"
        );
        ix
    }
}

impl SymbolGraph {
    /// Resolves a Go call by package directory (bare) or by name alone (selector).
    pub(super) fn resolve_go(ix: &GoIndex, call: &CallSite) -> Outcome {
        if call.callee.is_empty() {
            return Outcome::Gap(GapReason::Dynamic);
        }
        if call.method {
            return match ix.by_name.get(&call.callee) {
                Some(nodes) if !nodes.is_empty() => Outcome::NameOnly(nodes.clone()),
                _ => Outcome::Gap(GapReason::Unbound),
            };
        }
        let key = (
            package_dir(call.caller.path()).to_owned(),
            call.callee.clone(),
        );
        match ix.funcs.get(&key).map(Vec::as_slice) {
            Some([one]) => Outcome::Hit(vec![*one], Status::Must),
            Some(many) if !many.is_empty() => Outcome::Hit(many.to_vec(), Status::May),
            _ => Outcome::Gap(GapReason::Unbound),
        }
    }
}
