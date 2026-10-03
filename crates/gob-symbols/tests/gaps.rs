//! One test per landed-code gap closed by the U adapters (universal-model.md 7,
//! lint-requirements.md section 9), each named after its gap.

use gob_ir::{Operator, Universal};
use gob_symbols::{
    CallEdge, EdgeKind, Fidelity, FileSymbols, GapReason, ParseStatus, RefKind, Status,
    SymbolGraph, Symref, build_graph_with_stats, extract_file, fold_file,
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

fn extract(path: &str, text: &str) -> FileSymbols {
    extract_file(&entry(path, text), text)
}

fn graph_of(files: &[(&str, &str)]) -> SymbolGraph {
    SymbolGraph::from_files(files.iter().map(|(p, t)| extract(p, t)).collect())
}

fn sym(s: &str) -> Symref {
    Symref::parse(s).unwrap()
}

fn digests(fs: &FileSymbols, s: &str) -> gob_symbols::Digests {
    fs.symbols
        .iter()
        .find(|r| r.symref.to_string() == s)
        .unwrap_or_else(|| panic!("missing {s}"))
        .digests
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.reach_with_status
#[test]
fn g01_unresolved_calls_poison_reach_instead_of_being_dropped() {
    let g = graph_of(&[(
        "c/src/lib.rs",
        "fn a() { b(); mystery(); }\nfn b() {}\nfn clean() { b(); }\n",
    )]);
    let a = sym("c/src/lib.rs::a");
    let reach = g.reach_with_status(&a, &[EdgeKind::Calls]);
    assert_eq!(reach.reached[&sym("c/src/lib.rs::b")], Status::Must);
    assert!(!reach.is_complete(), "mystery() may reach anything");
    assert!(reach.poisoned_by.contains(&a));
    let clean = g.reach_with_status(&sym("c/src/lib.rs::clean"), &[EdgeKind::Calls]);
    assert!(clean.is_complete());
    // The poison travels: a caller of `a` has an incomplete reach too.
    let g2 = graph_of(&[("c/src/lib.rs", "fn top() { a(); }\nfn a() { mystery(); }\n")]);
    let top = g2.reach_with_status(&sym("c/src/lib.rs::top"), &[EdgeKind::Calls]);
    assert!(top.poisoned_by.contains(&sym("c/src/lib.rs::a")));
    let unknown: Vec<_> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.status == Status::Unknown)
        .collect();
    assert_eq!(unknown.len(), 1);
    assert_eq!(unknown[0].name.as_deref(), Some("mystery"));
    assert_eq!(unknown[0].reason, Some(GapReason::Unbound));
    assert!(unknown[0].to.is_none());
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.edges_with_status
#[test]
fn g02_edges_carry_must_may_unknown_status() {
    let src = "struct A;\nimpl A { fn go(&self) {} }\n\
               fn free() {}\nfn user(a: impl Tr) { free(); a.go(); other(); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let status_of = |to: &str| {
        g.edges_with_status()
            .iter()
            .find(|e| e.to.as_ref().is_some_and(|t| t.to_string() == to))
            .map(|e| e.status)
    };
    assert_eq!(status_of("c/src/lib.rs::free"), Some(Status::Must));
    assert_eq!(status_of("c/src/lib.rs::A.go"), Some(Status::May));
    // A single May candidate is still not "Resolved" in the compatibility view.
    assert!(g.call_edges().iter().any(|e| matches!(
        e,
        CallEdge::Ambiguous { candidates, .. } if candidates.len() == 1
    )));
    assert!(
        g.call_edges()
            .iter()
            .any(|e| matches!(e, CallEdge::Resolved { .. }))
    );
}

#[test]
fn g03_calls_of_function_values_are_unknown_not_dropped() {
    let src = "fn run(f: fn()) { f(); }\nfn dynamic() { (make())(); }\nfn make() -> fn() { || {} }\n\
               fn nested() { fn inner() {} inner(); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let gaps = |from: &str| -> Vec<GapReason> {
        g.edges_with_status()
            .iter()
            .filter(|e| e.from.to_string() == from && e.status == Status::Unknown)
            .filter_map(|e| e.reason)
            .collect()
    };
    assert_eq!(gaps("c/src/lib.rs::run"), [GapReason::LocalValue]);
    assert_eq!(gaps("c/src/lib.rs::dynamic"), [GapReason::Dynamic]);
    // A nested fn item is a static, local callee: no edge and no poison.
    assert!(gaps("c/src/lib.rs::nested").is_empty());
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.affects_with_status
#[test]
fn g04_function_passed_as_value_is_a_may_reference_edge() {
    let src = "fn helper() {}\nfn apply(f: fn()) { f(); }\nfn main() { apply(helper); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let helper = sym("c/src/lib.rs::helper");
    let edge = g
        .edges_with_status()
        .iter()
        .find(|e| e.kind == EdgeKind::References && e.to.as_ref() == Some(&helper))
        .expect("reference edge to helper");
    assert_eq!(edge.status, Status::May);
    assert_eq!(edge.from, sym("c/src/lib.rs::main"));
    assert!(g.affects(&helper).contains(&sym("c/src/lib.rs::main")));
    assert_eq!(
        g.affects_with_status(&helper)[&sym("c/src/lib.rs::main")],
        Status::May
    );
    // References are a superset of calls.
    let refs = g.reach(&sym("c/src/lib.rs::main"), EdgeKind::References);
    assert!(refs.contains(&sym("c/src/lib.rs::apply")) && refs.contains(&helper));
    let fs = extract("c/src/lib.rs", src);
    assert!(
        fs.refs
            .iter()
            .any(|r| r.kind == RefKind::Value && r.name == "helper")
    );
}

#[test]
fn g07_outer_attributes_are_in_sig_and_attr_digests() {
    let plain = extract("x.rs", "pub fn f() {}\n");
    let deprecated = extract("x.rs", "#[deprecated]\npub fn f() {}\n");
    let (a, b) = (digests(&plain, "x.rs::f"), digests(&deprecated, "x.rs::f"));
    assert_ne!(a.sig, b.sig, "attributes feed the sig stream");
    assert_ne!(a.attr, b.attr, "attributes have their own facet");
    assert_eq!(a.body, b.body);
    assert_eq!(a.doc, b.doc);
}

#[test]
fn g08_comments_in_a_body_do_not_change_the_body_digest() {
    let a = extract("x.rs", "pub fn f() -> u32 {\n    1 + 2\n}\n");
    let with_comments =
        "pub fn f() -> u32 {\n    // frob:todo T-1\n    1 /* two */ + 2 // trailing\n}\n";
    let b = extract("x.rs", with_comments);
    assert_eq!(digests(&a, "x.rs::f").body, digests(&b, "x.rs::f").body);
    let c = extract("x.rs", "pub fn f() -> u32 {\n    1 + 3\n}\n");
    assert_ne!(digests(&a, "x.rs::f").body, digests(&c, "x.rs::f").body);
}

#[test]
fn g09_markdown_body_is_section_local_with_a_separate_subtree_digest() {
    let a = "# Top\n\nintro\n\n## Child\n\nchild text\n";
    let b = "# Top\n\nintro\n\n## Child\n\nchild text EDITED\n";
    let (fa, fb) = (extract("d.md", a), extract("d.md", b));
    assert_eq!(digests(&fa, "d.md#top").body, digests(&fb, "d.md#top").body);
    assert_ne!(
        digests(&fa, "d.md#child").body,
        digests(&fb, "d.md#child").body
    );
    let sub = |fs: &FileSymbols, s: &str| {
        fs.extras
            .iter()
            .find(|e| e.symref.to_string() == s)
            .and_then(|e| e.subtree)
            .unwrap()
    };
    assert_ne!(sub(&fa, "d.md#top"), sub(&fb, "d.md#top"));
    assert_ne!(sub(&fa, "d.md#child"), sub(&fb, "d.md#child"));
    // Editing the parent's own text leaves the child's digests alone.
    let c = "# Top\n\nintro EDITED\n\n## Child\n\nchild text\n";
    let fc = extract("d.md", c);
    assert_eq!(sub(&fa, "d.md#child"), sub(&fc, "d.md#child"));
    assert_ne!(digests(&fa, "d.md#top").body, digests(&fc, "d.md#top").body);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.public_api
#[test]
fn g10_public_api_follows_pub_use_reexports() {
    let src = "mod inner { pub fn helper() {} pub fn other() {} }\npub use self::inner::helper;\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let api: Vec<String> = g
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    assert!(
        api.contains(&"c/src/lib.rs::inner.helper".to_owned()),
        "{api:?}"
    );
    assert!(
        !api.contains(&"c/src/lib.rs::inner.other".to_owned()),
        "{api:?}"
    );
    let globbed = "mod inner { pub fn helper() {} pub fn other() {} }\npub use self::inner::*;\n";
    let g = graph_of(&[("c/src/lib.rs", globbed)]);
    let api: Vec<String> = g
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    assert!(
        api.contains(&"c/src/lib.rs::inner.other".to_owned()),
        "{api:?}"
    );
    // A private `use` is not a re-export.
    let private = "mod inner { pub fn helper() {} }\nuse self::inner::helper;\n";
    let g = graph_of(&[("c/src/lib.rs", private)]);
    assert!(
        g.public_api()
            .iter()
            .all(|r| r.symref.name() != Some("helper"))
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.file_info
#[test]
fn g11_parse_errors_are_holes_and_parse_status_is_a_query() {
    let broken = "fn ok() {}\nfn broken( {\nfn after() {}\n";
    let folded = fold_file(&entry("x.rs", broken), broken).unwrap();
    let holes = folded
        .term
        .ids()
        .filter(|&n| {
            matches!(
                folded.term.operator(n),
                Operator::Universal(Universal::Hole { .. })
            )
        })
        .count();
    assert!(holes > 0, "syntax errors become hole nodes");
    assert!(matches!(
        folded.file.parse_status,
        ParseStatus::Partial { holes: h } if h as usize == holes
    ));
    let clean = extract("x.rs", "fn ok() {}\n");
    assert_eq!(clean.parse_status, ParseStatus::Complete);
    let g = SymbolGraph::from_files(vec![folded.file]);
    let info = g.file_info("x.rs").unwrap();
    assert!(!info.parse_status.is_complete());
    assert!(!info.degraded, "a tree exists: partial, not degraded");
    // A unit that holds a hole cannot claim a digest for the facet containing it.
    let inner = "fn ok() {}\nfn broken() { let = ; call(; }\n";
    let g = SymbolGraph::from_files(vec![extract("y.rs", inner)]);
    let broken = g.extras(&sym("y.rs::broken")).unwrap();
    assert_eq!(broken.unknown, ["body"]);
    assert!(g.extras(&sym("y.rs::ok")).unwrap().unknown.is_empty());
}

// frob:tests crates/gob-symbols/src/graph.rs::FileInfo.is_opaque
#[test]
fn g19_unknown_language_is_one_opaque_f0_unit() {
    let text = "a,b\n1,2\n";
    let folded = fold_file(&entry("data.csv", text), text).unwrap();
    let root = folded.term.root();
    let kids = folded.term.children(root);
    assert_eq!(kids.len(), 1);
    assert!(matches!(
        folded.term.operator(kids[0]),
        Operator::Universal(Universal::Opaque { reason, .. }) if reason == "no-adapter"
    ));
    let fs = folded.file;
    assert_eq!(fs.fidelity, Fidelity::F0);
    assert_eq!(fs.parse_status, ParseStatus::NotParsed);
    assert!(fs.symbols.is_empty() && !fs.degraded);
    let g = SymbolGraph::from_files(vec![fs]);
    let info = g.file_info("data.csv").unwrap();
    assert!(info.is_opaque(), "distinguishable from an empty Rust file");
    let empty_rs = SymbolGraph::from_files(vec![extract("e.rs", "")]);
    assert!(!empty_rs.file_info("e.rs").unwrap().is_opaque());
    // TOML has a grammar but no adapter: still opaque.
    let toml = extract("Cargo.toml", "[package]\n");
    assert_eq!(toml.fidelity, Fidelity::F0);
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.files
#[test]
fn g19_walked_files_without_an_adapter_are_counted_opaque() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(root.path().join("notes.txt"), "x").unwrap();
    let e = entry("notes.txt", "x");
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = gob_cache::Cache::open(cache_dir.path());
    let (g, stats) = build_graph_with_stats(root.path(), &[e], &cache);
    assert_eq!((stats.opaque, stats.extracted), (1, 0));
    assert!(g.files().any(|(p, i)| p == "notes.txt" && i.is_opaque()));
}

#[test]
fn contract_digest_erases_names_but_sig_keeps_them() {
    let a = extract("x.rs", "pub fn first(a: u32) -> u32 { a }\n");
    let b = extract("x.rs", "pub fn second(zed: u32) -> u32 { zed }\n");
    let (da, db) = (digests(&a, "x.rs::first"), digests(&b, "x.rs::second"));
    assert_eq!(da.contract, db.contract, "contract is name-erased");
    assert_eq!(da.body, db.body);
    let c = extract("x.rs", "pub fn first(a: u64) -> u32 { a }\n");
    assert_ne!(da.contract, digests(&c, "x.rs::first").contract);
}

#[test]
fn imports_pick_the_callee_among_same_named_functions() {
    let g = graph_of(&[
        (
            "c/src/lib.rs",
            "mod a;\nmod b;\nuse crate::a::run;\npub fn go() { run(); }\n",
        ),
        ("c/src/a.rs", "pub fn run() {}\n"),
        ("c/src/b.rs", "pub fn run() {}\n"),
    ]);
    let edge = g
        .edges_with_status()
        .iter()
        .find(|e| e.kind == EdgeKind::Calls)
        .expect("call edge");
    assert_eq!(edge.to, Some(sym("c/src/a.rs::run")));
    assert_eq!(edge.status, Status::Must);
    // Without the import the same call is an ambiguous May.
    let g = graph_of(&[
        ("c/src/lib.rs", "mod a;\nmod b;\npub fn go() { run(); }\n"),
        ("c/src/a.rs", "pub fn run() {}\n"),
        ("c/src/b.rs", "pub fn run() {}\n"),
    ]);
    let calls: Vec<_> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls)
        .collect();
    assert_eq!(calls.len(), 2);
    assert!(calls.iter().all(|e| e.status == Status::May));
}

#[test]
fn markdown_links_resolve_to_anchors_or_are_broken_unknown_edges() {
    let g = graph_of(&[
        (
            "a.md",
            "# A\n\nSee [b](b.md#target), [gone](gone.md), [x](https://x.y).\n",
        ),
        ("b.md", "# B\n\n## Target\n\ntext\n"),
    ]);
    let links: Vec<_> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Links)
        .collect();
    assert_eq!(links.len(), 2, "external links make no edge");
    let ok = links.iter().find(|e| e.status == Status::Must).unwrap();
    assert_eq!(ok.to, Some(Symref::anchor("b.md", "target")));
    let broken = links.iter().find(|e| e.status == Status::Unknown).unwrap();
    assert_eq!(broken.reason, Some(GapReason::BrokenLink));
}
