//! Edge cases of the UNITY301/302 pass: project settings, defaults, several projects in one repo.
// frob:ticket 01M5HGRWG7RDR3DTS7PT08HTWJ

use gob_languages::Language;
use gob_rules::Severity;
use grimble_lints::pass::PathFile;
use grimble_lints::unity_pass::{SettingsFile, analyze_project, is_project_settings};

const INPUT: &str = "using UnityEngine;\npublic class M : MonoBehaviour {\n void Update() { if (Input.GetKey(KeyCode.W)) {} }\n}\n";

fn cs<'a>(path: &'a str, text: &'a str) -> PathFile<'a> {
    PathFile {
        path,
        language: Language::CSharp,
        text,
    }
}

fn settings(path: &'static str, handler: &str) -> (&'static str, String) {
    (
        path,
        format!("%YAML 1.1\n--- !u!129 &1\nPlayerSettings:\n  activeInputHandler: {handler}\n"),
    )
}

fn run(
    files: &[PathFile<'_>],
    sets: &[(&'static str, String)],
) -> grimble_lints::unity_pass::UnityReport {
    let s: Vec<SettingsFile<'_>> = sets
        .iter()
        .map(|(path, text)| SettingsFile { path, text })
        .collect();
    analyze_project(files, &s)
}

fn count(r: &grimble_lints::unity_pass::UnityReport, rule: &str) -> usize {
    r.findings.iter().filter(|f| f.rule == rule).count()
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn input_system_handler_fires_unity301_as_warn() {
    let r = run(
        &[cs("Assets/M.cs", INPUT)],
        &[settings("ProjectSettings/ProjectSettings.asset", "1")],
    );
    assert_eq!(count(&r, "UNITY301"), 1);
    assert_eq!(r.findings[0].severity, Severity::Error);
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn default_handlers_report_nothing() {
    for h in ["0", "2"] {
        let r = run(
            &[cs("Assets/M.cs", INPUT)],
            &[settings("ProjectSettings/ProjectSettings.asset", h)],
        );
        assert_eq!(count(&r, "UNITY301"), 0, "handler {h}");
    }
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn missing_settings_make_unity301_not_applicable() {
    let r = run(&[cs("Assets/M.cs", INPUT)], &[]);
    assert!(r.not_applicable.contains_key("UNITY301"));
    assert!(!r.not_applicable.contains_key("UNITY302"));
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn malformed_or_unknown_settings_are_skipped() {
    for (text, label) in [
        ("not yaml at all: [", "malformed"),
        ("Other:\n  activeInputHandler: 1\n", "not player settings"),
        ("PlayerSettings:\n  activeInputHandler: 7\n", "bad value"),
    ] {
        let sets = [("ProjectSettings/ProjectSettings.asset", text.to_owned())];
        let r = run(&[cs("Assets/M.cs", INPUT)], &sets);
        assert_eq!(count(&r, "UNITY301"), 0, "{label}");
        assert!(r.not_applicable.contains_key("UNITY301"), "{label}");
    }
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn each_file_follows_its_own_project() {
    let r = run(
        &[cs("A/Assets/M.cs", INPUT), cs("B/Assets/M.cs", INPUT)],
        &[
            settings("A/ProjectSettings/ProjectSettings.asset", "1"),
            settings("B/ProjectSettings/ProjectSettings.asset", "0"),
        ],
    );
    assert_eq!(count(&r, "UNITY301"), 1);
    assert_eq!(r.findings[0].file, "A/Assets/M.cs");
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::analyze_project
#[test]
fn unity302_needs_no_settings_and_skips_plain_csharp() {
    let hot = "using UnityEngine;\npublic class P : MonoBehaviour {\n Rigidbody body;\n void Update() { body.AddForce(Vector3.up); }\n}\n";
    let plain = "public class P {\n void Update() { body.AddForce(1); }\n}\n";
    let r = run(&[cs("Assets/P.cs", hot), cs("Assets/Q.cs", plain)], &[]);
    assert_eq!(count(&r, "UNITY302"), 1);
}

// frob:tests crates/grimble-lints/src/unity_pass.rs::is_project_settings
#[test]
fn only_the_project_settings_asset_is_a_settings_file() {
    assert!(is_project_settings("ProjectSettings/ProjectSettings.asset"));
    assert!(is_project_settings(
        "g/ProjectSettings/ProjectSettings.asset"
    ));
    assert!(!is_project_settings("ProjectSettings/Other.asset"));
    assert!(!is_project_settings("Assets/ProjectSettings.asset"));
}
