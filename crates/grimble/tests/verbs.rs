//! The grimble verbs end to end: the sibling document against `docs/schemas/sibling.json`,
//! exit codes, idempotent init and fmt.

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;
use jsonschema::{Registry, Resource};
use serde_json::Value;

const SIBLING_ID: &str = "https://schemas.test/sibling.json";
const ENVELOPE_ID: &str = "https://schemas.test/envelope.json";

fn schemas_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/schemas")
}

fn load(name: &str) -> Value {
    let text = std::fs::read_to_string(schemas_dir().join(name)).expect("read schema");
    serde_json::from_str(&text).expect("schema is JSON")
}

/// Errors of the whole envelope against sibling.json (which composes envelope.json).
fn sibling_errors(envelope: &Value) -> Vec<String> {
    let mut sibling = load("sibling.json");
    sibling["$id"] = Value::String(SIBLING_ID.to_owned());
    let mut env = load("envelope.json");
    env["$id"] = Value::String(ENVELOPE_ID.to_owned());
    let registry = Registry::new()
        .add(ENVELOPE_ID, Resource::from_contents(env.clone()))
        .expect("register envelope")
        .prepare()
        .expect("prepare registry");
    let sibling_validator = jsonschema::options()
        .with_registry(&registry)
        .build(&sibling)
        .expect("compile sibling schema");
    sibling_validator
        .iter_errors(envelope)
        .map(|e| format!("{e} at {}", e.instance_path()))
        .collect()
}

/// Validate the envelope against sibling.json and envelope.json.
fn assert_valid_sibling(envelope: &Value) {
    let errors = sibling_errors(envelope);
    assert!(errors.is_empty(), "sibling document invalid: {errors:#?}");
    let mut env = load("envelope.json");
    env["$id"] = Value::String(ENVELOPE_ID.to_owned());
    let envelope_validator = jsonschema::options()
        .build(&env)
        .expect("compile envelope schema");
    assert!(
        envelope_validator.is_valid(envelope),
        "the envelope itself is invalid"
    );
}

fn repo() -> tempfile::TempDir {
    tempfile::tempdir().expect("tempdir")
}

fn grimble(dir: &Path, args: &[&str]) -> (i32, Value, String) {
    let cli = grimble::cli();
    let (code, out, err) = run_for_test(&cli, args, dir);
    let json = serde_json::from_str(&out).unwrap_or(Value::Null);
    (code, json, err)
}

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn check_json_without_a_model_is_a_valid_empty_sibling_document() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["ok"], true);
    assert_valid_sibling(&env);
    let doc = &env["data"];
    assert_eq!(doc["schema_version"], "gob.sibling/1");
    assert_eq!(doc["product"], "grimble");
    assert_eq!(doc["findings"].as_array().unwrap().len(), 0);
    assert!(
        doc["fidelity"]
            .as_array()
            .unwrap()
            .iter()
            .any(|f| f["language"] == "grmb" && f["level"] == "F4"),
        "fidelity report names the grmb adapter"
    );
    assert_eq!(doc["packs"].as_array().unwrap().len(), 0);
    assert!(doc["packs_digest"].as_str().unwrap().starts_with("blake3:"));
    assert_eq!(env["findings"].as_array().unwrap().len(), 0);
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_model_error_exits_one_and_the_finding_is_in_the_document() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode a : trusted { kind component; }\nnode a : trusted { kind component; }\n",
    );
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 1, "{env}");
    assert_eq!(env["ok"], true, "a failed gate still prints the document");
    assert_valid_sibling(&env);
    let findings = env["data"]["findings"].as_array().unwrap();
    assert!(
        findings.iter().any(|f| f["rule"] == "MDL001"
            && f["severity"] == "error"
            && f["file"] == "design/m.grmb"
            && f["line"] == 4),
        "{findings:#?}"
    );
    let entities = env["data"]["entities"].as_array().unwrap();
    assert!(entities.iter().any(|e| e["anchor"] == "node/a"));
    let mut broken = env.clone();
    broken["data"]["findings"][0]
        .as_object_mut()
        .unwrap()
        .remove("required");
    assert!(
        !sibling_errors(&broken).is_empty(),
        "the schema rejects a finding without its required mark"
    );
    let (code, _, _) = grimble(dir.path(), &["check", "--json", "--fail-on", "none"]);
    assert_eq!(code, 0, "--fail-on none never fails on findings");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn an_accept_clause_parks_its_finding_and_is_listed() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\nnode cli : trusted {\n  kind component;\n  owns \"nowhere/**\";\n  owns \"design/**\";\n  owns \"grimble.toml\";\n  accept MDL005 because=\"planned crate\";\n}\n",
    );
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_valid_sibling(&env);
    let doc = &env["data"];
    assert_eq!(doc["findings"].as_array().unwrap().len(), 0);
    let suppressed = doc["suppressed"].as_array().unwrap();
    assert_eq!(suppressed.len(), 1, "{doc:#}");
    let exc = &doc["exceptions"][0];
    assert_eq!(suppressed[0]["exception"], exc["id"]);
    assert_eq!(exc["kind"], "accept");
    assert_eq!(exc["suppresses"], 1);
    let (code, listed, _) = grimble(dir.path(), &["exceptions", "list", "--json"]);
    assert_eq!(code, 0);
    assert_eq!(listed["data"]["count"], 1);
}

// frob:tests crates/grimble/src/init.rs::Init
#[test]
fn init_twice_is_idempotent() {
    let dir = repo();
    let (code, first, _) = grimble(dir.path(), &["init", "--json"]);
    assert_eq!(code, 0, "{first}");
    assert_eq!(first["already"], false);
    let config = std::fs::read_to_string(dir.path().join("grimble.toml")).unwrap();
    assert!(config.contains("[compute]") && config.contains("expansion_steps = 1000"));
    assert!(
        config.contains("models = [\"design/model.grmb\"]"),
        "{config}"
    );
    let model = std::fs::read_to_string(dir.path().join("design/model.grmb")).unwrap();
    assert_eq!(model, "grimble = \"2\";\nmodule model;\n");
    let (code, second, _) = grimble(dir.path(), &["init", "--json"]);
    assert_eq!(code, 0);
    assert_eq!(second["already"], true, "{second}");
    assert_eq!(
        std::fs::read_to_string(dir.path().join("grimble.toml")).unwrap(),
        config
    );
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "an initialized repository checks clean: {env}");
    assert_valid_sibling(&env);
    let (code, fmt, _) = grimble(dir.path(), &["fmt", "--check", "--json"]);
    assert_eq!(code, 0, "the seeded model is formatted: {fmt}");
}

// frob:tests crates/grimble/src/fmt_cmd.rs::Fmt
#[test]
fn fmt_check_fails_on_an_unformatted_file_and_fmt_fixes_it() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble   =   \"2\";\nmodule m;\nnode   a : trusted {   kind component; }\n",
    );
    let (code, env, _) = grimble(dir.path(), &["fmt", "--check", "--json"]);
    assert_eq!(code, 1, "{env}");
    assert_eq!(env["data"]["changed"][0], "design/m.grmb");
    let (code, _, _) = grimble(dir.path(), &["fmt", "--json"]);
    assert_eq!(code, 0);
    let (code, env, _) = grimble(dir.path(), &["fmt", "--check", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["already"], true);
}

// frob:tests crates/gob-product/src/doctor.rs::Doctor
#[test]
fn doctor_reports_fidelity_model_and_config_status() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[packs]\nenabled = [\"grimble/core-effects\"]\n",
    );
    write(dir.path(), "design/m.grmb", "grimble = \"2\";\nmodule m;\n");
    let (code, env, _) = grimble(dir.path(), &["doctor", "--json"]);
    assert_eq!(code, 0, "{env}");
    let data = &env["data"];
    assert_eq!(data["config"]["status"], "ok");
    assert_eq!(data["config"]["packs_unloaded"], true);
    assert_eq!(data["model"][0]["status"], "parsed");
    assert!(
        data["languages"]
            .as_array()
            .unwrap()
            .iter()
            .any(|l| l["language"] == "grmb" && l["fidelity"] == "F4" && l["files"] == 1)
    );
    assert!(
        env["warnings"][0].as_str().unwrap().contains("packs"),
        "packs-not-loaded warning: {env}"
    );
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn a_bad_grimble_toml_is_a_refusal() {
    let dir = repo();
    write(dir.path(), "grimble.toml", "[compute]\nbogus = 1\n");
    let (code, env, _) = grimble(dir.path(), &["check", "--json"]);
    assert_eq!(code, 3, "{env}");
    assert_eq!(env["ok"], false);
}

// frob:tests crates/grimble/src/main.rs::main
#[test]
fn the_binary_prints_exactly_one_envelope_line_on_stdout() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    let out = assert_cmd::Command::cargo_bin("grimble")
        .unwrap()
        .args(["check", "--json", "-vv"])
        .current_dir(dir.path())
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8(out.stdout).unwrap();
    assert_eq!(stdout.lines().count(), 1, "one line: {stdout}");
    assert!(stdout.ends_with('\n'));
    let env: Value = serde_json::from_str(&stdout).unwrap();
    assert_valid_sibling(&env);
}

// frob:ticket 01M4M5CQ9529KH526299QXXFVF
const GRL_RULE: &str = "rule NOPE001 \"no-dbg\" {
  lang rust

  find d: `dbg!($$$ARGS)`
  where not d inside KIND
  report d \"remove dbg! before committing\"

  example fire \"\"\"
    fn f(x: u32) -> u32 { dbg!(x) }        //~ warn
  \"\"\"
  example clean \"\"\"
    fn f(x: u32) -> u32 { x }
  \"\"\"

  explain \"\"\"
    `dbg!` prints to stderr and is meant for local debugging only.

    ## Remedy
    Delete the call, or log through `tracing` if the value matters.
  \"\"\"
}
";

// frob:ticket 01M4M5CQ9529KH526299QXXFVF
// frob:tests crates/grimble/src/compile_cmd.rs::Compile
#[test]
fn compile_fails_on_an_unknown_kind() {
    let dir = repo();
    write(
        dir.path(),
        "rules/bad.grl",
        &GRL_RULE.replace("KIND", "tset"),
    );
    let (code, env, err) = grimble(dir.path(), &["compile", "rules/bad.grl", "--json"]);
    assert_eq!(code, 1, "{env} {err}");
    let report = env["data"]["files"][0]["report"].as_str().unwrap_or("");
    assert!(
        report.contains("error[GRL001]: unknown kind `tset`"),
        "{report}"
    );
    let (code, _, err) = grimble(dir.path(), &["compile", "--text"]);
    assert_eq!(code, 1);
    assert!(
        err.contains("GRL001"),
        "text mode prints the diagnostic: {err}"
    );
}

// frob:ticket 01M4M5CQ9529KH526299QXXFVF
// frob:tests crates/grimble/src/compile_cmd.rs::Compile
#[test]
fn compile_passes_a_valid_file_silently() {
    let dir = repo();
    write(
        dir.path(),
        "rules/ok.grl",
        &GRL_RULE.replace("KIND", "test"),
    );
    let (code, env, err) = grimble(dir.path(), &["compile", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    assert_eq!(env["data"]["files"][0]["errors"], 0);
    assert_eq!(env["data"]["files"][0]["report"], "");
}

// frob:tests crates/grimble/src/config_for.rs::run
// frob:ticket 01M3ZX7K04VN51PGCXT9DCYMWB
#[test]
fn config_for_names_the_line_and_scopes_by_path() {
    let dir = repo();
    write(
        dir.path(),
        "grimble.toml",
        "[[packs.enable]]\nname = \"react\"\npaths = [\"frontend/**\"]\n\n[[packs.enable]]\nname = \"core\"\n",
    );
    let (code, env, err) = grimble(dir.path(), &["config", "--for", "frontend/a.tsx", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    let packs = env["data"]["packs"].as_array().unwrap();
    assert_eq!(packs[0]["name"], "react");
    assert_eq!(packs[0]["config_line"], 1);
    assert_eq!(packs[1]["name"], "core");
    assert_eq!(packs[1]["config_line"], 5);

    let (code, env, err) = grimble(dir.path(), &["config", "--for", "backend/b.ts", "--json"]);
    assert_eq!(code, 0, "{env} {err}");
    let packs = env["data"]["packs"].as_array().unwrap();
    assert_eq!(packs.len(), 1);
    assert_eq!(packs[0]["name"], "core");
}
