//! Integration tests: corpus, digest facets, graph queries, cache.

use std::path::{Path, PathBuf};

use gob_cache::Cache;
use gob_symbols::{
    Admit, CallEdge, CallQualifier, EdgeKind, FileSymbols, ResolveError, SymbolGraph, SymbolKind,
    Symref, Visibility, build_graph_with_stats, extract_file,
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

fn find<'a>(fs: &'a FileSymbols, sym: &str) -> &'a gob_symbols::SymbolRecord {
    fs.symbols
        .iter()
        .find(|s| s.symref.to_string() == sym)
        .unwrap_or_else(|| panic!("missing {sym}"))
}

fn corpus_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus")
}

#[test]
fn corpus_matches_expected_symrefs() {
    let mut checked = 0;
    for lang in ["rust", "markdown"] {
        let dir = corpus_dir().join(lang);
        let mut names: Vec<_> = std::fs::read_dir(&dir)
            .unwrap()
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().is_some_and(|e| e == "rs" || e == "md"))
            .collect();
        names.sort();
        for src in names {
            let expected = std::fs::read_to_string(src.with_extension("expected")).unwrap();
            let rel = format!(
                "tests/corpus/{lang}/{}",
                src.file_name().unwrap().to_str().unwrap()
            );
            let text = std::fs::read_to_string(&src).unwrap();
            let got: Vec<String> = extract(&rel, &text)
                .symbols
                .iter()
                .map(|s| s.symref.to_string())
                .collect();
            let want: Vec<&str> = expected.lines().filter(|l| !l.is_empty()).collect();
            assert_eq!(got, want, "symrefs of {rel}");
            checked += 1;
        }
    }
    assert!(checked >= 2);
}

const BASE: &str = "/// Doc one.\npub fn f(a: u32) -> u32 {\n    a + 1\n}\n";

#[test]
fn consistent_param_rename_is_alpha_equivalent_but_a_type_change_is_not() {
    let a = extract("x.rs", BASE);
    let renamed = extract("x.rs", &BASE.replace('a', "b"));
    let (da, db) = (
        find(&a, "x.rs::f").digests,
        find(&renamed, "x.rs::f").digests,
    );
    // Bound variable names are erased by alpha-normality (digest scheme 2).
    assert_eq!(da.sig, db.sig);
    assert_eq!(da.body, db.body);
    let retyped = extract("x.rs", &BASE.replace("a: u32", "a: u64"));
    let dc = find(&retyped, "x.rs::f").digests;
    assert_ne!(da.sig, dc.sig);
    assert_eq!(da.body, dc.body);
    assert_eq!(da.doc, dc.doc);
}

#[test]
fn edit_body_changes_body_only() {
    let a = extract("x.rs", BASE);
    let b = extract("x.rs", &BASE.replace("a + 1", "a + 2"));
    let (da, db) = (find(&a, "x.rs::f").digests, find(&b, "x.rs::f").digests);
    assert_eq!(da.sig, db.sig);
    assert_ne!(da.body, db.body);
    assert_eq!(da.doc, db.doc);
}

#[test]
fn change_doc_changes_doc_only_and_whitespace_is_ignored() {
    let a = extract("x.rs", BASE);
    let b = extract("x.rs", &BASE.replace("Doc one.", "Doc two."));
    let (da, db) = (find(&a, "x.rs::f").digests, find(&b, "x.rs::f").digests);
    assert_eq!(da.sig, db.sig);
    assert_eq!(da.body, db.body);
    assert_ne!(da.doc, db.doc);
    let c = extract(
        "x.rs",
        "/// Doc one.\npub fn f( a : u32 )  -> u32 {\n\n  a   +   1 }\n",
    );
    assert_eq!(find(&c, "x.rs::f").digests.body, da.body);
}

#[test]
fn every_public_item_has_symref_kind_and_digests() {
    let text = std::fs::read_to_string(corpus_dir().join("rust/basic.rs")).unwrap();
    let fs = extract("tests/corpus/rust/basic.rs", &text);
    let free = find(&fs, "tests/corpus/rust/basic.rs::free");
    assert_eq!(free.kind, SymbolKind::Function);
    assert_eq!(free.visibility, Visibility::Public);
    let new = find(&fs, "tests/corpus/rust/basic.rs::Point.new");
    assert_eq!(new.kind, SymbolKind::Method);
    assert_eq!(
        find(&fs, "tests/corpus/rust/basic.rs::Color").visibility,
        Visibility::Crate
    );
    assert_eq!(
        find(&fs, "tests/corpus/rust/basic.rs::Point.secret").visibility,
        Visibility::Private
    );
    let area = find(&fs, "tests/corpus/rust/basic.rs::Point.area");
    assert_eq!(area.implements.as_deref(), Some("Shape"));
    assert_eq!(
        area.parent.as_ref().unwrap().to_string(),
        "tests/corpus/rust/basic.rs::Point[Shape]"
    );
}

#[test]
fn public_api_hides_private_containers() {
    let text = std::fs::read_to_string(corpus_dir().join("rust/basic.rs")).unwrap();
    let g = graph_of(&[("src/lib.rs", &text)]);
    let api: Vec<String> = g
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    assert!(api.contains(&"src/lib.rs::free".to_owned()));
    assert!(api.contains(&"src/lib.rs::Point.new".to_owned()));
    assert!(api.contains(&"src/lib.rs::inner.deep".to_owned()));
    assert!(api.contains(&"src/lib.rs::shout".to_owned()));
    assert!(!api.contains(&"src/lib.rs::private_mod.not_api".to_owned()));
    assert!(!api.contains(&"src/lib.rs::Point.secret".to_owned()));
    assert!(!api.contains(&"src/lib.rs::Color".to_owned()));
}

#[test]
fn imports_are_flattened_and_classified() {
    let text = std::fs::read_to_string(corpus_dir().join("rust/basic.rs")).unwrap();
    let fs = extract("crates/x/src/a/b.rs", &text);
    let targets: Vec<&str> = fs.imports.iter().map(|i| i.target.as_str()).collect();
    assert_eq!(
        targets,
        [
            "crate::util::helper",
            "std::collections::HashMap",
            "std::collections::HashSet",
            "crate::a::sibling",
            "crate::a::sibling::Thing",
        ]
    );
    assert!(fs.imports[0].is_internal());
    assert!(!fs.imports[1].is_internal());
}

#[test]
fn imports_link_files_in_the_graph() {
    let g = graph_of(&[
        (
            "c/src/lib.rs",
            "mod util;\nuse crate::util::helper;\npub fn run() { helper(); }\n",
        ),
        ("c/src/util.rs", "pub fn helper() {}\n"),
    ]);
    let reached = g.reach(&Symref::file("c/src/lib.rs"), EdgeKind::Imports);
    assert_eq!(
        reached.iter().map(ToString::to_string).collect::<Vec<_>>(),
        ["c/src/util.rs::helper"]
    );
}

#[test]
fn caller_is_affected_by_callee() {
    let g = graph_of(&[("c/src/lib.rs", "fn a() { b(); }\nfn b() {}\nfn c() {}\n")]);
    let b = Symref::parse("c/src/lib.rs::b").unwrap();
    let hit = g.affects(&b);
    assert!(hit.contains(&Symref::parse("c/src/lib.rs::a").unwrap()));
    assert!(!hit.contains(&Symref::parse("c/src/lib.rs::c").unwrap()));
    assert!(hit.contains(&Symref::file("c/src/lib.rs")));
    assert!(matches!(g.call_edges()[0], CallEdge::Resolved { .. }));
}

#[test]
fn affects_is_transitive_and_ambiguity_is_kept() {
    let src = "fn top() { mid(); }\nfn mid() { leaf(); }\nfn leaf() {}\n\
               struct A; struct B;\nimpl A { fn go(&self) {} }\nimpl B { fn go(&self) {} }\n\
               fn user() { let a = make(); a.go(); println!(); other(); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let leaf = Symref::parse("c/src/lib.rs::leaf").unwrap();
    let hit: Vec<String> = g.affects(&leaf).iter().map(ToString::to_string).collect();
    assert!(hit.contains(&"c/src/lib.rs::top".to_owned()));
    let go_a = Symref::parse("c/src/lib.rs::A.go").unwrap();
    assert!(
        g.affects(&go_a)
            .contains(&Symref::parse("c/src/lib.rs::user").unwrap())
    );
    assert!(g.call_edges().iter().any(|e| matches!(
        e,
        CallEdge::Ambiguous { candidates, .. } if candidates.len() == 2
    )));
    assert!(g.call_edges().iter().any(|e| matches!(
        e,
        CallEdge::Unresolved { name, .. } if name == "other"
    )));
}

#[test]
fn qualified_calls_narrow_candidates() {
    let src = "struct A; struct B;\nimpl A { fn new() -> A { A } }\nimpl B { fn new() -> B { B } }\n\
               fn mk() { let _ = A::new(); let _ = Vec::new(); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let edges: Vec<&CallEdge> = g.call_edges().iter().collect();
    assert!(edges.iter().any(|e| matches!(
        e,
        CallEdge::Resolved { callee, .. } if callee.to_string() == "c/src/lib.rs::A.new"
    )));
    assert!(
        edges
            .iter()
            .any(|e| matches!(e, CallEdge::Unresolved { name, .. } if name == "new"))
    );
}

#[test]
fn markdown_slugs_dedupe_and_nest() {
    let text = std::fs::read_to_string(corpus_dir().join("markdown/basic.md")).unwrap();
    let fs = extract("d.md", &text);
    let slugs: Vec<String> = fs.symbols.iter().map(|s| s.symref.to_string()).collect();
    assert_eq!(
        slugs,
        [
            "d.md#title",
            "d.md#setup",
            "d.md#details--notes",
            "d.md#usage",
            "d.md#setup-1",
            "d.md#setup-2",
        ]
    );
    let details = find(&fs, "d.md#details--notes");
    assert_eq!(details.parent.as_ref().unwrap().to_string(), "d.md#setup");
    assert_eq!(details.kind, SymbolKind::Heading);
    let setup = find(&fs, "d.md#setup");
    assert_ne!(setup.digests.body, find(&fs, "d.md#setup-1").digests.body);
    // A section body is section-local: it stops at the next heading of any level.
    let alone = extract("d.md", "## Setup\n\nAgain.\n");
    assert_eq!(
        find(&alone, "d.md#setup").digests.body,
        find(&fs, "d.md#setup-1").digests.body
    );
}

#[test]
fn resolve_accepts_unique_suffixes_and_reports_ambiguity() {
    let src = "struct A; struct B;\nimpl A { fn go(&self) {} fn only(&self) {} }\nimpl B { fn go(&self) {} }\n\
               impl std::fmt::Display for A { fn fmt(&self) {} }\nimpl std::fmt::Debug for A { fn fmt(&self) {} }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    assert_eq!(
        g.resolve("only").unwrap().symref.to_string(),
        "c/src/lib.rs::A.only"
    );
    assert_eq!(
        g.resolve("A.go").unwrap().symref.to_string(),
        "c/src/lib.rs::A.go"
    );
    assert_eq!(
        g.resolve("c/src/lib.rs::B.go").unwrap().symref.to_string(),
        "c/src/lib.rs::B.go"
    );
    assert_eq!(g.resolve("A").unwrap().kind, SymbolKind::Struct);
    match g.resolve("go") {
        Err(ResolveError::Ambiguous(c)) => assert_eq!(c.len(), 2),
        other => panic!("{other:?}"),
    }
    match g.resolve("A.fmt") {
        Err(ResolveError::Ambiguous(c)) => assert_eq!(c.len(), 2),
        other => panic!("{other:?}"),
    }
    assert!(g.resolve("A[std::fmt::Debug].fmt").is_ok());
    assert!(matches!(g.resolve("nope"), Err(ResolveError::NotFound(_))));
}

#[test]
fn graph_digest_tracks_structure() {
    let a = graph_of(&[("c/src/lib.rs", "fn a() { b(); }\nfn b() {}\n")]);
    let same = graph_of(&[("c/src/lib.rs", "fn a() { b(); }\nfn b() { 1; }\n")]);
    let moved = graph_of(&[("c/src/lib.rs", "fn a() {}\nfn b() {}\n")]);
    assert_eq!(a.graph_digest(), same.graph_digest());
    assert_ne!(a.graph_digest(), moved.graph_digest());
}

#[test]
fn second_build_extracts_nothing() {
    let root = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(root.path().join("src")).unwrap();
    let files = [
        ("src/lib.rs", "pub fn a() { b(); }\nfn b() {}\n"),
        ("README.md", "# Hi\n\ntext\n"),
        ("notes.txt", "ignored"),
    ];
    let mut entries = Vec::new();
    for (p, t) in files {
        std::fs::write(root.path().join(p), t).unwrap();
        entries.push(entry(p, t));
    }
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());
    assert!(!cache.is_null());
    let (g1, s1) = build_graph_with_stats(root.path(), &entries, &cache);
    assert_eq!(
        (s1.extracted, s1.cached, s1.skipped, s1.opaque),
        (2, 0, 0, 1)
    );
    let (g2, s2) = build_graph_with_stats(root.path(), &entries, &cache);
    assert_eq!(
        (s2.extracted, s2.cached, s2.skipped, s2.opaque),
        (0, 2, 0, 1)
    );
    assert_eq!(g1.graph_digest(), g2.graph_digest());
    assert!(g2.resolve("README.md#hi").is_ok());
}

/// The qualifier recorded on the unresolved call of `name` in `src` (one such call expected).
fn unresolved_qualifier(src: &str, name: &str) -> Option<CallQualifier> {
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let hits: Vec<Option<CallQualifier>> = g
        .call_edges()
        .iter()
        .filter_map(|e| match e {
            CallEdge::Unresolved {
                name: n, qualifier, ..
            } if n == name => Some(qualifier.clone()),
            _ => None,
        })
        .collect();
    assert_eq!(hits.len(), 1, "unresolved `{name}` calls: {hits:?}");
    hits.into_iter().next().flatten()
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files
#[test]
fn unresolved_path_calls_record_their_qualifier() {
    let q = |src: &str, name: &str| unresolved_qualifier(src, name);
    assert_eq!(
        q("fn f() { let _ = Vec::new(); }", "new"),
        Some(CallQualifier::Path("Vec".to_owned()))
    );
    assert_eq!(
        q("fn f() { other::helper(); }", "helper"),
        Some(CallQualifier::Path("other".to_owned()))
    );
    assert_eq!(
        q(
            "struct S;\nimpl S { fn f() { Self::missing(); } }",
            "missing"
        ),
        Some(CallQualifier::Path("S".to_owned()))
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files
#[test]
fn unresolved_calls_with_no_usable_qualifier_record_none() {
    assert_eq!(
        unresolved_qualifier("fn f() { external(); }", "external"),
        None
    );
    assert_eq!(
        unresolved_qualifier("fn f() { crate::gone(); }", "gone"),
        None
    );
    assert_eq!(
        unresolved_qualifier("fn f<T: Dflt>() { let _ = T::make(); }", "make"),
        None,
        "a generic parameter names no concrete type"
    );
    assert_eq!(
        unresolved_qualifier(
            "type Alias = Vec<u8>;\nfn f() { let _ = Alias::with_capacity(1); }",
            "with_capacity"
        ),
        None,
        "a type alias may stand for any type"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files
#[test]
fn unresolved_method_calls_record_the_receiver_kind() {
    let q = |src: &str, name: &str| unresolved_qualifier(src, name);
    assert_eq!(
        q(
            "struct S;\nimpl S { fn f(&self) { self.absent(); } }",
            "absent"
        ),
        Some(CallQualifier::SelfType("S".to_owned()))
    );
    assert_eq!(
        q("struct P;\nfn f(p: &mut P) { p.absent(); }", "absent"),
        Some(CallQualifier::Typed("P".to_owned()))
    );
    assert_eq!(
        q(
            "struct P;\nfn f() { let p = P::new(); p.absent(); }",
            "absent"
        ),
        Some(CallQualifier::Typed("P".to_owned()))
    );
    assert_eq!(
        q("fn f() { make().absent(); }", "absent"),
        Some(CallQualifier::Receiver)
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files
#[test]
fn receiver_types_are_dropped_when_shadowed_wrapped_or_generic() {
    let q = |src: &str, name: &str| unresolved_qualifier(src, name);
    assert_eq!(
        q(
            "struct P;\nfn f() { let p = P::new(); { let p = other(); p.absent(); } }",
            "absent"
        ),
        Some(CallQualifier::Receiver),
        "an inner untyped binding shadows the typed one"
    );
    assert_eq!(
        q("struct P;\nfn f(p: Box<P>) { p.absent(); }", "absent"),
        Some(CallQualifier::Receiver),
        "a deref wrapper hides the real receiver type"
    );
    assert_eq!(
        q("fn f<T: Tr>(t: T) { t.absent(); }", "absent"),
        Some(CallQualifier::Receiver),
        "a generic parameter is not a concrete type"
    );
    assert_eq!(
        q(
            "struct P;\nfn f(p: P) { fn inner() { p.absent(); } }",
            "absent"
        ),
        Some(CallQualifier::Receiver),
        "a nested fn cannot see the outer locals"
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.resolve_site
#[test]
fn self_and_typed_receivers_resolve_to_their_own_method() {
    let src = "struct A; struct B;\n\
               impl A { fn go(&self) {} fn run(&self) { self.go(); } }\n\
               impl B { fn go(&self) {} }\n\
               fn user(b: B) { b.go(); }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let resolved: Vec<(String, String)> = g
        .call_edges()
        .iter()
        .filter_map(|e| match e {
            CallEdge::Resolved { caller, callee } => Some((caller.to_string(), callee.to_string())),
            _ => None,
        })
        .collect();
    assert!(resolved.contains(&(
        "c/src/lib.rs::A.run".to_owned(),
        "c/src/lib.rs::A.go".to_owned()
    )));
    assert!(resolved.contains(&(
        "c/src/lib.rs::user".to_owned(),
        "c/src/lib.rs::B.go".to_owned()
    )));
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.admits
#[test]
fn admits_pins_the_named_type_and_rules_out_the_rest() {
    let src = "struct A; struct B;\n\
               impl A { fn new() {} fn go(&self) {} }\n\
               impl B { fn new() {} }\n\
               fn go() {}\n\
               trait T { fn dflt(&self) {} }\n";
    let g = graph_of(&[("c/src/lib.rs", src)]);
    let rec = |s: &str| {
        g.get(&Symref::parse(&format!("c/src/lib.rs::{s}")).unwrap())
            .unwrap()
            .clone()
    };
    let path_a = CallQualifier::Path("A".to_owned());
    assert_eq!(g.admits(&path_a, &rec("A.new")), Admit::Pinned);
    assert_eq!(g.admits(&path_a, &rec("B.new")), Admit::No);
    assert_eq!(g.admits(&path_a, &rec("T.dflt")), Admit::Maybe);
    let recv = CallQualifier::Receiver;
    assert_eq!(g.admits(&recv, &rec("A.go")), Admit::Maybe);
    assert_eq!(
        g.admits(&recv, &rec("go")),
        Admit::No,
        "a method call is never a free function"
    );
}
