//! An unknown `frob.toml` key is refused the same way by `init`, `doctor` and `check` (frob:ticket 01M4CTV0F8HWA7DPXYYDBE4TDJ).

use crate::common;

use std::path::Path;

use serde_json::Value;

fn run(dir: &Path, verb: &str) -> (i32, Value) {
    let out = common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .args([verb, "--json"])
        .output()
        .expect("run frob");
    let json = serde_json::from_slice(&out.stdout).unwrap_or(Value::Null);
    (out.status.code().expect("exit code"), json)
}

fn refusals(config: &str) -> Vec<(i32, Value)> {
    let dir = common::git_repo();
    std::fs::write(dir.path().join("frob.toml"), config).expect("frob.toml");
    ["init", "doctor", "check"]
        .iter()
        .map(|verb| run(dir.path(), verb))
        .collect()
}

fn assert_same_refusal(config: &str, key: &str) {
    let all = refusals(config);
    let first_code = all[0].0;
    assert_ne!(first_code, 0, "init must refuse: {:?}", all[0].1);
    for (verb, (code, json)) in ["init", "doctor", "check"].iter().zip(&all) {
        assert_eq!(*code, first_code, "{verb} exit code: {json}");
        assert_eq!(json["error"]["code"], "E-CONFIG", "{verb}: {json}");
        let message = json["error"]["message"].as_str().unwrap_or_default();
        assert!(message.contains(key), "{verb} names {key}: {json}");
    }
}

// frob:tests crates/frob/src/workspace.rs::load_config
#[test]
fn unknown_key_is_refused_by_init_doctor_and_check() {
    assert_same_refusal(
        "[tickets]\ndefault_milestone = \"x\"\n",
        "default_milestone",
    );
}
