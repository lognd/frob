//! Annotated TypeScript receivers resolve by the type facts: Must when tsc-clean, May when claimed, dynamic for any.

// frob:ticket 01M4CXSY224VNMR2R5Q69D9E89

use gob_symbols::{
    EdgeKind, FileSymbols, Status, SymbolGraph, TypeFacts, TypesTrust, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

const TYPED: &str =
    "class A { run(): void {} }\nclass B { run(): void {} }\nfunction go(x: A) { x.run(); }\n";
const LOOSE: &str =
    "class A { run(): void {} }\nclass B { run(): void {} }\nfunction go(x: any) { x.run(); }\n";

fn files(src: &str) -> Vec<FileSymbols> {
    let entry = FileEntry {
        path: "m.ts".to_owned(),
        size: src.len() as u64,
        digest: Digest::of(src.as_bytes()),
        language: LanguageHint::from_path("m.ts"),
    };
    vec![extract_file(&entry, src)]
}

fn calls(g: &SymbolGraph) -> Vec<(Option<String>, Status)> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string().ends_with("go"))
        .map(|e| (e.to.as_ref().map(ToString::to_string), e.status))
        .collect()
}

fn clean(trust: TypesTrust) -> TypeFacts {
    let mut facts = TypeFacts::new(trust);
    facts.mark_clean("m.ts");
    facts
}

#[test]
// frob:tests crates/gob-symbols/src/graph/typescript.rs::SymbolGraph.ts_typed_method
fn strict_clean_concrete_dispatch_is_must_and_any_sites_are_dynamic() {
    let exact = calls(&SymbolGraph::from_files_typed(
        files(TYPED),
        clean(TypesTrust::Checked),
    ));
    assert_eq!(exact.len(), 1, "{exact:?}");
    assert_eq!(exact[0].1, Status::Must);
    assert!(exact[0].0.as_deref().is_some_and(|t| t.ends_with("A.run")));

    let claimed = calls(&SymbolGraph::from_files_typed(
        files(TYPED),
        TypeFacts::new(TypesTrust::Checked),
    ));
    assert_eq!(claimed.len(), 1, "{claimed:?}");
    assert_eq!(claimed[0].1, Status::May);

    let dynamic = calls(&SymbolGraph::from_files_typed(
        files(LOOSE),
        clean(TypesTrust::Checked),
    ));
    assert_eq!(dynamic.len(), 1, "{dynamic:?}");
    assert!(
        dynamic[0].0.is_none(),
        "any receiver must not resolve: {dynamic:?}"
    );

    let hint = calls(&SymbolGraph::from_files_typed(
        files(TYPED),
        clean(TypesTrust::None),
    ));
    assert!(
        hint.len() >= 2,
        "trust none keeps the name-wide fan-out: {hint:?}"
    );
}
