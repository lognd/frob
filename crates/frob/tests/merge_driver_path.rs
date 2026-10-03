//! `frob init` and `frob doctor` pick and check the merge driver against `frob` on PATH.
// frob:ticket 01M40SG11J388ZYWB7YJD0NPX1
#![cfg(unix)]

use std::os::unix::fs::{PermissionsExt, symlink};
use std::path::{Path, PathBuf};
use std::process::Output;

use assert_cmd::Command;
use serde_json::Value;

const KEY: &str = "merge.frob-ledger.driver";

/// A temp repository (never this repository's own config).
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    gob_git::Repo::init(dir.path()).expect("git init");
    dir
}

/// The binary under test.
fn frob_bin() -> PathBuf {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .get_program()
        .into()
}

/// `PATH` with `first` prepended to the inherited one (git must stay reachable).
fn path_with(first: &Path) -> String {
    format!(
        "{}:{}",
        first.display(),
        std::env::var("PATH").unwrap_or_default()
    )
}

/// A directory holding a stub `frob` script that prints `version`.
fn stub_dir(version: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let stub = dir.path().join("frob");
    std::fs::write(&stub, format!("#!/bin/sh\necho 'frob {version}'\n")).expect("write stub");
    std::fs::set_permissions(&stub, std::fs::Permissions::from_mode(0o755)).expect("chmod");
    dir
}

/// A directory whose `frob` is a symlink to the binary under test.
fn running_dir() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    symlink(frob_bin(), dir.path().join("frob")).expect("symlink");
    dir
}

/// Run `frob --json <args>` in `cwd` with `path_dir` first on PATH.
fn frob(cwd: &Path, path_dir: &Path, args: &[&str]) -> Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .env("PATH", path_with(path_dir))
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout).expect("json envelope")
}

/// The local git config value of the driver key.
fn driver(cwd: &Path) -> Option<String> {
    let out = std::process::Command::new("git")
        .args(["config", "--local", "--get", KEY])
        .current_dir(cwd)
        .output()
        .expect("git config");
    out.status
        .success()
        .then(|| String::from_utf8_lossy(&out.stdout).trim().to_owned())
}

fn set_driver(cwd: &Path, value: &str) {
    let st = std::process::Command::new("git")
        .args(["config", "--local", KEY, value])
        .current_dir(cwd)
        .status()
        .expect("git config");
    assert!(st.success());
}

/// Acceptance 1: a different frob earlier on PATH makes init write the absolute path and say why.
// frob:tests crates/frob/src/init.rs::Init
#[test]
fn init_writes_the_absolute_path_when_path_has_another_frob() {
    let dir = repo();
    let other = stub_dir("9.9.9");
    let out = frob(dir.path(), other.path(), &["init"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    let exe = frob_bin().canonicalize().expect("canonical");
    let cmd = driver(dir.path()).expect("driver set");
    assert_eq!(cmd, format!("{} merge-driver %O %A %B %P", exe.display()));
    let env = json(&out);
    let info = &env["data"]["driver"];
    assert_eq!(info["command"], cmd);
    let reason = info["reason"].as_str().expect("reason");
    assert!(reason.contains("different frob"), "{reason}");
    assert!(
        reason.contains(&other.path().display().to_string()),
        "{reason}"
    );
}

/// Bare `frob` stays when PATH resolves to the running binary.
// frob:tests crates/frob/src/init.rs::Init
#[test]
fn init_keeps_bare_frob_when_path_is_the_running_binary() {
    let dir = repo();
    let same = running_dir();
    let out = frob(dir.path(), same.path(), &["init"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    assert_eq!(
        driver(dir.path()).as_deref(),
        Some("frob merge-driver %O %A %B %P")
    );
}

/// `--driver-command` overrides the resolved command verbatim.
// frob:tests crates/frob/src/init.rs::Init
#[test]
fn init_driver_command_flag_overrides() {
    let dir = repo();
    let other = stub_dir("9.9.9");
    let out = frob(
        dir.path(),
        other.path(),
        &[
            "init",
            "--driver-command",
            "/opt/x/frob merge-driver %O %A %B %P",
        ],
    );
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    assert_eq!(
        driver(dir.path()).as_deref(),
        Some("/opt/x/frob merge-driver %O %A %B %P")
    );
    assert_eq!(json(&out)["data"]["driver"]["action"], "override");
}

/// Acceptance 2: doctor reports a driver resolving to a different frob, with the fix command.
// frob:tests crates/frob/src/doctor.rs::Doctor
#[test]
fn doctor_reports_a_mismatched_driver_with_the_fix() {
    let dir = repo();
    let other = stub_dir("9.9.9");
    set_driver(dir.path(), "frob merge-driver %O %A %B %P");
    let out = frob(dir.path(), other.path(), &["doctor"]);
    assert_eq!(out.status.code(), Some(0), "{}", json(&out));
    let env = json(&out);
    let d = &env["data"]["driver"];
    assert_eq!(d["state"], "mismatch");
    let exe = frob_bin().canonicalize().expect("canonical");
    assert_eq!(d["fix"], format!("{} init --fix-driver", exe.display()));
    assert!(
        env["warnings"].to_string().contains("init --fix-driver"),
        "{env}"
    );
}

/// Doctor reports a driver that resolves to nothing, and is quiet for a good one.
// frob:tests crates/frob/src/doctor.rs::Doctor
#[test]
fn doctor_reports_unresolvable_and_ok_drivers() {
    let dir = repo();
    let same = running_dir();
    set_driver(dir.path(), "/nonexistent/frob merge-driver %O %A %B %P");
    let env = json(&frob(dir.path(), same.path(), &["doctor"]));
    assert_eq!(env["data"]["driver"]["state"], "unresolvable");
    set_driver(dir.path(), "frob merge-driver %O %A %B %P");
    let env = json(&frob(dir.path(), same.path(), &["doctor"]));
    assert_eq!(env["data"]["driver"]["state"], "ok");
    assert!(env["data"]["driver"]["fix"].is_null());
}

/// Re-running init leaves a driver that already names the running binary; a different frob is reported and only `--fix-driver` rewrites it.
// frob:tests crates/frob/src/init.rs::Init
#[test]
fn init_rerun_is_idempotent_and_fix_driver_rewrites_a_mismatch() {
    let dir = repo();
    let other = stub_dir("9.9.9");
    assert_eq!(
        frob(dir.path(), other.path(), &["init"]).status.code(),
        Some(0)
    );
    let first = driver(dir.path());
    let again = frob(dir.path(), other.path(), &["init"]);
    assert_eq!(json(&again)["already"], true);
    assert_eq!(driver(dir.path()), first);

    let stale = "frob merge-driver %O %A %B %P";
    set_driver(dir.path(), stale);
    let left = frob(dir.path(), other.path(), &["init"]);
    let env = json(&left);
    assert_eq!(env["data"]["driver"]["action"], "mismatch-left");
    assert!(env["warnings"].to_string().contains("init --fix-driver"));
    assert_eq!(driver(dir.path()).as_deref(), Some(stale));

    let fixed = frob(dir.path(), other.path(), &["init", "--fix-driver"]);
    assert_eq!(fixed.status.code(), Some(0), "{}", json(&fixed));
    assert_eq!(driver(dir.path()), first);
}
