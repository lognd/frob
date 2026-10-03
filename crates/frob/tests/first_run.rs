//! A config-needing verb without `frob.toml` teaches `frob init` instead of running (~ANDZXZ4).
// frob:ticket 01M40FXV09GYGBH9YZZANDZXZ4

use std::path::Path;
use std::time::Duration;

use assert_cmd::Command;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

/// Run frob in `dir`.
fn frob(dir: &Path, args: &[&str]) -> std::process::Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
        .current_dir(dir)
        .args(args)
        .output()
        .expect("run frob")
}

/// A temp directory holding a git repository and no `frob.toml`.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = Spec {
        program: Program::Git,
        args: vec!["init".to_owned(), "-q".to_owned()],
        cwd: Some(dir.path().to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .expect("git init");
    assert_eq!(out.status, Outcome::Exited(0));
    let marker = ["TO", "DO"].concat();
    std::fs::write(dir.path().join("lib.rs"), format!("// {marker}: later\n")).expect("write");
    dir
}

fn envelope(o: &std::process::Output) -> Value {
    serde_json::from_slice(&o.stdout).expect("json envelope")
}

/// Assert `args` refuse with the teaching diagnostic in a repo without config.
fn assert_teaches(args: &[&str]) {
    let dir = repo();
    let out = frob(dir.path(), args);
    assert_eq!(out.status.code(), Some(3), "needs-action guard exit");
    let v = envelope(&out);
    assert_eq!(v["ok"], false);
    assert_eq!(v["error"]["code"], "E-NO-CONFIG");
    assert_eq!(v["error"]["remedy"], "frob init");
    assert_eq!(v["error"]["retryable"], false);
    let msg = v["error"]["message"].as_str().expect("message");
    for needle in [
        "frob.toml",
        ".gitignore entry for .frob/",
        ".gitattributes",
        "merge driver",
        "frob doctor",
    ] {
        assert!(msg.contains(needle), "message lacks {needle}: {msg}");
    }
    assert!(v["data"].is_null() || v["data"].get("findings").is_none());
    assert!(!String::from_utf8_lossy(&out.stdout).contains("TODO001"));
}

// frob:tests crates/frob/src/first_run.rs::require_config
#[test]
fn check_without_config_teaches_init_with_no_findings() {
    assert_teaches(&["check", "--json"]);
}

// frob:tests crates/frob/src/first_run.rs::require_config
#[test]
fn ticket_list_without_config_gives_the_same_diagnostic() {
    assert_teaches(&["ticket", "list", "--json"]);
}

// frob:tests crates/frob/src/first_run.rs::no_config_refusal
#[test]
fn text_mode_names_init_on_stderr() {
    let dir = repo();
    let out = frob(dir.path(), &["check", "--text"]);
    assert_eq!(out.status.code(), Some(3));
    let all =
        String::from_utf8_lossy(&out.stderr).into_owned() + &String::from_utf8_lossy(&out.stdout);
    assert!(
        all.contains("frob init") && all.contains("E-NO-CONFIG"),
        "{all}"
    );
}

// frob:tests crates/frob/src/first_run.rs::no_config_refusal
#[test]
fn outside_a_git_repository_says_to_run_inside_one() {
    let dir = tempfile::tempdir().expect("tempdir");
    let out = frob(dir.path(), &["check", "--json"]);
    assert_eq!(out.status.code(), Some(3));
    let v = envelope(&out);
    assert_eq!(v["error"]["code"], "E-NO-CONFIG");
    assert_eq!(v["error"]["remedy"], "git init");
    let msg = v["error"]["message"].as_str().expect("message");
    assert!(
        msg.contains("git init") && msg.contains("not inside"),
        "{msg}"
    );
}

// frob:tests crates/frob/src/first_run.rs::require_config
#[test]
fn doctor_schema_and_help_work_without_config() {
    let dir = repo();
    let doctor = frob(dir.path(), &["doctor", "--json"]);
    assert_ne!(
        envelope(&doctor)["error"]["code"],
        "E-NO-CONFIG",
        "doctor must not be guarded"
    );
    let schema = frob(dir.path(), &["check", "--schema"]);
    assert_eq!(schema.status.code(), Some(0));
    let schema_verb = frob(dir.path(), &["schema", "--json"]);
    assert_ne!(envelope(&schema_verb)["error"]["code"], "E-NO-CONFIG");
    let help = frob(dir.path(), &["--help"]);
    assert_eq!(help.status.code(), Some(0));
}

// frob:tests crates/frob/src/first_run.rs::require_config
#[test]
fn a_present_frob_toml_lets_check_run() {
    let dir = repo();
    std::fs::write(dir.path().join("frob.toml"), "").expect("write");
    let out = frob(dir.path(), &["check", "--json"]);
    assert_ne!(envelope(&out)["error"]["code"], "E-NO-CONFIG");
}
