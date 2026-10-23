//! Edge cases of the UNITY201/202 pass: cached lookups, helpers, non-Unity C#, other languages.
// frob:ticket 01M5HPSP14N3NCX5TNA9XDR1GY

use gob_languages::Language;
use gob_rules::Severity;
use grimble_lints::pass::PathFile;
use grimble_lints::unity_pass::analyze;

fn cs(text: &str) -> PathFile<'_> {
    PathFile {
        path: "Assets/Scripts/Mover.cs",
        language: Language::CSharp,
        text,
    }
}

const HEADER: &str = "using UnityEngine;\npublic class Mover : MonoBehaviour {\n";

fn unity(body: &str) -> String {
    format!("{HEADER}{body}\n}}\n")
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn lookup_in_update_fires_unity201_as_advisory() {
    let src = unity("void Update() { var r = GetComponent<Rigidbody>(); }");
    let r = analyze(&[cs(&src)]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, "UNITY201");
    assert_eq!(r.findings[0].severity, Severity::Advisory);
    assert!(r.not_applicable.is_empty());
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn allocation_in_update_fires_unity202() {
    let src = unity("void Update() { var l = new List<int>(); }");
    let r = analyze(&[cs(&src)]);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule, "UNITY202");
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn cached_lookup_in_awake_and_start_is_clean() {
    let src = unity(
        "Rigidbody rb;\nvoid Awake() { rb = GetComponent<Rigidbody>(); }\nvoid Start() { var c = GetComponent<Collider>(); }\nvoid Update() { rb.AddForce(Vector3.up); }",
    );
    let r = analyze(&[cs(&src)]);
    assert!(r.findings.is_empty(), "{:?}", r.findings.len());
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn helper_reached_from_update_fires() {
    let src = unity(
        "void Update() { Step(); }\nvoid Step() { var r = GetComponent<Rigidbody>(); }\nvoid Unused() { var r = GetComponent<Rigidbody>(); }",
    );
    let r = analyze(&[cs(&src)]);
    assert_eq!(r.findings.len(), 1);
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn csharp_without_unity_is_not_examined() {
    let src = "public class Plain {\n  void Update() { var l = new List<int>(); }\n}\n";
    let r = analyze(&[cs(src)]);
    assert!(r.findings.is_empty());
    assert!(r.not_applicable.contains_key("UNITY201"));
    assert!(r.not_applicable.contains_key("UNITY202"));
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze
#[test]
fn non_csharp_files_are_ignored() {
    let f = PathFile {
        path: "src/a.ts",
        language: Language::TypeScript,
        text: "function Update() { new Foo(); } // UnityEngine",
    };
    let r = analyze(&[f]);
    assert!(r.findings.is_empty());
    assert!(r.not_applicable.contains_key("UNITY201"));
}
