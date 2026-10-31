//! Edge cases of the ERR pass: certainty, per-rule language coverage and applicability.
// frob:ticket 01M4MBJ35HGM0P2MH4B7YMB3EQ

use gob_languages::Language;
use gob_rules::Severity;
use grimble_lints::err_pass::{ERR001, ERR002, ERR003, analyze};
use grimble_lints::pass::PathFile;

fn file<'a>(path: &'a str, language: Language, text: &'a str) -> PathFile<'a> {
    PathFile {
        path,
        language,
        text,
    }
}

// frob:tests crates/grimble-lints/src/err_pass.rs::analyze
#[test]
fn an_empty_python_handler_is_a_certain_err001() {
    let src = "try:\n    f()\nexcept:\n    pass\n";
    let r = analyze(&[file("a.py", Language::Python, src)]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, ERR001);
    assert_eq!(r.findings[0].severity, Severity::Error);
    assert_eq!(r.subjects.get(ERR001), Some(&1));
    assert_eq!(r.subjects.get(ERR003), Some(&1));
    assert!(r.not_applicable.contains_key(ERR002));
}

// frob:tests crates/grimble-lints/src/err_pass.rs::analyze
#[test]
fn an_unknown_callee_is_unresolved() {
    let r = analyze(&[file(
        "a.rs",
        Language::Rust,
        "fn f() { let _ = mystery(); }\n",
    )]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, ERR002);
    assert_eq!(r.findings[0].severity, Severity::Unresolved);
    assert!(r.findings[0].reason.is_some());
}

// frob:tests crates/grimble-lints/src/err_pass.rs::analyze
#[test]
fn a_silent_typescript_catch_all_is_err003() {
    let r = analyze(&[file(
        "a.ts",
        Language::TypeScript,
        "try { f(); } catch (e) { x = 1; }\n",
    )]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, ERR003);
    assert!(r.not_applicable.contains_key(ERR002));
}

// frob:tests crates/grimble-lints/src/err_pass.rs::analyze
#[test]
fn files_the_rules_do_not_judge_make_them_not_applicable() {
    let r = analyze(&[file("a.md", Language::Markdown, "# x\n")]);
    assert!(r.findings.is_empty());
    assert_eq!(r.not_applicable.len(), 3);
    assert!(r.subjects.is_empty());
}
