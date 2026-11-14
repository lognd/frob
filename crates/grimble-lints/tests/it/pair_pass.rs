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

const UNITY_HEAD: &str = "using UnityEngine;\npublic class Hud : MonoBehaviour {\n";

fn unity(body: &str) -> String {
    format!("{UNITY_HEAD}{body}\n}}\n")
}

fn run_cs(src: &str) -> grimble_lints::pair_pass::PairReport {
    analyze(&[file("Assets/Hud.cs", Language::CSharp, src)])
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_onenable_without_ondisable_is_reported() {
    let src = unity("void OnEnable() { Health.Changed += Hit; }\nvoid Hit() {}");
    let r = run_cs(&src);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, PAIR001);
    assert_eq!(r.findings[0].severity, gob_rules::Severity::Error);
    assert!(r.findings[0].message.contains("OnDisable"));
    assert_eq!(r.subjects.get(PAIR001), Some(&1));
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_paired_onenable_ondisable_is_clean() {
    let src = unity(
        "void OnEnable() { Health.Changed += Hit; }\nvoid OnDisable() { Health.Changed -= Hit; }\nvoid Hit() {}",
    );
    let r = run_cs(&src);
    assert!(r.findings.is_empty());
    assert!(r.not_applicable.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_start_paired_with_ondestroy_is_clean() {
    let src = unity(
        "void Start() { Health.Changed += Hit; }\nvoid OnDestroy() { Health.Changed -= Hit; }\nvoid Hit() {}",
    );
    assert!(run_cs(&src).findings.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_unsubscribing_a_different_handler_is_reported() {
    let src = unity(
        "void OnEnable() { Health.Changed += Hit; }\nvoid OnDisable() { Health.Changed -= Other; }\nvoid Hit() {}\nvoid Other() {}",
    );
    assert_eq!(run_cs(&src).findings.len(), 1);
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_lambda_subscription_is_unresolved_not_warn() {
    let src = unity(
        "void OnEnable() { Health.Changed += () => Hit(); }\nvoid OnDisable() {}\nvoid Hit() {}",
    );
    let r = run_cs(&src);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].severity, gob_rules::Severity::Unresolved);
    assert!(r.findings[0].reason.is_some());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn non_unity_csharp_is_not_applicable() {
    let src = "public class Plain {\n void OnEnable() { Bus.Changed += Hit; }\n void Hit() {}\n}\n";
    let r = run_cs(src);
    assert!(r.findings.is_empty());
    assert!(!r.not_applicable.is_empty());
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn unity_partial_class_is_unresolved_not_warn() {
    let src = "using UnityEngine;\npublic partial class Hud : MonoBehaviour {\nvoid OnEnable() { Health.Changed += Hit; }\nvoid Hit() {}\n}\n";
    let r = run_cs(src);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].severity, gob_rules::Severity::Unresolved);
}

// frob:tests crates/grimble-lints/src/pair_pass.rs::analyze
#[test]
fn react_and_unity_files_report_together() {
    let cs = unity("void OnEnable() { Health.Changed += Hit; }\nvoid Hit() {}");
    let r = analyze(&[
        file(
            "src/App.tsx",
            Language::Tsx,
            "useEffect(() => { setInterval(f, 1); }, []);",
        ),
        file("Assets/Hud.cs", Language::CSharp, &cs),
    ]);
    assert_eq!(r.findings.len(), 2);
    assert_eq!(r.subjects.get(PAIR001), Some(&2));
}
