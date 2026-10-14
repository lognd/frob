//! Annotated Python receivers resolve by the type facts: Must in a checker-clean file, May when claimed.

// frob:ticket 01M4CXSWZ95SVDADAB97TYG963

use gob_symbols::{
    EdgeKind, FileSymbols, Status, SymbolGraph, TypeFacts, TypesTrust, extract_file,
};
use gob_walk::{Digest, FileEntry, LanguageHint};

const SRC: &str = "class A:\n    def run(self):\n        pass\n\nclass B:\n    def run(self):\n        pass\n\ndef go(x: A):\n    x.run()\n";

fn files() -> Vec<FileSymbols> {
    let entry = FileEntry {
        path: "m.py".to_owned(),
        size: SRC.len() as u64,
        digest: Digest::of(SRC.as_bytes()),
        language: LanguageHint::from_path("m.py"),
    };
    vec![extract_file(&entry, SRC)]
}

fn edges(g: &SymbolGraph) -> Vec<(String, Status)> {
    g.edges_with_status()
        .iter()
        .filter(|e| e.kind == EdgeKind::Calls && e.from.to_string().ends_with("go"))
        .filter_map(|e| e.to.as_ref().map(|t| (t.to_string(), e.status)))
        .collect()
}

#[test]
// frob:tests crates/gob-symbols/src/graph/python.rs::SymbolGraph.py_typed_method
fn clean_file_makes_the_annotated_target_must_and_failing_makes_it_may() {
    let mut facts = TypeFacts::new(TypesTrust::Checked);
    facts.mark_clean("m.py");
    let exact = edges(&SymbolGraph::from_files_typed(files(), facts));
    assert_eq!(exact.len(), 1, "{exact:?}");
    assert_eq!(exact[0].1, Status::Must);
    let claimed = edges(&SymbolGraph::from_files_typed(
        files(),
        TypeFacts::new(TypesTrust::Checked),
    ));
    assert_eq!(claimed.len(), 1, "{claimed:?}");
    assert_eq!(claimed[0].1, Status::May);
    let annotated = edges(&SymbolGraph::from_files_typed(
        files(),
        TypeFacts::new(TypesTrust::Annotated),
    ));
    assert_eq!(annotated.len(), 1);
    assert_eq!(annotated[0].1, Status::May);
}
