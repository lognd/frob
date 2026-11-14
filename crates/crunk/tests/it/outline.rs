//! `crunk outline` and `guidelines` end to end, and their listing as read-only MCP tools.

// frob:ticket 01M5XCW9WCHSZBR5F29VKYBM25

use std::io::Cursor;
use std::path::Path;

use gob_cli::run_for_test;
use serde_json::{Value, json};

const SPEC: &str = r##"[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#111"
accent = "#ff0000"

[scales]
spacing = [0, 8]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base", "components"]

[tokens]
json_file = "tokens.json"

[tailwind]
tokens_file = "tailwind.tokens.json"
namespace_keys = true
"##;

/// A project with tokens and one scaffolded component, screen and flow.
fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("crunk.toml"), SPEC).expect("write spec");
    for args in [
        &["tokens"][..],
        &["new", "component", "card"],
        &["new", "screen", "home"],
        &["new", "flow", "signup"],
    ] {
        let (code, out, err) = crunk(dir.path(), args);
        assert_eq!(code, 0, "{args:?}: {out} {err}");
    }
    dir
}

/// Run crunk in `dir`.
fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

/// Parse a JSON envelope.
fn json_of(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

/// The `kind:id` pairs of an outline reply.
fn pairs(env: &Value) -> Vec<String> {
    env["data"]["entries"]
        .as_array()
        .expect("entries")
        .iter()
        .map(|e| {
            format!(
                "{}:{}",
                e["kind"].as_str().unwrap(),
                e["id"].as_str().unwrap()
            )
        })
        .collect()
}

// frob:tests crates/crunk/src/outline.rs::Outline
#[test]
fn outline_lists_every_kind_sparsely() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["outline", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env = json_of(&out);
    let got = pairs(&env);
    for want in ["component:card", "screen:home", "flow:signup"] {
        assert!(got.iter().any(|g| g == want), "{want} in {got:?}");
    }
    assert!(
        got.iter().any(|g| g.starts_with("token:--color-ink")),
        "{got:?}"
    );
    assert!(env["data"].get("detail").is_none(), "sparse: {env}");
}

// frob:tests crates/crunk/src/outline.rs::Outline
#[test]
fn outline_node_drills_into_one_node_only() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["outline", "--node", "home", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env = json_of(&out);
    assert_eq!(pairs(&env), ["screen:home"]);
    assert!(env["data"]["detail"].is_object(), "{env}");

    let (code, out, _) = crunk(dir.path(), &["outline", "--node", "color-ink", "--json"]);
    assert_eq!(code, 0, "{out}");
    assert_eq!(pairs(&json_of(&out)), ["token:--color-ink"]);
}

// frob:tests crates/crunk/src/outline.rs::Outline
#[test]
fn outline_unknown_node_is_a_usage_error() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["outline", "--node", "nope", "--json"]);
    assert_ne!(code, 0, "{out} {err}");
    assert!(format!("{out}{err}").contains("nope"), "{out} {err}");
}

// frob:tests crates/crunk/src/guidelines.rs::Guidelines
// frob:tests crates/crunk/src/guidelines.rs::read_guidelines
#[test]
fn guidelines_default_then_project_file() {
    let dir = project();
    let (code, out, err) = crunk(dir.path(), &["guidelines", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let env = json_of(&out);
    assert_eq!(env["data"]["source"], "builtin");
    assert!(
        env["data"]["text"]
            .as_str()
            .unwrap()
            .contains("crunk outline")
    );

    std::fs::write(dir.path().join("design/guidelines.md"), "# Mine\n").expect("write");
    let (code, out, _) = crunk(dir.path(), &["guidelines", "--json"]);
    assert_eq!(code, 0, "{out}");
    let env = json_of(&out);
    assert_eq!(env["data"]["source"], "project");
    assert_eq!(env["data"]["text"], "# Mine\n");
}

// frob:tests crates/crunk/src/outline.rs::Outline
// frob:tests crates/crunk/src/guidelines.rs::Guidelines
// frob:tests crates/crunk/src/query.rs::Query
// frob:tests crates/crunk/src/map.rs::Map
#[test]
fn serve_lists_outline_guidelines_search_and_map_as_read_only_tools() {
    let dir = project();
    let req = json!({"jsonrpc":"2.0","id":1,"method":"tools/list"});
    let mut out = Vec::new();
    crunk::cli()
        .serve_mcp(Cursor::new(format!("{req}\n")), &mut out, dir.path())
        .expect("serve");
    let reply: Value = serde_json::from_slice(&out).expect("json reply");
    let tools = reply["result"]["tools"].as_array().expect("tools");
    for name in [
        "crunk_outline",
        "crunk_guidelines",
        "crunk_query",
        "crunk_map",
    ] {
        let tool = tools
            .iter()
            .find(|t| t["name"] == name)
            .unwrap_or_else(|| panic!("{name} listed in {tools:?}"));
        assert_eq!(tool["annotations"]["readOnlyHint"], true, "{name}");
    }
}
