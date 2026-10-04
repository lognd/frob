//! Sibling discovery (D87): next to the running frob first, then PATH; `check` runs it and `doctor` reports both copies.
// frob:ticket 01M421F7Q66MW38R7J1JS1VMBC
#![cfg(unix)]

use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::Output;

use serde_json::Value;

/// The binary under test.
fn frob_bin() -> PathBuf {
    assert_cmd::Command::cargo_bin("frob")
        .expect("frob binary")
        .get_program()
        .into()
}

/// A tool environment: `bin/` holding a real copy of frob (hard link when possible).
fn tool_env() -> (tempfile::TempDir, PathBuf) {
    let env = tempfile::tempdir().expect("tempdir");
    let bin = env.path().join("bin");
    std::fs::create_dir(&bin).expect("mkdir");
    let frob = bin.join("frob");
    if std::fs::hard_link(frob_bin(), &frob).is_err() {
        std::fs::copy(frob_bin(), &frob).expect("copy frob");
    }
    (env, frob)
}

/// Write an executable `grimble` stub into `dir`.
fn stub(dir: &Path, body: &str) {
    let path = dir.join("grimble");
    std::fs::write(&path, format!("#!/bin/sh\n{body}\n")).expect("write stub");
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
}

/// A repository configured for grimble.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("git init");
    std::fs::write(dir.path().join("grimble.toml"), "").expect("write");
    std::fs::write(dir.path().join("frob.toml"), "").expect("write");
    dir
}

/// Run `frob --json <args>` in `cwd` with `path_first` prepended to PATH (when given).
fn run(frob: &Path, cwd: &Path, path_first: Option<&Path>, args: &[&str]) -> Output {
    let mut dirs: Vec<PathBuf> = path_first.map(Path::to_path_buf).into_iter().collect();
    // Hermetic: drop inherited directories that already hold a real sibling.
    dirs.extend(
        std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default())
            .filter(|d| !d.join("grimble").exists() && !d.join("crunk").exists()),
    );
    let path = std::env::join_paths(dirs).expect("join PATH");
    std::process::Command::new(frob)
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .env("PATH", path)
        .args(if args.contains(&"--text") {
            None
        } else {
            Some("--json")
        })
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("json envelope")
}

/// Acceptance 1: grimble beside the running frob and not on PATH is found and run by `check`.
// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn check_runs_the_grimble_next_to_frob_when_path_has_none() {
    let (env, frob) = tool_env();
    let bin = env.path().join("bin");
    let repo = repo();
    let absent = json(&run(&frob, repo.path(), None, &["check"])).to_string();
    assert!(
        absent.contains("was not found next to frob or on PATH"),
        "{absent}"
    );
    stub(
        &bin,
        r#"echo '{"verb":"check","already":false,"ok":false,"data":null,"findings":[],"warnings":[],"error":{"code":"E-X","message":"ran beside frob","remedy":"x","retryable":false},"schema_version":1}'; exit 4"#,
    );
    let ran = json(&run(&frob, repo.path(), None, &["check"])).to_string();
    assert!(ran.contains("ran beside frob"), "{ran}");
    assert!(!ran.contains("was not found"), "{ran}");
}

/// Acceptance 2: different versions beside frob and on PATH are both reported; the one beside frob is used.
// frob:tests crates/frob/src/doctor.rs::Doctor
#[test]
fn doctor_reports_both_grimbles_and_uses_the_one_beside_frob() {
    let (env, frob) = tool_env();
    stub(&env.path().join("bin"), "echo 'grimble 1.0.0'");
    let on_path = tempfile::tempdir().expect("tempdir");
    stub(on_path.path(), "echo 'grimble 2.0.0'");
    let repo = repo();
    let out = run(&frob, repo.path(), Some(on_path.path()), &["doctor"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    let env_json = json(&out);
    let row = env_json["data"]["siblings"]
        .as_array()
        .expect("siblings")
        .iter()
        .find(|r| r["product"] == "grimble")
        .expect("grimble row");
    assert_eq!(row["location"], "beside-frob");
    assert_eq!(row["version"], "grimble 1.0.0");
    assert_eq!(row["other"]["version"], "grimble 2.0.0");
    assert_eq!(row["other"]["differs"], true);
    assert!(
        env_json["warnings"]
            .to_string()
            .contains("differs from the one next to frob"),
        "{env_json}"
    );
}

/// A grimble only on PATH is reported as such, with no second copy.
// frob:tests crates/frob/src/doctor.rs::Doctor
#[test]
fn doctor_reports_a_path_only_grimble() {
    let (_env, frob) = tool_env();
    let on_path = tempfile::tempdir().expect("tempdir");
    stub(on_path.path(), "echo 'grimble 2.0.0'");
    let repo = repo();
    let env_json = json(&run(&frob, repo.path(), Some(on_path.path()), &["doctor"]));
    let rows = env_json["data"]["siblings"].as_array().expect("siblings");
    let row = rows
        .iter()
        .find(|r| r["product"] == "grimble")
        .expect("row");
    assert_eq!(row["location"], "path");
    assert!(row["other"].is_null());
    let crunk = rows.iter().find(|r| r["product"] == "crunk").expect("row");
    assert_eq!(crunk["location"], "absent", "{crunk}");
}

/// `check` reports where each configured sibling was found as `data.siblings`; the text view lists them only under `-v`.
// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn check_reports_sibling_locations_in_json_and_only_under_verbose_in_text() {
    let (env, frob) = tool_env();
    let repo = repo();
    std::fs::write(
        repo.path().join("frob.toml"),
        "[check]\nrequire_siblings = false\n",
    )
    .expect("write");
    let absent = json(&run(&frob, repo.path(), None, &["check"]));
    let row = &absent["data"]["siblings"][0];
    assert_eq!(row["product"], "grimble", "{absent}");
    assert_eq!(row["location"], "absent");
    assert!(row["path"].is_null());
    stub(&env.path().join("bin"), "echo not-a-document");
    let beside = json(&run(&frob, repo.path(), None, &["check"]));
    let row = &beside["data"]["siblings"][0];
    assert_eq!(row["location"], "beside-frob", "{beside}");
    assert!(row["path"].as_str().is_some_and(|p| p.ends_with("grimble")));
    let quiet = run(&frob, repo.path(), None, &["--text", "check"]);
    assert!(!String::from_utf8_lossy(&quiet.stdout).contains("sibling grimble"));
    let loud = run(&frob, repo.path(), None, &["--text", "-v", "check"]);
    assert!(
        String::from_utf8_lossy(&loud.stdout).contains("sibling grimble: beside-frob"),
        "{}",
        String::from_utf8_lossy(&loud.stdout)
    );
}

/// Write an executable `crunk` stub into `dir`.
fn crunk_stub(dir: &Path, body: &str) {
    let path = dir.join("crunk");
    std::fs::write(&path, format!("#!/bin/sh\n{body}\n")).expect("write stub");
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).expect("chmod");
}

/// A repository configured for crunk alone.
fn crunk_repo() -> tempfile::TempDir {
    let dir = repo();
    std::fs::remove_file(dir.path().join("grimble.toml")).expect("remove");
    std::fs::write(dir.path().join("crunk.toml"), "").expect("write");
    dir
}

/// Crunk acceptance 1: a crunk beside frob and not on PATH is run by `check` when `crunk.toml` exists.
// frob:ticket 01M43ARWKFWVZZAR84NF50FAHB
// frob:tests crates/frob-check/src/sibling/mod.rs::Siblings
#[test]
fn check_runs_the_crunk_next_to_frob_when_path_has_none() {
    let (env, frob) = tool_env();
    let repo = crunk_repo();
    let absent = json(&run(&frob, repo.path(), None, &["check"])).to_string();
    assert!(
        absent.contains("`crunk` was not found next to frob or on PATH"),
        "{absent}"
    );
    crunk_stub(
        &env.path().join("bin"),
        r#"echo '{"verb":"check","already":false,"ok":false,"data":null,"findings":[],"warnings":[],"error":{"code":"E-X","message":"crunk ran beside frob","remedy":"x","retryable":false},"schema_version":1}'; exit 4"#,
    );
    let ran = json(&run(&frob, repo.path(), None, &["check"])).to_string();
    assert!(ran.contains("crunk ran beside frob"), "{ran}");
    assert!(!ran.contains("was not found"), "{ran}");
}

/// Crunk acceptance 2: different crunk versions beside frob and on PATH are both reported; the one beside frob is used.
// frob:ticket 01M43ARWKFWVZZAR84NF50FAHB
// frob:tests crates/frob/src/doctor.rs::Doctor
#[test]
fn doctor_reports_both_crunks_and_uses_the_one_beside_frob() {
    let (env, frob) = tool_env();
    crunk_stub(&env.path().join("bin"), "echo 'crunk 1.0.0'");
    let on_path = tempfile::tempdir().expect("tempdir");
    crunk_stub(on_path.path(), "echo 'crunk 2.0.0'");
    let repo = crunk_repo();
    let out = run(&frob, repo.path(), Some(on_path.path()), &["doctor"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    let env_json = json(&out);
    let row = env_json["data"]["siblings"]
        .as_array()
        .expect("siblings")
        .iter()
        .find(|r| r["product"] == "crunk")
        .expect("crunk row");
    assert_eq!(row["location"], "beside-frob");
    assert_eq!(row["version"], "crunk 1.0.0");
    assert_eq!(row["other"]["version"], "crunk 2.0.0");
    assert_eq!(row["other"]["differs"], true);
    assert!(
        env_json["warnings"]
            .to_string()
            .contains("differs from the one next to frob"),
        "{env_json}"
    );
}

/// Crunk acceptance 3: a crunk whose `--json` carries another `schema_version` is a required Unresolved and exit 1.
// frob:ticket 01M43ARWKFWVZZAR84NF50FAHB
// frob:tests crates/frob-check/src/sibling/mod.rs::Sib001
#[test]
fn a_crunk_with_another_schema_version_fails_check_with_exit_one() {
    let (env, frob) = tool_env();
    crunk_stub(
        &env.path().join("bin"),
        r#"echo '{"verb":"check","already":false,"ok":true,"data":{"schema_version":"gob.sibling/9","product":"crunk"},"findings":[],"warnings":[],"error":null,"schema_version":1}'"#,
    );
    let repo = crunk_repo();
    let out = run(&frob, repo.path(), None, &["check"]);
    assert_eq!(out.status.code(), Some(1), "{}", json(&out));
    let text = json(&out).to_string();
    assert!(
        text.contains("SIB001") && text.contains("(incompatible)"),
        "{text}"
    );
}
