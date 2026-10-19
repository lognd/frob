//! Lexical scan of files with no registered grammar: honoured, reported, or quiet, never silent.

mod common;

use gob_directives::{Binding, ScanConfig, ScanResult, Scanner};
use gob_text::FileInterner;

const ID: &str = "01J9QKX3M8Z4T7N2V5B6C0D1E2";

/// Scan `text` at `path` lexically.
fn lexical(path: &str, text: &str) -> ScanResult {
    let syms = common::symbols(path, text);
    let file = FileInterner::new().intern(path);
    Scanner::new(&ScanConfig::default()).scan_unparsed_in(file, text, &syms)
}

fn rules(r: &ScanResult) -> Vec<String> {
    r.findings.iter().map(|f| f.rule.to_string()).collect()
}

// frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
// frob:tests crates/gob-directives/src/unparsed.rs::scan_unparsed_in
#[test]
fn directive_behind_known_leader_is_honoured_with_marker() {
    for leader in ["#", "//", ";", "--", "%"] {
        let r = lexical(
            "conf/site.caddy",
            &format!("{leader} frob:ticket {ID}\nroute\n"),
        );
        assert_eq!(r.directives.len(), 1, "leader {leader}: {:?}", r.findings);
        assert_eq!(r.directives[0].bound, Binding::File);
        assert_eq!(rules(&r), ["PARSE002"], "leader {leader}");
        let m = &r.findings[0].message;
        assert!(
            m.contains("matched lexically (no grammar for .caddy; text scan, not parsed)"),
            "{m}"
        );
        assert!(
            m.contains("unparsed and invisible to structural gates"),
            "{m}"
        );
    }
}

// frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
// frob:tests crates/gob-directives/src/unparsed.rs::scan_unparsed_in
#[test]
fn v1_waive_in_no_grammar_file_is_reported_not_silent() {
    for text in [
        "# frob:waive RULE001 reason=\"x\"\n",
        "debt: frob:debt T-1\n",
    ] {
        let r = lexical("conf/site.caddy", text);
        assert!(r.directives.is_empty());
        assert!(!r.findings.is_empty(), "silent: {text}");
        assert!(
            r.findings[0]
                .message
                .contains("matched lexically (no grammar for .caddy"),
            "{}",
            r.findings[0].message
        );
    }
}

// frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
// frob:tests crates/gob-directives/src/unparsed.rs::scan_unparsed_in
#[test]
fn unrecognised_comment_syntax_is_an_error_naming_the_directive() {
    let r = lexical("conf/site.caddy", &format!("/* frob:ticket {ID} */\n"));
    assert!(r.directives.is_empty());
    assert_eq!(rules(&r), ["PARSE001"]);
    let m = &r.findings[0].message;
    assert!(
        m.contains("frob:ticket") && m.contains("not honoured") && m.contains("lexically"),
        "{m}"
    );
}

// frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
// frob:tests crates/gob-directives/src/unparsed.rs::scan_unparsed_in
#[test]
fn no_directive_no_grammar_file_stays_quiet() {
    for text in [
        "route /api\n# plain comment\n",
        "{\"note\": \"see frob:ticket docs\"}\n",
        "run frob: later, then # frob is great\n",
    ] {
        let r = lexical("conf/site.caddy", text);
        assert!(
            r.directives.is_empty() && r.findings.is_empty(),
            "{text}: {:?}",
            r.findings
        );
    }
}

// frob:ticket 01M1QDTYRJ3P3GT8828GCNECVB
// frob:tests crates/gob-directives/src/scan.rs::scan_in
#[test]
fn parsed_language_scan_is_unchanged_and_carries_no_marker() {
    let r = common::scan(
        "src/a.py",
        &format!("# frob:ticket {ID}\ndef f():\n    pass\n"),
    );
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    assert_eq!(r.directives.len(), 1);
}
