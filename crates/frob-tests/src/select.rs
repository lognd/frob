//! Test selection: which test functions can see the touched symbols.

use std::collections::BTreeSet;
use std::path::Path;

use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord, Symref};
use schemars::JsonSchema;
use serde::Serialize;

use crate::catalog::{Packages, is_test_file, is_test_fn, test_name};
use crate::reach::{Sources, name_callers};
use crate::touched::TouchedSet;

/// One selected test: the owning package and the name nextest knows it by.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema)]
pub struct TestTarget {
    /// Cargo package name (`-p`).
    pub package: String,
    /// The test's name inside its binary (`tests::doubles`, `integration_quad`).
    pub test_path: String,
    /// The test function's symref.
    pub symref: String,
}

/// Seeds for `touched`: its symbols, widened for non-function items.
///
/// The call graph says nothing about who uses a changed struct, enum or
/// constant, so every function in the same file is a seed as well.
fn seeds(graph: &SymbolGraph, touched: &TouchedSet) -> BTreeSet<Symref> {
    let mut out: BTreeSet<Symref> = touched.symbols.iter().cloned().collect();
    for s in &touched.symbols {
        let widen = graph.get(s).is_some_and(|r| {
            !matches!(
                r.kind,
                SymbolKind::Function | SymbolKind::Method | SymbolKind::Impl | SymbolKind::Module
            )
        });
        if widen {
            out.extend(
                graph
                    .records()
                    .filter(|r| {
                        r.symref.path() == s.path()
                            && matches!(r.kind, SymbolKind::Function | SymbolKind::Method)
                    })
                    .map(|r| r.symref.clone()),
            );
        }
    }
    out
}

/// Tests reachable from the touched symbols through `affects` (and unique-name calls, see [`crate::reach`]), plus every test of a touched test file.
///
/// `root` is the work tree: it supplies file text for the `#[test]` attribute
/// scan and `Cargo.toml` files for package ownership. The result is sorted and
/// free of duplicates.
pub fn select_tests(root: &Path, graph: &SymbolGraph, touched: &TouchedSet) -> Vec<TestTarget> {
    let mut sources = Sources::new(root);
    let mut reach: BTreeSet<Symref> = BTreeSet::new();
    let all_seeds = seeds(graph, touched);
    for seed in &all_seeds {
        reach.extend(graph.affects(seed));
    }
    reach.extend(name_callers(graph, &mut sources, &all_seeds));
    reach.extend(all_seeds);
    for rec in graph.records() {
        if is_test_file(rec.symref.path()) && touched.files.iter().any(|f| f == rec.symref.path()) {
            reach.insert(rec.symref.clone());
        }
    }
    let mut packages = Packages::new(root);
    let mut out: BTreeSet<TestTarget> = BTreeSet::new();
    for symref in &reach {
        let Some(rec) = graph.get(symref) else {
            continue;
        };
        if rec.kind != SymbolKind::Function {
            continue;
        }
        if !is_test_fn(rec, sources.get(rec.symref.path())) {
            continue;
        }
        if let Some(target) = target_of(&mut packages, rec) {
            out.insert(target);
        } else {
            tracing::warn!(symref = %rec.symref, "test function has no owning cargo package; skipped");
        }
    }
    tracing::info!(
        touched = touched.symbols.len(),
        selected = out.len(),
        "tests selected"
    );
    out.into_iter().collect()
}

fn target_of(packages: &mut Packages, rec: &SymbolRecord) -> Option<TestTarget> {
    let (package, rel) = packages.owner(rec.symref.path())?;
    Some(TestTarget {
        package,
        test_path: test_name(rec, &rel),
        symref: rec.symref.to_string(),
    })
}
