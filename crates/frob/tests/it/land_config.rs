//! The `[land]` table is registered in `FrobConfig`, so validation, `config sync` and `doctor` accept it.
// frob:ticket 01M4D6NWQ3F11S4MB3KT5K4JHZ

use crate::common;

use std::path::Path;
use std::process::Output;

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
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

const LAND: &str = "[land]\nrequire_base_green = false\nci_required = [\"test*\"]\nci_ignore = []\nblock_on_unknown_ci = true\n";

// frob:tests crates/frob/src/config.rs::load
#[test]
fn config_sync_and_doctor_accept_a_land_table() {
    let dir = repo();
    std::fs::write(dir.path().join("frob.toml"), LAND).expect("write");
    let sync = frob(dir.path(), &["config", "sync"]);
    assert_eq!(
        sync.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&sync.stdout)
    );
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).expect("text");
    let doc: toml::Table = text.parse().expect("toml");
    assert_eq!(doc["land"]["require_base_green"].as_bool(), Some(false));
    assert_eq!(doc["land"]["block_on_unknown_ci"].as_bool(), Some(true));
    let doctor = frob(dir.path(), &["doctor"]);
    let v: serde_json::Value = serde_json::from_slice(&doctor.stdout).expect("json stdout");
    assert!(v["error"].is_null(), "{v}");
}

// frob:tests crates/frob/src/config.rs::load
#[test]
fn an_unknown_land_key_is_rejected() {
    let dir = repo();
    std::fs::write(
        dir.path().join("frob.toml"),
        "[land]\nrequire_base_gren = true\n",
    )
    .expect("write");
    let out = frob(dir.path(), &["doctor"]);
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).expect("json stdout");
    assert_eq!(v["error"]["code"], "E-CONFIG", "{v}");
    let err = v["error"]["message"].as_str().expect("config error");
    assert!(err.contains("require_base_gren"), "{err}");
}
