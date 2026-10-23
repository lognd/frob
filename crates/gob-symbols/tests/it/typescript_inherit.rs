//! Annotated TypeScript receivers dispatch through interfaces and inheritance: the declaring method, nearest first.

// frob:ticket 01M5HMPQB3WG50FBPZ3TQNJ1XC

use gob_symbols::{
    EdgeKind, FileSymbols, Status, SymbolGraph, TypeFacts, TypesTrust, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn extract(path: &str, src: &str) -> FileSymbols {
    let entry = FileEntry {
        path: path.to_owned(),
        size: src.len() as u64,
        digest: Digest::of(src.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    extract_file(&entry, src)
}

/// The `Calls` edges out of `go` in a repository of `srcs`, every file tsc-clean.
fn calls_in(srcs: &[(&str, &str)]) -> Vec<(Option<String>, Status)> {
    let files: Vec<FileSymbols> = srcs.iter().map(|(p, s)| extract(p, s)).collect();
    let mut facts = TypeFacts::new(TypesTrust::Checked);
    for (p, _) in srcs {
        facts.mark_clean(p);
    }
    let g = SymbolGraph::from_files_typed(files, facts);
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string().ends_with("go"))
        .map(|e| (e.to.as_ref().map(ToString::to_string), e.status))
        .collect()
}

fn one(src: &str) -> Vec<(Option<String>, Status)> {
    calls_in(&[("m.ts", src)])
}

/// Asserts exactly one Must call edge to a symbol ending in `suffix`.
fn assert_sole(got: &[(Option<String>, Status)], suffix: &str) {
    assert_eq!(got.len(), 1, "{got:?}");
    assert_eq!(got[0].1, Status::Must, "{got:?}");
    assert!(
        got[0].0.as_deref().is_some_and(|t| t.ends_with(suffix)),
        "want {suffix}: {got:?}"
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_typed_method
fn interface_receiver_links_to_interface_method() {
    let got = one(
        "interface Runner { run(): void }\nclass A implements Runner { run(): void {} }\nclass B implements Runner { run(): void {} }\nfunction go(x: Runner) { x.run(); }\n",
    );
    assert_sole(&got, "Runner.run");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_typed_method
fn derived_receiver_links_to_inherited_method() {
    let got = one(
        "class Base { run(): void {} }\nclass Other { run(): void {} }\nclass D extends Base {}\nfunction go(x: D) { x.run(); }\n",
    );
    assert_sole(&got, "Base.run");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_member
fn inheritance_prefers_the_override_and_walks_several_levels() {
    let src = "class Base { run(): void {} }\nclass D extends Base { run(): void {} }\nclass E extends D {}\nclass F extends E {}\n";
    assert_sole(
        &one(&format!("{src}function go(x: D) {{ x.run(); }}\n")),
        "D.run",
    );
    assert_sole(
        &one(&format!("{src}function go(x: Base) {{ x.run(); }}\n")),
        "Base.run",
    );
    assert_sole(
        &one(&format!("{src}function go(x: F) {{ x.run(); }}\n")),
        "D.run",
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_member
fn interface_extends_chains_diamonds_and_optional_methods() {
    let chain = "interface A { run(): void }\ninterface B extends A {}\ninterface C extends B {}\nfunction go(x: C) { x.run(); }\n";
    assert_sole(&one(chain), "A.run");
    let diamond = "interface A { run(): void }\ninterface B extends A {}\ninterface C extends A {}\ninterface D extends B, C {}\nfunction go(x: D) { x.run(); }\n";
    assert_sole(&one(diamond), "A.run");
    let optional =
        "interface A { run?(): void }\ninterface B extends A {}\nfunction go(x: B) { x.run!(); }\n";
    assert_sole(&one(optional), "A.run");
    let two = "interface A { run(): void }\ninterface B { run(): void }\ninterface C extends A, B {}\nfunction go(x: C) { x.run(); }\n";
    let got = one(two);
    assert_eq!(got.len(), 2, "{got:?}");
    assert!(got.iter().all(|g| g.1 == Status::May), "{got:?}");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_member
fn class_prefers_its_extends_chain_over_implemented_interfaces() {
    let got = one(
        "interface I { run(): void }\nclass Base { run(): void {} }\nclass D extends Base implements I {}\nfunction go(x: D) { x.run(); }\n",
    );
    assert_sole(&got, "Base.run");
    let via_interface = one(
        "interface I { run(): void }\nclass D implements I {}\nfunction go(x: D) { x.run(); }\n",
    );
    assert_sole(&via_interface, "I.run");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_type_nodes
fn generic_annotations_and_bases_resolve_by_their_simple_name() {
    let got = one(
        "interface Box<T> { get(): T }\nclass Base<T> { get(): T { throw 1; } }\nclass D<T> extends Base<T> {}\nclass Q extends Base<string> {}\nfunction go(x: Q) { x.get(); }\n",
    );
    assert_sole(&got, "Base.get");
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_member
fn cyclic_heritage_terminates_and_falls_back() {
    let got = one(
        "interface A extends B {}\ninterface B extends A {}\nclass C { run(): void {} }\nfunction go(x: A) { x.run(); }\n",
    );
    assert!(
        got.iter().all(|g| g.1 == Status::May),
        "no exact claim from a cycle: {got:?}"
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_unknown_receiver
fn unannotated_receivers_stay_unresolved_and_never_reach_interface_methods() {
    let got = one(
        "interface Runner { run(): void }\nclass A { run(): void {} }\nfunction go(x) { x.run(); }\n",
    );
    assert!(got.iter().all(|g| g.1 == Status::May), "{got:?}");
    assert!(
        got.iter()
            .all(|g| g.0.as_deref().is_none_or(|t| !t.ends_with("Runner.run"))),
        "{got:?}"
    );
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_type_nodes
fn bases_resolve_through_imports_in_another_file() {
    let got = calls_in(&[
        (
            "base.ts",
            "export class Base { run(): void {} }\nexport interface Run { stop(): void }\n",
        ),
        (
            "m.ts",
            "import { Base, Run } from './base';\nclass D extends Base {}\ninterface R2 extends Run {}\nfunction go(x: D, y: R2) { x.run(); y.stop(); }\n",
        ),
    ]);
    assert_eq!(got.len(), 2, "{got:?}");
    assert!(got.iter().all(|g| g.1 == Status::Must), "{got:?}");
    let targets: Vec<&str> = got.iter().filter_map(|g| g.0.as_deref()).collect();
    assert!(
        targets.iter().any(|t| t.ends_with("Base.run")),
        "{targets:?}"
    );
    assert!(
        targets.iter().any(|t| t.ends_with("Run.stop")),
        "{targets:?}"
    );
}
