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
    fixture_of(SRC)
}

fn fixture_of(src: &str) -> (Vec<gob_directives::DirectiveRecord>, SymbolGraph) {
    let entry = FileEntry {
        path: "src/lib.rs".into(),
        size: src.len() as u64,
        digest: Digest::of(src.as_bytes()),
        language: LanguageHint::Rust,
    };
    let symbols = extract_file(&entry, src);
    let scan = Scanner::new(&ScanConfig::default()).scan(Language::Rust, src, &symbols);
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

const MEMBER_SRC: &str = r"pub struct Widget;

impl Widget {
    // frob:tests src/lib.rs::Widget::spin
    pub fn turn(&self) {}

    pub fn spin(&self) {}
}
";

// frob:tests crates/frob-tests/src/rule.rs::test001_with_sources
// frob:ticket 01M4BMRXQ0H30CBE9V02RPYTC8
#[test]
fn double_colon_member_symref_is_told_the_dotted_form() {
    let (records, graph) = fixture_of(MEMBER_SRC);
    assert!(
        graph.resolve("src/lib.rs::Widget.spin").is_ok(),
        "dotted form must resolve for this test to mean anything"
    );
    let findings = test001(&records, &graph);
    assert_eq!(findings.len(), 1, "{findings:#?}");
    assert!(
        findings[0].message.contains("`src/lib.rs::Widget.spin`"),
        "{}",
        findings[0].message
    );
}
