//! The Python adapter end to end: a small package with pytest tests, folded and linked into the graph.

use std::path::{Path, PathBuf};

use gob_symbols::{
    CallEdge, EdgeKind, FileSymbols, GapReason, Status, SymbolGraph, SymbolKind, Symref,
    extract_file, is_python_test_fn,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn repo_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus/python/repo")
}

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

/// Every fixture file extracted under its repo-relative path.
fn files() -> Vec<FileSymbols> {
    let mut out = Vec::new();
    let mut stack = vec![repo_dir()];
    while let Some(d) = stack.pop() {
        for e in std::fs::read_dir(&d).expect("read_dir").flatten() {
            let p = e.path();
            if p.is_dir() {
                stack.push(p);
                continue;
            }
            let rel = p
                .strip_prefix(repo_dir())
                .expect("under repo")
                .to_string_lossy()
                .replace('\\', "/");
            let text = std::fs::read_to_string(&p).expect("read");
            out.push(extract_file(&entry(&rel, &text), &text));
        }
    }
    out
}

fn graph() -> SymbolGraph {
    SymbolGraph::from_files(files())
}

fn sym(s: &str) -> Symref {
    Symref::parse(s).expect("symref")
}

fn status_of(g: &SymbolGraph, from: &str, to: &str) -> Option<Status> {
    g.edges_with_status()
        .iter()
        .find(|e| {
            e.kind == EdgeKind::Calls
                && e.from.to_string() == from
                && e.to.as_ref().is_some_and(|t| t.to_string() == to)
        })
        .map(|e| e.status)
}

#[test]
// frob:tests crates/gob-symbols/src/python.rs::fold_tree
fn the_package_yields_modules_classes_methods_and_functions() {
    let fs = files();
    let model = fs
        .iter()
        .find(|f| f.path == "pkg/model.py")
        .expect("model.py");
    let got: Vec<(String, SymbolKind)> = model
        .symbols
        .iter()
        .map(|s| (s.symref.to_string(), s.kind))
        .collect();
    assert_eq!(
        got,
        [
            ("pkg/model.py::Base".to_owned(), SymbolKind::Class),
            ("pkg/model.py::Base.run".to_owned(), SymbolKind::Method),
            ("pkg/model.py::Thing".to_owned(), SymbolKind::Class),
            (
                "pkg/model.py::Thing.__init__".to_owned(),
                SymbolKind::Method
            ),
            ("pkg/model.py::Thing.go".to_owned(), SymbolKind::Method),
            ("pkg/model.py::Thing.step".to_owned(), SymbolKind::Method),
        ]
    );
    assert!(model.parse_status.is_complete());
    assert_eq!(model.fidelity, gob_symbols::Fidelity::F2);
}

#[test]
// frob:tests crates/gob-symbols/src/graph/python.rs::SymbolGraph.resolve_python
fn imports_and_self_calls_resolve_to_must_edges() {
    let g = graph();
    assert_eq!(
        status_of(&g, "pkg/model.py::Thing.go", "pkg/model.py::Thing.step"),
        Some(Status::Must)
    );
    assert_eq!(
        status_of(&g, "pkg/model.py::Thing.go", "pkg/util.py::helper"),
        Some(Status::Must),
        "from .util import helper"
    );
    assert_eq!(
        status_of(&g, "pkg/model.py::Thing.step", "pkg/util.py::helper"),
        Some(Status::Must),
        "from . import util; util.helper()"
    );
    assert_eq!(
        status_of(&g, "pkg/util.py::helper", "pkg/util.py::_twice"),
        Some(Status::Must)
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/python.rs::SymbolGraph.resolve_python
fn tests_reach_through_constructors_reexports_and_unknown_receivers() {
    let g = graph();
    assert_eq!(
        status_of(
            &g,
            "tests/test_model.py::test_go",
            "pkg/model.py::Thing.__init__"
        ),
        Some(Status::Must),
        "Thing(1) is its __init__"
    );
    assert_eq!(
        status_of(&g, "tests/test_model.py::test_go", "pkg/model.py::Thing.go"),
        Some(Status::May),
        "t.go() is a call on a value of unknown type"
    );
    assert_eq!(
        status_of(
            &g,
            "tests/test_model.py::TestThing.test_helper",
            "pkg/util.py::helper"
        ),
        Some(Status::Must),
        "from pkg import helper, re-exported by pkg/__init__.py"
    );
    let reach = g.reach(&sym("tests/test_model.py::test_go"), EdgeKind::Calls);
    assert!(reach.iter().any(|s| s.to_string() == "pkg/util.py::_twice"));
}

#[test]
// frob:tests crates/gob-symbols/src/graph/python.rs::SymbolGraph.resolve_python
fn local_dynamic_and_external_callees_are_unknown_never_clean() {
    let g = graph();
    let mut reasons: Vec<(String, Option<GapReason>)> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.from.to_string() == "pkg/dyn.py::apply" && e.status == Status::Unknown)
        .map(|e| (e.name.clone().unwrap_or_default(), e.reason))
        .collect();
    reasons.sort_by(|a, b| a.0.cmp(&b.0));
    assert_eq!(
        reasons,
        [
            ("<dynamic>".to_owned(), Some(GapReason::Dynamic)),
            ("fn".to_owned(), Some(GapReason::LocalValue)),
            ("getcwd".to_owned(), Some(GapReason::Unbound)),
        ]
    );
    assert!(
        g.call_edges()
            .iter()
            .any(|e| matches!(e, CallEdge::Unresolved { caller, .. } if caller.to_string() == "pkg/dyn.py::apply"))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/python.rs::SymbolGraph.link_python_imports
fn imports_link_files_and_symbols() {
    let g = graph();
    let imports: Vec<String> = g
        .reach(&sym("tests/test_model.py"), EdgeKind::Imports)
        .iter()
        .map(ToString::to_string)
        .collect();
    assert!(
        imports.contains(&"pkg/model.py::Thing".to_owned()),
        "{imports:?}"
    );
    assert!(
        imports.contains(&"pkg/util.py::helper".to_owned()),
        "through the re-export in pkg/__init__.py: {imports:?}"
    );
}

#[test]
// frob:tests crates/gob-symbols/src/python.rs::is_python_test_fn
fn pytest_functions_and_test_class_methods_are_tests() {
    let g = graph();
    let mut tests: Vec<String> = g
        .records()
        .filter(|r| is_python_test_fn(r))
        .map(|r| r.symref.to_string())
        .collect();
    tests.sort();
    assert_eq!(
        tests,
        [
            "tests/test_model.py::TestThing.test_helper",
            "tests/test_model.py::test_go"
        ]
    );
}
