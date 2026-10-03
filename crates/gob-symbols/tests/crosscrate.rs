//! Cross-crate path resolution through `use` imports and the Cargo dependency closure.

// frob:ticket 01M3ZR5KCPY3E3NFCVFS404RDJ

use std::path::Path;

use gob_cache::Cache;
use gob_symbols::{CallEdge, EdgeKind, Status, SymbolGraph, build_graph};
use gob_walk::{WalkConfig, walk};

/// Writes `files` under `root` and builds the graph the way `frob check` does.
fn graph_in(root: &Path, files: &[(&str, &str)]) -> SymbolGraph {
    for (path, text) in files {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
    let walked = walk(root, &WalkConfig::default()).expect("walk");
    build_graph(root, &walked.files, &Cache::null())
}

const ROOT: (&str, &str) = ("Cargo.toml", "[workspace]\nmembers = [\"crates/*\"]\n");
const A_TOML: (&str, &str) = (
    "crates/a/Cargo.toml",
    "[package]\nname = \"a-lib\"\n\n[dependencies]\n",
);
const B_TOML: (&str, &str) = (
    "crates/b/Cargo.toml",
    "[package]\nname = \"b-app\"\n\n[dependencies]\na-lib = { path = \"../a\" }\n",
);
const C_TOML: (&str, &str) = ("crates/c/Cargo.toml", "[package]\nname = \"c-app\"\n");
const A_LIB: (&str, &str) = (
    "crates/a/src/lib.rs",
    "mod inputs;\npub mod util;\npub use inputs::Inputs;\npub use util::run;\n",
);
const A_INPUTS: (&str, &str) = (
    "crates/a/src/inputs.rs",
    "pub struct Inputs;\nimpl Inputs {\n    pub fn collect() {}\n    pub fn go(&self) {}\n}\n",
);
const A_UTIL: (&str, &str) = ("crates/a/src/util.rs", "pub fn run() {}\n");

/// Every call edge of `g` from a caller ending in `caller`: (callee, status).
fn calls_of(g: &SymbolGraph, caller: &str) -> Vec<(String, Status)> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string().ends_with(caller))
        .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
        .collect()
}

/// True when `caller` has an unresolved (Unknown) call edge.
fn has_unknown(g: &SymbolGraph, caller: &str) -> bool {
    g.edges_with_status().iter().any(|e| {
        e.kind == EdgeKind::Calls
            && e.status == Status::Unknown
            && e.from.to_string().ends_with(caller)
    })
}

fn tmp() -> tempfile::TempDir {
    tempfile::tempdir().expect("tempdir")
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn use_import_resolves_an_associated_function_in_another_crate() {
    let dir = tmp();
    let t = "use a_lib::Inputs;\n#[test]\nfn t() { Inputs::collect(); }\n";
    let g = graph_in(
        dir.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            A_LIB,
            A_INPUTS,
            A_UTIL,
            ("crates/b/tests/t.rs", t),
        ],
    );
    assert_eq!(
        calls_of(&g, "tests/t.rs::t"),
        [(
            "crates/a/src/inputs.rs::Inputs.collect".to_owned(),
            Status::Must
        )],
        "re-exported through `pub use inputs::Inputs`, one candidate, Must"
    );
    assert!(g.call_edges().iter().any(|e| matches!(
        e,
        CallEdge::Resolved { callee, .. } if callee.to_string().ends_with("Inputs.collect")
    )));
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn module_path_import_and_own_crate_integration_tests_resolve() {
    let dir = tmp();
    let a_lib = (
        "crates/a/src/lib.rs",
        "pub mod inputs;\npub mod util;\npub use util::run;\n",
    );
    let long = "use a_lib::inputs::Inputs;\n#[test]\nfn t() { Inputs::collect(); }\n";
    let own = "use a_lib::Inputs;\n#[test]\nfn own() { Inputs::collect(); }\n";
    let own_lib = (
        "crates/a/src/lib.rs",
        "pub mod inputs;\npub use inputs::Inputs;\n",
    );
    let g = graph_in(
        dir.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            a_lib,
            A_INPUTS,
            A_UTIL,
            ("crates/b/tests/t.rs", long),
        ],
    );
    assert_eq!(
        calls_of(&g, "tests/t.rs::t"),
        [(
            "crates/a/src/inputs.rs::Inputs.collect".to_owned(),
            Status::Must
        )]
    );
    let dir2 = tmp();
    let g2 = graph_in(
        dir2.path(),
        &[
            ROOT,
            A_TOML,
            own_lib,
            A_INPUTS,
            ("crates/a/tests/own.rs", own),
        ],
    );
    assert_eq!(
        calls_of(&g2, "tests/own.rs::own"),
        [(
            "crates/a/src/inputs.rs::Inputs.collect".to_owned(),
            Status::Must
        )],
        "an integration test names its own crate by package name"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn imported_functions_and_typed_receivers_resolve_across_crates() {
    let dir = tmp();
    let t = "use a_lib::{Inputs, run};\n\
             #[test]\nfn t() { run(); }\n\
             fn user(i: &Inputs) { i.go(); }\n";
    let g = graph_in(
        dir.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            A_LIB,
            A_INPUTS,
            A_UTIL,
            ("crates/b/tests/t.rs", t),
        ],
    );
    assert_eq!(
        calls_of(&g, "tests/t.rs::t"),
        [("crates/a/src/util.rs::run".to_owned(), Status::Must)]
    );
    assert_eq!(
        calls_of(&g, "tests/t.rs::user"),
        [("crates/a/src/inputs.rs::Inputs.go".to_owned(), Status::Must)]
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn glob_import_resolves_only_when_it_is_the_files_sole_glob() {
    let dir = tmp();
    let sole = "use a_lib::*;\n#[test]\nfn t() { Inputs::collect(); }\n";
    let g = graph_in(
        dir.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            A_LIB,
            A_INPUTS,
            A_UTIL,
            ("crates/b/tests/t.rs", sole),
        ],
    );
    assert_eq!(
        calls_of(&g, "tests/t.rs::t"),
        [(
            "crates/a/src/inputs.rs::Inputs.collect".to_owned(),
            Status::Must
        )]
    );
    // A second glob could shadow or also define `Inputs`: stays May.
    let dir2 = tmp();
    let two = "use a_lib::*;\nuse other::*;\n#[test]\nfn t() { Inputs::collect(); }\n";
    let g2 = graph_in(
        dir2.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            A_LIB,
            A_INPUTS,
            A_UTIL,
            ("crates/b/tests/t.rs", two),
        ],
    );
    assert_eq!(
        calls_of(&g2, "tests/t.rs::t"),
        [(
            "crates/a/src/inputs.rs::Inputs.collect".to_owned(),
            Status::May
        )],
        "an ambiguous glob never becomes Must"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn ambiguous_or_unlinked_cross_crate_calls_never_resolve() {
    let dir = tmp();
    // Two `collect` functions behind one name: an inherent one and a trait impl.
    let inputs = "pub struct Inputs;\n\
                  impl Inputs { pub fn collect() {} }\n\
                  pub trait Collect { fn collect(); }\n\
                  impl Collect for Inputs { fn collect() {} }\n";
    let t = "use a_lib::Inputs;\n#[test]\nfn t() { Inputs::collect(); }\n";
    let g = graph_in(
        dir.path(),
        &[
            ROOT,
            A_TOML,
            B_TOML,
            A_LIB,
            ("crates/a/src/inputs.rs", inputs),
            A_UTIL,
            ("crates/b/tests/t.rs", t),
        ],
    );
    let calls = calls_of(&g, "tests/t.rs::t");
    assert_eq!(calls.len(), 2, "{calls:?}");
    assert!(calls.iter().all(|(_, s)| *s == Status::May), "{calls:?}");
    assert!(
        !g.call_edges()
            .iter()
            .any(|e| matches!(e, CallEdge::Resolved { caller, .. } if caller.to_string().ends_with("tests/t.rs::t"))),
        "two candidates are never a Resolved edge"
    );
    // A crate that does not depend on a-lib cannot call into it.
    let dir2 = tmp();
    let g2 = graph_in(
        dir2.path(),
        &[
            ROOT,
            A_TOML,
            C_TOML,
            A_LIB,
            A_INPUTS,
            A_UTIL,
            ("crates/c/tests/t.rs", t),
        ],
    );
    assert!(calls_of(&g2, "tests/t.rs::t").is_empty());
    assert!(has_unknown(&g2, "tests/t.rs::t"));
}

// frob:ticket 01M3ZVQA77ZEK9DXEN5Z0XMZEG
// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps
#[test]
fn unknown_receiver_call_poisons_same_named_methods_in_dependency_crates() {
    let dir = tmp();
    // c-app -> b-app -> a-lib; each defines `m(&self)` (and `d` is a different arity).
    let c_toml = (
        "crates/c/Cargo.toml",
        "[package]\nname = \"c-app\"\n\n[dependencies]\nb-app = { path = \"../b\" }\n",
    );
    let a = (
        "crates/a/src/lib.rs",
        "pub struct A;\nimpl A {\n    pub fn m(&self) {}\n    pub fn two(&self, _x: u8) {}\n}\n",
    );
    let b = (
        "crates/b/src/lib.rs",
        "pub struct B;\nimpl B {\n    pub fn m(&self) {}\n}\n",
    );
    let c = (
        "crates/c/src/lib.rs",
        "pub struct C;\nimpl C {\n    pub fn m(&self) {}\n}\npub fn go() { make().m(); }\n",
    );
    let g = graph_in(dir.path(), &[ROOT, A_TOML, B_TOML, c_toml, a, b, c]);
    let mut calls = calls_of(&g, "crates/c/src/lib.rs::go");
    calls.sort();
    let want = [
        "a/src/lib.rs::A.m",
        "b/src/lib.rs::B.m",
        "c/src/lib.rs::C.m",
    ];
    assert_eq!(calls.len(), 3, "{calls:?}");
    for (w, (got, status)) in want.iter().zip(&calls) {
        assert!(got.ends_with(w), "{got} vs {w}");
        assert_eq!(*status, Status::May, "{got}");
    }
    assert!(
        !g.call_edges()
            .iter()
            .any(|e| matches!(e, CallEdge::Resolved { .. })),
        "an unknown receiver never yields a Resolved edge"
    );
    // A crate that links nothing is not given the other crates' methods.
    let g2 = graph_in(
        dir.path(),
        &[(
            "crates/a/src/lib.rs",
            "pub fn lone() { make().m(); }\npub struct A;\nimpl A { pub fn m(&self) {} }\n",
        )],
    );
    let own = calls_of(&g2, "crates/a/src/lib.rs::lone");
    assert_eq!(own.len(), 1, "{own:?}");
}
