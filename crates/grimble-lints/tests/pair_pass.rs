//! Edge cases of the PAIR001 pass: cleanup, many effects, non-React files, closures.
// frob:ticket 01M5HDAS62G7H4YY9FVG59GJ01

use gob_languages::Language;
use grimble_lints::pair_pass::{PAIR001, analyze};
use grimble_lints::pass::PathFile;

fn file<'a>(path: &'a str, language: Language, text: &'a str) -> PathFile<'a> {
    PathFile {
        path,
        language,
        text,
    }
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn interval_without_cleanup_fires() {
    let src = "useEffect(() => {\n  setInterval(f, 1);\n}, []);\n";
    let r = analyze(&[file("src/App.tsx", Language::Tsx, src)]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, PAIR001);
    assert!(r.not_applicable.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn cleanup_present_is_clean() {
    let src = "useEffect(() => {\n  const id = setInterval(f, 1);\n  return () => clearInterval(id);\n}, []);\n";
    let r = analyze(&[file("src/App.tsx", Language::Tsx, src)]);
    assert!(r.findings.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn several_effects_report_each_leak() {
    let src = "useEffect(() => { setInterval(a, 1); }, []);\nuseEffect(() => { const i = setInterval(b, 1); return () => clearInterval(i); }, []);\nuseEffect(() => { setTimeout(c, 1); }, []);\n";
    let r = analyze(&[file("src/App.jsx", Language::Jsx, src)]);
    assert_eq!(r.findings.len(), 2);
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn non_react_file_is_not_applicable() {
    let r = analyze(&[file("a.py", Language::Python, "setInterval(f, 1)")]);
    assert!(r.findings.is_empty());
    assert!(!r.not_applicable.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn nested_closure_return_is_not_the_cleanup() {
    let src = "useEffect(() => {\n  setInterval(() => { return 1; }, 1);\n}, []);\n";
    let r = analyze(&[file("src/App.tsx", Language::Tsx, src)]);
    assert_eq!(r.findings.len(), 1);
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn opaque_cleanup_is_unresolved_not_warn() {
    let src = "useEffect(() => {\n  setInterval(f, 1);\n  return stop;\n}, []);\n";
    let r = analyze(&[file("src/App.tsx", Language::Tsx, src)]);
    assert_eq!(r.findings.len(), 1);
    assert!(r.findings[0].reason.is_some());
}
