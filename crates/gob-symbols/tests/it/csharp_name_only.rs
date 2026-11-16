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

// frob:ticket 01M67PBKDJP2WCYAAHMX41BW80
// frob:tests crates/gob-symbols/src/csharp.rs::collect_locals
#[test]
fn a_var_local_from_a_declared_call_is_typed_or_unresolved() {
    let src = "class Client { public void GetAsync(int u) { } }\n\
               class A { Client Make() { return null; }\n\
               void M() { var c = Make(); c.GetAsync(1); } }\n";
    let g = graph_of("A.cs", src);
    let edges = g.edges_with_status();
    let e = edges
        .iter()
        .find(|e| e.kind == EdgeKind::Calls && e.name.as_deref() == Some("GetAsync"))
        .or_else(|| {
            edges.iter().find(|e| {
                e.kind == EdgeKind::Calls
                    && e.to
                        .as_ref()
                        .is_some_and(|t| t.to_string().contains("GetAsync"))
            })
        });
    let e = e.unwrap_or_else(|| panic!("c.GetAsync is silently clean: {edges:#?}"));
    assert!(e.to.is_some() || e.reason.is_some());
}

// frob:ticket 01M67PBKDJP2WCYAAHMX41BW80
// frob:tests crates/gob-symbols/src/csharp.rs::collect_locals
#[test]
fn a_var_local_from_an_unknown_call_is_unresolved_not_clean() {
    let src = "class A { void M() { var c = Build(); c.GetAsync(1); } }\n";
    let g = graph_of("A.cs", src);
    let gaps = g
        .edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.to.is_none() && e.reason.is_some())
        .count();
    assert_eq!(gaps, 2, "both Build and c.GetAsync must be gaps");
}
