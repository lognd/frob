//! TEST001 over a graph and directives extracted from real source text.

use frob_tests::{test001, test001_with_sources};
use gob_directives::{ScanConfig, Scanner};
use gob_languages::Language;
use gob_symbols::{SymbolGraph, extract_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

const SRC: &str = r"pub fn covered() {}

// frob:tests ghost_function
pub fn helper() {}

// frob:tests tests.real_test
pub fn also_helper() {}

mod tests {
    // frob:tests covered
    #[test]
    fn real_test() {}

    // frob:tests no_such_symbol
    #[test]
    fn bad_cover() {}
}
";

fn fixture() -> (Vec<gob_directives::DirectiveRecord>, SymbolGraph) {
    let entry = FileEntry {
        path: "src/lib.rs".into(),
        size: SRC.len() as u64,
        digest: Digest::of(SRC.as_bytes()),
        language: LanguageHint::Rust,
    };
    let symbols = extract_file(&entry, SRC);
    let scan = Scanner::new(&ScanConfig::default()).scan(Language::Rust, SRC, &symbols);
    assert!(scan.findings.is_empty(), "{:?}", scan.findings);
    (scan.directives, SymbolGraph::from_files(vec![symbols]))
}

#[test]
fn flags_targets_that_resolve_to_no_test_or_no_symbol() {
    let (records, graph) = fixture();
    let findings = test001(&records, &graph);
    let messages: Vec<&str> = findings.iter().map(|f| f.message.as_str()).collect();
    assert_eq!(findings.len(), 2, "{messages:#?}");
    assert!(
        messages
            .iter()
            .any(|m| m.contains("ghost_function") && m.contains("no test"))
    );
    assert!(
        messages
            .iter()
            .any(|m| m.contains("no_such_symbol") && m.contains("no symbol"))
    );
    assert!(findings.iter().all(|f| f.rule.as_str() == "TEST001"));
}

#[test]
fn attribute_scan_recognises_tests_outside_a_tests_module() {
    let (records, graph) = fixture();
    // With text, `ghost_function` is still unknown; the covers-form results are unchanged.
    let findings = test001_with_sources(&records, &graph, &|_| Some(SRC.to_owned()));
    assert_eq!(findings.len(), 2);
}
