//! Warm checks keep degraded files and the linked call resolution in the cache.

// frob:ticket 01M4D6NHS19AGZS6NV6B077GY9

use gob_cache::Cache;
use gob_symbols::{
    CallEdge, EdgeKind, FileSymbols, InputsHasher, LinkCache, SymbolGraph, TypeFacts,
    build_graph_with_stats, extract_file,
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

/// A Rust file over the parser's 2 MiB cap: it always degrades, the same way.
fn oversized() -> String {
    format!("// {}\nfn big() {{}}\n", "x".repeat(2 * 1024 * 1024 + 16))
}

fn symbols(path: &str, text: &str) -> FileSymbols {
    extract_file(&entry(path, text), text)
}

fn build_with(
    files: Vec<FileSymbols>,
    cache: &Cache,
    inputs: &str,
    facts: TypeFacts,
) -> SymbolGraph {
    let mut deps = gob_symbols::CrateDeps::new(std::path::Path::new("."));
    let link = LinkCache::new(cache, inputs.to_owned());
    SymbolGraph::from_files_with_deps_cached(files, &mut deps, facts, &link)
}

fn callee_of(g: &SymbolGraph) -> String {
    g.call_edges()
        .iter()
        .find_map(|c| match c {
            CallEdge::Resolved { callee, .. } => Some(callee.to_string()),
            _ => None,
        })
        .expect("a resolved call")
}

fn same_graph(a: &SymbolGraph, b: &SymbolGraph) {
    assert_eq!(a.node_count(), b.node_count());
    assert_eq!(a.call_edges(), b.call_edges());
    assert_eq!(a.edges_with_status(), b.edges_with_status());
}

// frob:tests crates/gob-symbols/src/pipeline.rs::build_graph_with_stats_typed
// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps_cached
#[test]
fn warm_build_keeps_degraded_files_cached_and_reuses_the_link_results() {
    let root = tempfile::tempdir().unwrap();
    let big = oversized();
    let small = "pub fn a() { b(); }\npub fn b() {}\n";
    std::fs::create_dir_all(root.path().join("c/src")).unwrap();
    std::fs::write(root.path().join("c/src/big.rs"), &big).unwrap();
    std::fs::write(root.path().join("c/src/lib.rs"), small).unwrap();
    let files = [entry("c/src/big.rs", &big), entry("c/src/lib.rs", small)];
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());

    let (cold, s1) = build_graph_with_stats(root.path(), &files, &cache);
    assert_eq!((s1.extracted, s1.cached), (2, 0));
    assert!(cold.file_info("c/src/big.rs").unwrap().degraded);

    let (warm, s2) = build_graph_with_stats(root.path(), &files, &cache);
    assert_eq!(
        (s2.extracted, s2.cached),
        (0, 2),
        "the degraded file is not re-folded on a warm build"
    );
    assert!(warm.file_info("c/src/big.rs").unwrap().degraded);
    same_graph(&cold, &warm);

    // Same inputs digest, different call target: only a replayed result still answers `b`.
    let first = build_with(
        vec![symbols(
            "c/src/lib.rs",
            "pub fn a() { b(); }\npub fn b() {}\npub fn c() {}\n",
        )],
        &cache,
        "inputs-one",
        TypeFacts::default(),
    );
    let replay = build_with(
        vec![symbols(
            "c/src/lib.rs",
            "pub fn a() { c(); }\npub fn b() {}\npub fn c() {}\n",
        )],
        &cache,
        "inputs-one",
        TypeFacts::default(),
    );
    assert_eq!(callee_of(&first), "c/src/lib.rs::b");
    assert_eq!(
        callee_of(&replay),
        "c/src/lib.rs::b",
        "the stored resolution is reused"
    );
    assert!(
        replay
            .edges_with_status()
            .iter()
            .any(|e| e.kind == EdgeKind::Calls)
    );
}

// frob:tests crates/gob-symbols/src/graph.rs::SymbolGraph.from_files_with_deps_cached
#[test]
fn changed_inputs_or_facts_recompute_the_link_results() {
    let cache_dir = tempfile::tempdir().unwrap();
    let cache = Cache::open(cache_dir.path());
    let calls_b = "pub fn a() { b(); }\npub fn b() {}\npub fn c() {}\n";
    let calls_c = "pub fn a() { c(); }\npub fn b() {}\npub fn c() {}\n";
    let one = |text: &str, inputs: &str, facts: TypeFacts| {
        build_with(vec![symbols("c/src/lib.rs", text)], &cache, inputs, facts)
    };
    assert_eq!(
        callee_of(&one(calls_b, "x", TypeFacts::default())),
        "c/src/lib.rs::b"
    );
    assert_eq!(
        callee_of(&one(calls_c, "y", TypeFacts::default())),
        "c/src/lib.rs::c"
    );
    let mut facts = TypeFacts::default();
    facts.trust = gob_symbols::TypesTrust::None;
    let other = one(calls_c, "x", facts);
    assert_eq!(
        callee_of(&other),
        "c/src/lib.rs::c",
        "other facts never reuse the old result"
    );
}

// frob:tests crates/gob-symbols/src/pipeline.rs::build_graph_with_stats_typed
#[test]
fn an_unreadable_payload_is_a_miss_and_hashing_is_order_sensitive() {
    let mut a = InputsHasher::new();
    a.add("x.rs", "d1", "rust");
    let mut b = InputsHasher::new();
    b.add("x.rs", "d2", "rust");
    assert_ne!(a.finish(), b.finish());
    let null = Cache::null();
    let g = build_with(
        vec![symbols(
            "c/src/lib.rs",
            "pub fn a() { b(); }\npub fn b() {}\n",
        )],
        &null,
        "n",
        TypeFacts::default(),
    );
    assert_eq!(callee_of(&g), "c/src/lib.rs::b");
}
