//! Acceptance of the TYPING004 pass: unvalidated boundary casts fire, validated parses are clean.
// frob:ticket 01M4D95Q9WWPDZH86CMBMAZEDQ

use gob_languages::Language;
use grimble_lints::pass::PathFile;
use grimble_lints::typing_pass::{TYPING004, analyze};

fn run(
    path: &'static str,
    language: Language,
    text: &'static str,
) -> grimble_lints::pass::PathReport {
    analyze(&[PathFile {
        path,
        language,
        text,
    }])
}

// frob:tests crates/grimble-lints/src/typing_pass.rs::analyze
#[test]
fn awaited_json_cast_fires() {
    let r = run(
        "src/api.ts",
        Language::TypeScript,
        "async function f(res: Response) {\n  return (await res.json()) as User;\n}\n",
    );
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, TYPING004);
    assert_eq!(r.subjects.get(TYPING004), Some(&1));
}

// frob:tests crates/grimble-lints/src/typing_pass.rs::analyze
#[test]
fn schema_parse_is_clean() {
    let r = run(
        "src/api.ts",
        Language::TypeScript,
        "async function f(res: Response) {\n  return schema.parse(await res.json());\n}\n",
    );
    assert!(r.findings.is_empty());
}

// frob:tests crates/grimble-lints/src/typing_pass.rs::analyze
#[test]
fn no_typescript_is_not_applicable() {
    let r = run("a.rs", Language::Rust, "fn f() {}\n");
    assert!(r.findings.is_empty());
    assert!(r.not_applicable.contains_key(TYPING004));
}
