//! `frob init`, `config sync` and `doctor` and the `[pm]` tables.
// frob:ticket 01M4069R19D2KZENDGEH83JZSW

use std::path::Path;
use std::process::Output;

use assert_cmd::Command;
use serde_json::Value;

const PM_KEYS: [&str; 12] = [
    "pm.strict",
    "pm.pull",
    "pm.ready_min",
    "pm.ready_requires",
    "pm.done_requires",
    "pm.cycle_days",
    "pm.min_history",
    "pm.capacity_k",
    "pm.wip.in_progress_per_identity",
    "pm.wip.in_progress",
    "pm.classes.expedite_max",
    "pm.classes.intangible_share",
];

fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("git init");
    let status = std::process::Command::new("git")
        .args(["config", "user.email", "test@example.com"])
        .current_dir(dir.path())
        .status()
        .expect("git config");
    assert!(status.success());
    dir
}

fn frob(cwd: &Path, args: &[&str]) -> Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("json stdout")
}

fn toml_of(dir: &Path) -> toml::Table {
    std::fs::read_to_string(dir.join("frob.toml"))
        .expect("frob.toml")
        .parse()
        .expect("toml")
}

fn added(v: &Value) -> Vec<String> {
    v["data"]["config"]["added"]
        .as_array()
        .or_else(|| v["data"]["added"].as_array())
        .expect("added")
        .iter()
        .map(|k| k.as_str().expect("key").to_owned())
        .collect()
}

#[test]
fn init_writes_every_pm_knob_with_its_default_and_a_doc_comment() {
    let dir = repo();
    let out = frob(dir.path(), &["init"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let keys = added(&json(&out));
    for k in PM_KEYS {
        assert!(
            keys.iter().any(|a| a == k),
            "init did not add {k}: {keys:?}"
        );
    }
    let table = toml_of(dir.path());
    let pm = table["pm"].as_table().expect("[pm]");
    assert_eq!(pm["pull"].as_str(), Some("rank"));
    assert_eq!(pm["ready_min"].as_integer(), Some(4));
    assert_eq!(pm["cycle_days"].as_integer(), Some(7));
    assert_eq!(pm["ready_requires"].as_array().map(Vec::len), Some(5));
    assert_eq!(pm["wip"]["in_progress"].as_integer(), Some(2));
    assert_eq!(pm["wip"]["in_progress_per_identity"].as_integer(), Some(1));
    assert_eq!(pm["classes"]["expedite_max"].as_integer(), Some(1));
    assert_eq!(pm["classes"]["intangible_share"].as_float(), Some(0.2));
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).expect("text");
    assert!(text.contains("# Replenishment order point"), "{text}");
    assert!(text.contains("[pm.wip]"), "{text}");
}

#[test]
fn config_sync_adds_pm_tables_without_touching_other_keys() {
    let dir = repo();
    let original = "# mine\n[check]\nfail_on = \"warning\"\n\n[pm]\nready_min = 9\n";
    std::fs::write(dir.path().join("frob.toml"), original).expect("write");
    let out = frob(dir.path(), &["config", "sync"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let keys = added(&json(&out));
    assert!(!keys.iter().any(|k| k == "pm.ready_min"), "{keys:?}");
    assert!(keys.iter().any(|k| k == "pm.wip.in_progress"), "{keys:?}");
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).expect("text");
    assert!(
        text.starts_with("# mine\n[check]\nfail_on = \"warning\"\n"),
        "{text}"
    );
    let table = toml_of(dir.path());
    assert_eq!(table["pm"]["ready_min"].as_integer(), Some(9));
    assert_eq!(table["check"]["fail_on"].as_str(), Some("warning"));
    assert_eq!(table["pm"]["cycle_days"].as_integer(), Some(7));
    let again = json(&frob(dir.path(), &["config", "sync"]));
    assert_eq!(again["already"], true);
}

#[test]
fn doctor_reports_missing_pm_knobs_as_cfg001() {
    let dir = repo();
    assert_eq!(frob(dir.path(), &["init"]).status.code(), Some(0));
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).expect("text");
    let mut doc: toml::Table = text.parse().expect("toml");
    doc["pm"].as_table_mut().expect("pm").remove("wip");
    std::fs::write(
        dir.path().join("frob.toml"),
        toml::to_string(&doc).expect("ser"),
    )
    .expect("write");
    let v = json(&frob(dir.path(), &["doctor"]));
    assert_eq!(v["data"]["config"]["missing_knobs"], 2);
    let msgs: Vec<String> = v["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "CFG001")
        .map(ToString::to_string)
        .collect();
    assert!(msgs.iter().any(|m| m.contains("pm.wip")), "{msgs:?}");
}

#[test]
fn unknown_requirement_name_is_a_config_error_with_did_you_mean() {
    let dir = repo();
    std::fs::write(
        dir.path().join("frob.toml"),
        "[pm]\nready_requires = [\"pointz\"]\n",
    )
    .expect("write");
    let out = frob(dir.path(), &["config", "show", "--effective"]);
    assert_ne!(out.status.code(), Some(0));
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("did you mean `points`?"), "{text}");
}
