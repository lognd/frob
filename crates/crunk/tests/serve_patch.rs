//! The serve patch tool: `edit --patch` as an opt-in write MCP tool.

// frob:ticket 01M5XCW9ZZ5GX5VGERB6H96M2G

use std::path::Path;

use crunk::serve_patch::{PatchTool, TOOL_NAME};
use serde_json::{Value, json};

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
    dir
}

fn read(dir: &Path) -> String {
    std::fs::read_to_string(dir.join(REL)).unwrap()
}

/// The decoded JSON body of a tool result.
fn body(result: &Value) -> Value {
    let text = result["content"][0]["text"].as_str().expect("text content");
    serde_json::from_str(text).expect("json body")
}

fn replace_title(text: &str) -> Value {
    json!({ "file": REL, "patch": [
        { "op": "replace", "path": "/key/home.title/text", "value": text }
    ] })
}

// frob:tests PatchTool.call
#[test]
fn patch_returns_the_diff_and_touched_findings_only() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    let result = tool
        .call(TOOL_NAME, &replace_title("Hello there, friend!"))
        .expect("call");
    assert_eq!(result["isError"], false);
    let data = body(&result);
    assert_eq!(data["changed"], true);
    assert!(
        data["diff"]
            .as_str()
            .unwrap()
            .contains("+text = \"Hello there, friend!\"")
    );
    assert!(read(dir.path()).contains("Hello there, friend!"));
    let findings = data["findings"].as_array().unwrap();
    assert!(!findings.is_empty(), "{data}");
    for f in findings {
        let msg = f["message"].as_str().unwrap();
        assert!(msg.contains("home.title"), "{msg}");
        assert!(!msg.contains("home.sub"), "untouched node leaked: {msg}");
    }
}

// frob:tests PatchTool.call
#[test]
fn a_schema_failure_writes_nothing_and_returns_a_located_error() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    let args = json!({ "file": REL, "patch": [
        { "op": "add", "path": "/key/home.title/bogus", "value": 1 }
    ] });
    let result = tool.call(TOOL_NAME, &args).expect("call");
    assert_eq!(result["isError"], true);
    let err = body(&result);
    assert_eq!(err["code"], "E-EDIT-SCHEMA");
    assert_eq!(err["file"], REL);
    assert_eq!(err["written"], false);
    assert!(err["message"].as_str().unwrap().contains("bogus"), "{err}");
    assert_eq!(read(dir.path()), CONTENT);
}

// frob:tests PatchTool.call
#[test]
fn a_patch_that_does_not_apply_writes_nothing() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    let args = json!({ "file": REL, "patch": [
        { "op": "replace", "path": "/key/nope.id/text", "value": "x" }
    ] });
    let err = body(&tool.call(TOOL_NAME, &args).expect("call"));
    assert_eq!(err["code"], "E-EDIT-PATCH");
    assert_eq!(read(dir.path()), CONTENT);
}

// frob:tests PatchTool.listing
// frob:tests PatchTool.call
#[test]
fn a_read_only_session_does_not_offer_the_tool() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), false);
    assert!(tool.listing().is_empty());
    let err = tool.call(TOOL_NAME, &replace_title("X")).unwrap_err();
    assert!(err.contains("unknown tool"), "{err}");
    assert_eq!(read(dir.path()), CONTENT);
}

// frob:tests PatchTool.listing
#[test]
fn a_write_session_lists_the_tool_with_its_schema() {
    let dir = project();
    let listing = PatchTool::new(dir.path(), true).listing();
    assert_eq!(listing.len(), 1);
    assert_eq!(listing[0]["name"], TOOL_NAME);
    assert_eq!(
        listing[0]["inputSchema"]["required"],
        json!(["file", "patch"])
    );
    assert_eq!(listing[0]["annotations"]["readOnlyHint"], false);
}

// frob:tests PatchTool.call
#[test]
fn dry_run_reports_the_diff_without_writing() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    let mut args = replace_title("Hi");
    args["dry_run"] = json!(true);
    let data = body(&tool.call(TOOL_NAME, &args).expect("call"));
    assert_eq!(data["changed"], true);
    assert_eq!(data["findings_checked"], false);
    assert_eq!(read(dir.path()), CONTENT);
}

// frob:tests PatchTool.call
#[test]
fn malformed_arguments_are_invalid_params() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    assert!(tool.call(TOOL_NAME, &json!({ "file": REL })).is_err());
    assert!(
        tool.call(TOOL_NAME, &json!({ "file": REL, "patch": "x" }))
            .is_err()
    );
    assert!(
        tool.call(TOOL_NAME, &json!({ "file": REL, "patch": [], "x": 1 }))
            .is_err()
    );
    assert!(tool.call(TOOL_NAME, &json!("nope")).is_err());
}

// frob:tests PatchTool.call
#[test]
fn a_file_outside_the_project_is_refused() {
    let dir = project();
    let tool = PatchTool::new(dir.path(), true);
    let args = json!({ "file": "crunk.toml", "patch": [] });
    let err = body(&tool.call(TOOL_NAME, &args).expect("call"));
    assert_eq!(err["code"], "E-EDIT-PATH");
}
