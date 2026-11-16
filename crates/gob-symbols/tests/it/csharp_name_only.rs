//! C# graph regressions: `using static` of a BCL type, and name-only extension fallbacks.

use gob_symbols::{EdgeBasis, EdgeKind, GapReason, SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn graph_of(path: &str, text: &str) -> SymbolGraph {
    let entry = FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    SymbolGraph::from_files(vec![extract_file(&entry, text)])
}

/// The bases of the `Calls` edges that resolved to a target.
fn resolved_bases(g: &SymbolGraph) -> Vec<EdgeBasis> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.to.is_some())
        .map(|e| e.basis)
        .collect()
}

// frob:ticket 01M63G1NY275Y890ZD5W1EVN63
// frob:tests crates/gob-symbols/src/graph/csharp.rs::cs_name
#[test]
fn using_static_of_a_bcl_type_terminates_with_an_honest_gap() {
    let src = "using static System.Console;\n\
               class A { void M() { Console.WriteLine(1); WriteLine(2); } }\n";
    let g = graph_of("A.cs", src);
    let calls: Vec<_> = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls)
        .map(|e| (e.to.is_some(), e.reason))
        .collect();
    // `Console.WriteLine` is a BCL call (no edge); the bare `WriteLine` stays an honest gap.
    assert_eq!(calls, [(false, Some(GapReason::Unbound))]);
}

// frob:ticket 01M63G1NY275Y890ZD5W1EVN63
// frob:tests crates/gob-symbols/src/graph/csharp.rs::cs_extensions
#[test]
fn an_extension_with_no_exact_receiver_is_name_only() {
    let src = "static class E { public static int Twice(this string s) { return 1; } }\n\
               class A { void M(int x) { x.Twice(); } }\n";
    let g = graph_of("A.cs", src);
    assert_eq!(resolved_bases(&g), [EdgeBasis::NameOnly]);
}
