//! The crunk verbs end to end: the sibling document against `docs/schemas/sibling.json`,
//! the no-config refusal, `doctor` and `--version`.

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

fn crunk(dir: &Path, args: &[&str]) -> (i32, Value, String) {
    let cli = crunk::cli();
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
fn check_without_crunk_toml_refuses_with_the_shared_no_config_code() {
    let dir = repo();
    let (code, env, _) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 3, "{env}");
    assert_eq!(env["ok"], false);
    assert_eq!(env["error"]["code"], "E-NO-CONFIG");
    assert!(
        env["error"]["remedy"]
            .as_str()
            .unwrap()
            .contains("crunk.toml"),
        "{env}"
    );
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn check_json_with_an_unusable_config_is_refused_not_passed() {
    let dir = repo();
    write(dir.path(), "crunk.toml", "");
    let (code, env, _) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 3, "{env}");
    assert_eq!(env["ok"], false);
    assert_eq!(env["error"]["code"], "E-CONFIG");
}

// frob:tests crates/gob-product/src/check.rs::Check
#[test]
fn check_json_with_a_valid_config_is_a_valid_sibling_document() {
    let dir = repo();
    write(
        dir.path(),
        "crunk.toml",
        &crunk_spec::presets::preset("default")
            .expect("default preset")
            .replace("[lint]", "[lint]\nTOKENS001 = \"off\""),
    );
    write(dir.path(), "styles/base/a.css", ".a { margin: 0; }\n");
    let (code, env, _) = crunk(dir.path(), &["check", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["ok"], true);
    assert_valid_sibling(&env);
    let doc = &env["data"];
    assert_eq!(doc["schema_version"], "gob.sibling/1");
    assert_eq!(doc["product"], "crunk");
}

// frob:tests crates/gob-product/src/doctor.rs::Doctor
#[test]
fn doctor_runs_without_a_config_and_reports_it_absent() {
    let dir = repo();
    let (code, env, _) = crunk(dir.path(), &["doctor", "--json"]);
    assert_eq!(code, 0, "{env}");
    assert_eq!(env["data"]["config"]["present"], false);
    assert_eq!(env["data"]["config"]["status"], "absent");
    write(dir.path(), "crunk.toml", "");
    let (_, env, _) = crunk(dir.path(), &["doctor", "--json"]);
    assert_eq!(env["data"]["config"]["status"], "ok");
    assert_eq!(env["data"]["version"], env!("CARGO_PKG_VERSION"));
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn version_flag_prints_the_workspace_version() {
    let out = assert_cmd::Command::cargo_bin("crunk")
        .expect("crunk binary")
        .arg("--version")
        .output()
        .expect("run crunk");
    assert!(out.status.success());
    let text = String::from_utf8(out.stdout).unwrap();
    assert!(text.contains(env!("CARGO_PKG_VERSION")), "{text}");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn a_bad_flag_exits_two() {
    let dir = repo();
    write(dir.path(), "crunk.toml", "");
    let (code, _, _) = crunk(dir.path(), &["check", "--no-such-flag"]);
    assert_eq!(code, 2);
}

/// Every `$ref` under `v` that points into the document's own `$defs`.
fn refs(v: &Value, out: &mut Vec<String>) {
    match v {
        Value::Object(m) => {
            for (k, x) in m {
                match (k.as_str(), x.as_str()) {
                    ("$ref", Some(r)) => out.push(r.to_owned()),
                    _ => refs(x, out),
                }
            }
        }
        Value::Array(a) => a.iter().for_each(|x| refs(x, out)),
        _ => {}
    }
}

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
// frob:tests crates/gob-cli/src/schema_cmd.rs::extend_config
#[test]
fn schema_prints_the_crunk_tables_with_keys_and_types_not_only_the_shared_ones() {
    let dir = repo();
    let (code, json, err) = crunk(dir.path(), &["schema"]);
    assert_eq!(code, 0, "{err}");
    let config = &json["data"]["config"];
    let props = config["properties"].as_object().expect("properties");
    for shared in ["check", "compute", "directives", "perf"] {
        assert!(props.contains_key(shared), "shared table [{shared}] kept");
    }
    for table in [
        "project",
        "palette",
        "scales",
        "typography",
        "layers",
        "org",
        "jsx",
        "tailwind",
        "tokens",
        "lint",
    ] {
        assert!(props.contains_key(table), "crunk table [{table}] missing");
    }
    let css_root = &props["project"]["properties"]["css_root"];
    assert_eq!(
        css_root["type"], "string",
        "keys carry their types: {css_root}"
    );
    // The shared tables' own refs are not this test's concern; crunk's must resolve.
    let mut wanted = Vec::new();
    for table in ["jsx", "tailwind", "tokens", "lint"] {
        refs(&props[table], &mut wanted);
    }
    assert!(!wanted.is_empty(), "the optional tables reference $defs");
    for r in wanted {
        let name = r.strip_prefix("#/$defs/").expect("local ref");
        assert!(
            config["$defs"].get(name).is_some(),
            "{r} dangles in the merged schema"
        );
    }
}
