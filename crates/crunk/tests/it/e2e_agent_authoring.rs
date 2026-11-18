//! Agent authoring end to end: `crunk new` then `crunk edit --patch` report findings for touched nodes only.

// frob:ticket 01M5XCWA3KQZFNDX9F46YNRVA6

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use serde_json::Value;

const COMP_FILE: &str = "design/components/card.component.toml";
const SCREEN_FILE: &str = "design/screens/home.screen.toml";
const CONTENT_FILE: &str = "design/content/home.toml";

/// The fixture files (not subdirectories) every project starts from.
fn fixture_files() -> Vec<PathBuf> {
    let fx = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/agent_authoring");
    std::fs::read_dir(&fx)
        .expect("fixture dir")
        .map(|e| e.expect("entry").path())
        .filter(|p| p.is_file())
        .collect()
}

/// A fresh project dir holding the fixture `crunk.toml` and every fixture patch; the design dir is empty.
fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    for path in fixture_files() {
        let name = path.file_name().expect("file name");
        std::fs::copy(&path, dir.path().join(name)).expect("copy fixture");
    }
    dir
}

/// Run `crunk args` in `dir`, returning the exit code and the parsed stdout envelope.
fn crunk(dir: &Path, args: &[&str]) -> (i32, Value) {
    let (code, out, err) = run_for_test(&crunk::cli(), args, dir);
    let v = serde_json::from_str(&out).unwrap_or_else(|e| panic!("not json ({e}): {out} {err}"));
    (code, v)
}

/// `crunk edit file --patch patch`, expecting success; returns the `data` object.
fn edit_ok(dir: &Path, file: &str, patch: &str) -> Value {
    let (code, v) = crunk(dir, &["edit", file, "--patch", patch]);
    assert_eq!(code, 0, "{v}");
    v["data"].clone()
}

/// Rule ids of the findings in an edit response.
fn rules(data: &Value) -> Vec<String> {
    data["findings"]
        .as_array()
        .expect("findings array")
        .iter()
        .map(|f| f["rule"].as_str().expect("rule").to_owned())
        .collect()
}

/// Rule ids of the findings a full `crunk check` reports against `file`.
fn check_rules_in(dir: &Path, file: &str) -> Vec<String> {
    let (_, v) = crunk(dir, &["check"]);
    v["data"]["findings"]
        .as_array()
        .expect("findings array")
        .iter()
        .filter(|f| f["file"] == file)
        .map(|f| f["rule"].as_str().expect("rule").to_owned())
        .collect()
}

// frob:tests crates/crunk/src/new.rs::New.run
// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn new_component_then_edit_variants_reports_comp_findings_for_touched_nodes_only() {
    let dir = project();
    let (code, _) = crunk(dir.path(), &["new", "component", "card"]);
    assert_eq!(code, 0);

    let data = edit_ok(dir.path(), COMP_FILE, "component.add_variants.patch.json");
    assert_eq!(data["touched"], serde_json::json!(["card"]));
    assert!(rules(&data).contains(&"COMP002".to_owned()), "{data}");

    // The COMP002 finding names `card`; a patch touching only the `size` prop must not report it.
    let data = edit_ok(dir.path(), COMP_FILE, "component.retune.patch.json");
    assert_eq!(data["touched"], serde_json::json!(["size"]));
    assert!(!rules(&data).contains(&"COMP002".to_owned()), "{data}");
    assert!(
        check_rules_in(dir.path(), COMP_FILE).contains(&"COMP002".to_owned()),
        "the finding must still exist in a full check"
    );
}

// frob:tests crates/crunk/src/new.rs::New.run
// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn new_screen_then_edit_states_reports_state_findings_for_touched_nodes_only() {
    let dir = project();
    let (code, _) = crunk(dir.path(), &["new", "screen", "home"]);
    assert_eq!(code, 0);

    let data = edit_ok(dir.path(), SCREEN_FILE, "screen.kinds.patch.json");
    assert_eq!(data["touched"], serde_json::json!(["home"]));
    assert!(rules(&data).contains(&"STATE002".to_owned()), "{data}");

    // The remaining findings name the screen `home`; patching only state ids must not report them.
    let data = edit_ok(dir.path(), SCREEN_FILE, "screen.add_states.patch.json");
    assert_eq!(
        data["touched"],
        serde_json::json!(["empty", "error", "loading", "partial"])
    );
    assert!(
        !rules(&data).iter().any(|r| r.starts_with("STATE")),
        "{data}"
    );
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
#[test]
fn edit_content_reports_content_findings_for_the_touched_key_only() {
    let dir = project();
    std::fs::create_dir_all(dir.path().join("design/content")).unwrap();
    let fx = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/agent_authoring/content/home.toml");
    std::fs::copy(fx, dir.path().join(CONTENT_FILE)).expect("content fixture");

    let data = edit_ok(dir.path(), CONTENT_FILE, "content.patch.json");
    assert_eq!(data["touched"], serde_json::json!(["home.title"]));
    let findings = data["findings"].as_array().unwrap();
    assert!(findings.iter().any(|f| f["rule"] == "CONTENT002"), "{data}");
    for f in findings {
        let msg = f["message"].as_str().unwrap();
        assert!(msg.contains("home.title"), "{msg}");
        assert!(!msg.contains("home.sub"), "untouched key leaked: {msg}");
    }
}

// frob:tests crates/crunk/src/edit.rs::Edit.run
// frob:tests crates/crunk/src/edit.rs::EditError.code
#[test]
fn edit_patch_to_a_missing_id_is_refused_naming_the_id_and_writes_nothing() {
    let dir = project();
    let (code, _) = crunk(dir.path(), &["new", "screen", "home"]);
    assert_eq!(code, 0);
    let path = dir.path().join(SCREEN_FILE);
    let before = std::fs::read_to_string(&path).unwrap();
    let (code, v) = crunk(
        dir.path(),
        &["edit", SCREEN_FILE, "--patch", "missing_id.patch.json"],
    );
    // Exit 3 is the CLI's "refused" class; the ticket text says 2 (usage), which edit reserves for bad arguments.
    assert_eq!(code, 3, "{v}");
    assert_eq!(v["error"]["code"], "E-EDIT-PATCH");
    assert!(
        v["error"]["message"].as_str().unwrap().contains("ghost"),
        "{v}"
    );
    assert_eq!(std::fs::read_to_string(&path).unwrap(), before);
}
