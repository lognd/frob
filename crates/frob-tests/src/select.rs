//! Test selection: which test functions can see the touched symbols.

use std::collections::BTreeSet;
use std::path::Path;

use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord, Symref};
use schemars::JsonSchema;
use serde::Serialize;

use crate::catalog::{Packages, is_test_file, is_test_fn, test_name};
use crate::node::{JsMember, JsMembers};
use crate::reach::{Sources, name_callers};
use crate::touched::TouchedSet;

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// The runner that executes a test.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Framework {
    /// `cargo nextest run`: Rust tests.
    Nextest,
    /// `pytest`: Python tests.
    Pytest,
    /// `vitest run`: TypeScript tests of a member that uses vitest.
    Vitest,
    /// `jest`: TypeScript tests of a member that uses jest.
    Jest,
}

/// One selected test: the runner, the owning package and the name the runner knows it by.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, JsonSchema)]
pub struct TestTarget {
    /// Which runner executes it.
    pub framework: Framework,
    /// Cargo package name (`-p`); the member directory (empty at the root) for vitest and jest; empty for pytest.
    pub package: String,
    /// The test's name inside its binary (`tests::doubles`, `integration_quad`), its pytest node id (`tests/test_a.py::TestC::test_m`), or its vitest or jest node id (`src/a.test.ts::suite$s::test$t`).
    pub test_path: String,
    /// The test function's symref.
    pub symref: String,
}

impl TestTarget {
    /// One plan line: `package test_path` for nextest, `pytest node_id` for pytest, `vitest node_id` or `jest node_id` for TypeScript.
    pub fn plan_line(&self) -> String {
        match self.framework {
            Framework::Nextest => format!("{} {}", self.package, self.test_path),
            Framework::Pytest => format!("pytest {}", self.test_path),
            // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
            Framework::Vitest => format!("vitest {}", self.test_path),
            Framework::Jest => format!("jest {}", self.test_path),
        }
    }
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
    let mut members = JsMembers::new(root);
    let mut out: BTreeSet<TestTarget> = BTreeSet::new();
    for symref in &reach {
        let Some(rec) = graph.get(symref) else {
            continue;
        };
        // frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
        if !matches!(rec.kind, SymbolKind::Function | SymbolKind::Method) {
            continue;
        }
        if !is_test_fn(rec, sources.get(rec.symref.path())) {
            continue;
        }
        if gob_symbols::is_typescript_path(rec.symref.path()) {
            // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
            let text = sources.get(rec.symref.path());
            if let Some(member) = members.resolve(rec.symref.path(), text) {
                out.insert(js_target(rec, &member));
            }
            continue;
        }
        let target = if gob_symbols::is_python_path(rec.symref.path()) {
            Some(python_target(rec))
        } else {
            target_of(&mut packages, rec)
        };
        if let Some(target) = target {
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

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The vitest or jest target of a TypeScript test unit: the file path then its unit names (`suite$s` then `test$t`), as `::` segments.
fn js_target(rec: &SymbolRecord, member: &JsMember) -> TestTarget {
    TestTarget {
        framework: member.framework,
        package: member.dir.clone(),
        test_path: node_id(rec),
        symref: rec.symref.to_string(),
    }
}

/// The node id of a TypeScript test unit: `src/a.test.ts::suite$s::test$t`.
pub(crate) fn node_id(rec: &SymbolRecord) -> String {
    let mut node = rec.symref.path().to_owned();
    for seg in rec.symref.segments() {
        node.push_str("::");
        node.push_str(seg);
    }
    node
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// The pytest target of a Python test: its node id is the file path then the class and function names.
fn python_target(rec: &SymbolRecord) -> TestTarget {
    let mut node = rec.symref.path().to_owned();
    for seg in rec.symref.segments() {
        node.push_str("::");
        node.push_str(seg);
    }
    TestTarget {
        framework: Framework::Pytest,
        package: String::new(),
        test_path: node,
        symref: rec.symref.to_string(),
    }
}

fn target_of(packages: &mut Packages, rec: &SymbolRecord) -> Option<TestTarget> {
    let (package, rel) = packages.owner(rec.symref.path())?;
    Some(TestTarget {
        framework: Framework::Nextest,
        package,
        test_path: test_name(rec, &rel),
        symref: rec.symref.to_string(),
    })
}
