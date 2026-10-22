//! `crunk edit` end to end: id-addressed patches, atomic writes, schema refusal, touched findings.

// frob:ticket 01M4CXRA570ABD65ZDFAFVVZ8Y

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111111"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[jsx]
globs = ["src/**/*.tsx"]
"##;

const CONTENT: &str = "locale = \"en\"\n\n[[key]]\nid = \"home.title\"\ntext = \"Hello\"\nmax_chars = 10\n\n[[key]]\nid = \"home.sub\"\ntext = \"A very long subtitle indeed\"\nmax_chars = 5\n";
const REL: &str = "design/content/home.toml";

fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    std::fs::write(p.join("crunk.toml"), SPEC).unwrap();
    std::fs::create_dir_all(p.join("design/content")).unwrap();
    std::fs::write(p.join(REL), CONTENT).unwrap();
    std::fs::write(p.join("p.json"), "[]").unwrap();
    dir
}

fn patch(dir: &Path, text: &str) {
    std::fs::write(dir.join("p.json"), text).unwrap();
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn read(dir: &Path) -> String {
    std::fs::read_to_string(dir.join(REL)).unwrap()
}

fn json(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

/// Run an edit expecting refusal `code` and an untouched file.
fn refused(dir: &Path, patch_text: &str, code: &str) {
    patch(dir, patch_text);
    let (exit, out, err) = crunk(dir, &["edit", REL, "--patch", "p.json"]);
    assert_ne!(exit, 0, "{out} {err}");
    assert!(
        out.contains(code) || err.contains(code),
        "{code} not in {out} {err}"
    );
    assert_eq!(read(dir), CONTENT, "file must be untouched");
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
// frob:tests crates/crunk/src/edit.rs::EditData.lines
// frob:tests crates/crunk/src/patch.rs::apply
#[test]
fn edit_applies_by_id_and_reports_diff_and_touched_findings_only() {
    let dir = project();
    patch(
        dir.path(),
        r#"[{"op":"replace","path":"/key/home.title/text","value":"Hello there, friend!"}]"#,
    );
    let (code, out, err) = crunk(dir.path(), &["edit", REL, "--patch", "p.json"]);
    assert_eq!(code, 0, "{out} {err}");
    let v = json(&out);
    let data = &v["data"];
    assert_eq!(data["changed"], true);
    assert!(
        data["diff"]
            .as_str()
            .unwrap()
            .contains("+text = \"Hello there, friend!\"")
    );
    assert!(read(dir.path()).contains("Hello there, friend!"));
    let (_, text, _) = crunk(dir.path(), &["edit", REL, "--patch", "p.json", "--text"]);
    assert!(text.contains("unchanged"), "{text}");
    assert_eq!(data["touched"], serde_json::json!(["home.title"]));
    let findings = data["findings"].as_array().unwrap();
    assert!(!findings.is_empty(), "{out}");
    for f in findings {
        let msg = f["message"].as_str().unwrap();
        assert!(msg.contains("home.title"), "{msg}");
        assert!(!msg.contains("home.sub"), "untouched id leaked: {msg}");
    }
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
// frob:tests crates/crunk/src/edit.rs::EditError.code
#[test]
fn edit_refuses_a_schema_violation_and_leaves_the_file_alone() {
    let dir = project();
    refused(
        dir.path(),
        r#"[{"op":"add","path":"/key/home.title/bogus","value":1}]"#,
        "E-EDIT-SCHEMA",
    );
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn edit_refuses_bad_pointer_missing_id_and_failed_test() {
    let dir = project();
    refused(
        dir.path(),
        r#"[{"op":"remove","path":"key/0"}]"#,
        "E-EDIT-PATCH",
    );
    refused(
        dir.path(),
        r#"[{"op":"replace","path":"/key/nope.id/text","value":"x"}]"#,
        "E-EDIT-PATCH",
    );
    refused(
        dir.path(),
        r#"[{"op":"test","path":"/key/home.title/text","value":"Other"}]"#,
        "E-EDIT-PATCH",
    );
    refused(dir.path(), "not json", "E-EDIT-PATCH");
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn edit_is_atomic_when_a_later_op_fails() {
    let dir = project();
    refused(
        dir.path(),
        r#"[{"op":"replace","path":"/key/home.title/text","value":"X"},{"op":"remove","path":"/key/missing"}]"#,
        "E-EDIT-PATCH",
    );
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn edit_empty_patch_and_dry_run_write_nothing() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["edit", REL, "--patch", "p.json"]);
    assert_eq!(code, 0, "{out} {err}");
    assert_eq!(json(&out)["data"]["changed"], false);
    assert_eq!(read(dir.path()), CONTENT);

    patch(
        dir.path(),
        r#"[{"op":"replace","path":"/key/home.title/text","value":"Hi"}]"#,
    );
    let (code, out, err) = crunk(dir.path(), &["edit", REL, "--patch", "p.json", "--dry-run"]);
    assert_eq!(code, 0, "{out} {err}");
    let data = &json(&out)["data"];
    assert_eq!(data["changed"], true);
    assert_eq!(data["findings_checked"], false);
    assert!(data["diff"].as_str().unwrap().contains("+text = \"Hi\""));
    assert_eq!(read(dir.path()), CONTENT);
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn edit_refuses_files_outside_the_project_or_of_the_wrong_kind() {
    let dir = project();
    std::fs::write(dir.path().join("other.toml"), "a = 1\n").unwrap();
    for target in ["other.toml", "crunk.toml", "../elsewhere.screen.toml"] {
        let (exit, out, err) = crunk(dir.path(), &["edit", target, "--patch", "p.json"]);
        assert_ne!(exit, 0, "{target}: {out} {err}");
        assert!(
            out.contains("E-EDIT-PATH") || err.contains("E-EDIT-PATH"),
            "{out} {err}"
        );
    }
}
