//! `frob mirror render` output validates against the generated `docs/schemas/issue-projection.json`.
// frob:ticket 01M3ZX836BNV9H9K9ZCKNMAEDB

use serde_json::Value;

use crate::common;

fn frob(cwd: &std::path::Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob");
    serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "{args:?}: {e}: {}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        )
    })
}

#[test]
fn render_output_validates_against_the_committed_schema() {
    // frob:tests crates/frob/src/mirror_cmd.rs::MirrorRender
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    frob(p, &["ticket", "branch", "init"]);
    let id = frob(p, &["ticket", "new", "--title", "Mirror me"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let out = frob(p, &["mirror", "render", &id, "--json"]);
    assert_eq!(out["ok"], true, "{out}");
    let schema_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../docs/schemas/issue-projection.json");
    let schema: Value =
        serde_json::from_str(&std::fs::read_to_string(schema_path).expect("schema file"))
            .expect("schema json");
    let validator = jsonschema::validator_for(&schema).expect("schema compiles");
    let errors: Vec<String> = validator
        .iter_errors(&out["data"])
        .map(|e| e.to_string())
        .collect();
    assert!(errors.is_empty(), "{errors:?}\n{}", out["data"]);
    assert_eq!(out["data"]["title"], "Mirror me");
}
