//! Edge cases of the RES pass: certainty, language coverage, escaping handles and applicability.
// frob:ticket 01M4MGE2XKGBNJEV1AECPBVHQF

use gob_languages::Language;
use gob_rules::Severity;
use grimble_lints::pass::PathFile;
use grimble_lints::res_pass::{RES001, analyze};

fn file<'a>(path: &'a str, language: Language, text: &'a str) -> PathFile<'a> {
    PathFile {
        path,
        language,
        text,
    }
}

// frob:tests crates/grimble-lints/src/res_pass.rs::analyze
#[test]
fn an_unpaired_performance_mark_is_a_certain_warn() {
    let r = analyze(&[file(
        "a.ts",
        Language::TypeScript,
        "function f() { performance.mark('a'); }\n",
    )]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, RES001);
    assert_eq!(r.findings[0].severity, Severity::Error);
    assert!(r.findings[0].reason.is_none());
    assert!(r.findings[0].message.contains("performance.clearMarks"));
    assert_eq!(r.subjects.get(RES001), Some(&1));
}

// frob:tests crates/grimble-lints/src/res_pass.rs::analyze
#[test]
fn a_paired_release_is_quiet_but_the_file_is_still_a_subject() {
    let r = analyze(&[file(
        "a.js",
        Language::JavaScript,
        "function f() { performance.mark('a'); performance.clearMarks('a'); }\n",
    )]);
    assert!(r.findings.is_empty());
    assert_eq!(r.subjects.get(RES001), Some(&1));
}

// frob:tests crates/grimble-lints/src/res_pass.rs::analyze
#[test]
fn an_escaping_or_discarded_handle_is_unresolved() {
    for src in [
        "function f() { const t = setTimeout(g, 5); return t; }\n",
        "function f() { setTimeout(g, 5); }\n",
    ] {
        let r = analyze(&[file("a.ts", Language::TypeScript, src)]);
        assert_eq!(r.findings.len(), 1, "{src}");
        assert_eq!(r.findings[0].severity, Severity::Unresolved, "{src}");
        assert!(r.findings[0].reason.is_some(), "{src}");
    }
}

// frob:tests crates/grimble-lints/src/res_pass.rs::analyze
#[test]
fn a_release_in_another_function_does_not_pair_and_tests_are_exempt() {
    let r = analyze(&[file(
        "a.ts",
        Language::TypeScript,
        "function f() { const t = setTimeout(g, 5); }\nfunction h() { clearTimeout(x); }\n",
    )]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].severity, Severity::Error);
    let r = analyze(&[file(
        "a.test.ts",
        Language::TypeScript,
        "it('x', () => { performance.mark('a'); });\n",
    )]);
    assert!(r.findings.is_empty());
}

// frob:tests crates/grimble-lints/src/res_pass.rs::analyze
#[test]
fn unsupported_languages_make_the_rule_not_applicable() {
    let r = analyze(&[
        file("a.py", Language::Python, "performance.mark('a')\n"),
        file("a.md", Language::Markdown, "# x\n"),
    ]);
    assert!(r.findings.is_empty());
    assert!(r.subjects.is_empty());
    assert!(r.not_applicable.contains_key(RES001));
}
