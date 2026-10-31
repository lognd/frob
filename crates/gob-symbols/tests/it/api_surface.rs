//! Small public builders and predicates, each pinned by a direct test.

// frob:ticket 01M61CD6Q7ZBB2B4YDXST6JQTK

use gob_symbols::{
    CallQualifier, Capability, CapabilityDecl, CrateDeps, Digests, EdgeKind, FacetDigest, Lang,
    Precision, Status, SymbolGraph, Symref, TypeFacts, UnityAssembly, UnityTestMode, extract_file,
    is_html_path,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn ts_files(files: &[(&str, &str)]) -> Vec<gob_symbols::FileSymbols> {
    files
        .iter()
        .map(|(p, s)| extract_file(&entry(p, s), s))
        .collect()
}

fn assembly(defines: &[&str], refs: &[&str], dir: &str, platforms: &[&str]) -> UnityAssembly {
    let strings = |xs: &[&str]| xs.iter().map(|s| (*s).to_owned()).collect::<Vec<_>>();
    UnityAssembly {
        id: format!("{dir}/A.asmdef"),
        name: "A".to_owned(),
        dir: dir.to_owned(),
        guid: None,
        references: strings(refs),
        include_platforms: strings(platforms),
        exclude_platforms: Vec::new(),
        define_constraints: strings(defines),
        precompiled_references: Vec::new(),
        override_references: false,
        auto_referenced: true,
        allow_unsafe_code: false,
        external: Vec::new(),
    }
}

// frob:tests crates/gob-symbols/src/adapter.rs::CapabilityDecl.with
#[test]
fn capability_decl_with_replaces_an_earlier_declaration() {
    let base = CapabilityDecl::for_lang(Lang::Rust);
    let once = base
        .clone()
        .with(Capability::ResolveRef, Precision::Lexical);
    let twice = once.clone().with(Capability::ResolveRef, Precision::None);
    assert_eq!(once.precision(Capability::ResolveRef), Precision::Lexical);
    assert_eq!(twice.precision(Capability::ResolveRef), Precision::None);
    assert_eq!(twice.rows().len(), base.rows().len());
}

// frob:tests crates/gob-symbols/src/model.rs::Digests.of_facets
#[test]
fn digests_of_facets_hashes_three_facets_and_leaves_two_empty() {
    let d = Digests::of_facets("sig", "body", "doc");
    assert_eq!(d.sig, FacetDigest::of(b"sig"));
    assert_eq!(d.body, FacetDigest::of(b"body"));
    assert_eq!(d.doc, FacetDigest::of(b"doc"));
    assert_eq!(d.attr, FacetDigest::of(b""));
    assert_eq!(d.contract, FacetDigest::of(b""));
}

// frob:tests crates/gob-symbols/src/qualifier.rs::CallQualifier.describe
#[test]
fn call_qualifier_describe_names_each_shape() {
    assert_eq!(CallQualifier::Path("m".into()).describe(), "path `m::`");
    assert_eq!(
        CallQualifier::SelfType("T".into()).describe(),
        "`self.` in `T`"
    );
    assert_eq!(
        CallQualifier::Typed("T".into()).describe(),
        "receiver of type `T`"
    );
    assert_eq!(
        CallQualifier::Receiver { args: None }.describe(),
        "receiver of unknown type"
    );
}

// frob:tests crates/gob-symbols/src/symref.rs::Symref.with_path
// frob:tests crates/gob-symbols/src/symref.rs::Symref.with_segments
#[test]
fn symref_with_path_and_with_segments_rewrite_one_part() {
    let s = Symref::parse("a/b.rs::Foo.bar").expect("parses");
    assert_eq!(s.with_path("c/d.rs").to_string(), "c/d.rs::Foo.bar");
    assert_eq!(
        s.with_segments(vec!["Baz".to_owned(), "q".to_owned()])
            .to_string(),
        "a/b.rs::Baz.q"
    );
}

// frob:tests crates/gob-symbols/src/html/mod.rs::is_html_path
#[test]
fn is_html_path_matches_html_and_htm_in_any_case() {
    assert!(is_html_path("site/index.html"));
    assert!(is_html_path("INDEX.HTM"));
    assert!(!is_html_path("index.htmx"));
    assert!(!is_html_path("html"));
}

// frob:tests crates/gob-symbols/src/unity_project.rs::Assembly.is_test
// frob:tests crates/gob-symbols/src/unity_project.rs::Assembly.test_mode
#[test]
fn unity_assembly_is_test_and_test_mode_follow_constraint_and_directory() {
    let refs = ["UnityEngine.TestRunner"];
    let play = assembly(
        &["UNITY_INCLUDE_TESTS"],
        &refs,
        "Assets/Tests/PlayMode",
        &[],
    );
    let edit = assembly(
        &["UNITY_INCLUDE_TESTS"],
        &refs,
        "Assets/Tests/EditMode",
        &[],
    );
    let editor = assembly(&["UNITY_INCLUDE_TESTS"], &refs, "Assets/Tests", &["Editor"]);
    let plain = assembly(&[], &refs, "Assets/Tests", &[]);
    assert!(play.is_test());
    assert_eq!(play.test_mode(), Some(UnityTestMode::PlayMode));
    assert_eq!(edit.test_mode(), Some(UnityTestMode::EditMode));
    assert_eq!(editor.test_mode(), Some(UnityTestMode::EditMode));
    assert!(!plain.is_test());
    assert_eq!(plain.test_mode(), None);
}

// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_import_targets
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_import_source
#[test]
fn ts_import_targets_and_source_answer_for_a_named_import() {
    let g = SymbolGraph::from_files(ts_files(&[
        ("a.ts", "export function x() { return 1; }\n"),
        ("b.ts", "import { x } from './a';\nx();\n"),
    ]));
    let targets = g.ts_import_targets("b.ts", "x");
    assert!(
        targets
            .iter()
            .any(|(s, st)| s.to_string() == "a.ts::x" && *st == Status::Must),
        "{targets:?}"
    );
    assert!(g.ts_import_targets("b.ts", "nope").is_empty());
    assert_eq!(
        g.ts_import_source("b.ts", "x"),
        Some(("./a".to_owned(), "x".to_owned()))
    );
    assert_eq!(g.ts_import_source("b.ts", "nope"), None);
    assert!(
        g.edges_with_status()
            .iter()
            .any(|e| e.kind == EdgeKind::Imports)
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps_typed
#[test]
fn from_files_with_deps_typed_builds_the_same_graph_as_untyped_without_facts() {
    let files = || ts_files(&[("m.py", "def f():\n    pass\n\ndef g():\n    f()\n")]);
    let typed = SymbolGraph::from_files_with_deps_typed(
        files(),
        &mut CrateDeps::new(std::path::Path::new(".")),
        TypeFacts::default(),
    );
    let plain =
        SymbolGraph::from_files_with_deps(files(), &mut CrateDeps::new(std::path::Path::new(".")));
    assert_eq!(
        typed.edges_with_status().len(),
        plain.edges_with_status().len()
    );
    assert!(!typed.edges_with_status().is_empty());
}
