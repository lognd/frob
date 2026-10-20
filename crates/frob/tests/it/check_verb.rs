//! `frob check` through the binary: exit codes, `--fail-on`, `--explain`, `--timing`.

use crate::common;

use std::path::Path;

use serde_json::Value;

fn frob(dir: &Path, args: &[&str]) -> std::process::Output {
    common::frob_command()
        .current_dir(dir)
        .args(args)
        .output()
        .expect("run frob")
}

fn code(o: &std::process::Output) -> i32 {
    o.status.code().expect("exit code")
}

fn tree() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let marker = ["TO", "DO"].concat();
    std::fs::write(dir.path().join("lib.rs"), format!("// {marker}: later\n")).expect("write");
    // A configured repository: check refuses without frob.toml (~ANDZXZ4).
    let init = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
        .run(&gob_exec::Spec {
            program: gob_exec::Program::Git,
            args: vec!["init".to_owned(), "-q".to_owned()],
            cwd: Some(dir.path().to_path_buf()),
            env: Vec::new(),
            timeout: std::time::Duration::from_secs(30),
            capture: true,
        })
        .expect("git init");
    assert_eq!(init.status, gob_exec::Outcome::Exited(0));
    std::fs::write(dir.path().join("frob.toml"), "").expect("frob.toml");
    dir
}

#[test]
fn error_finding_exits_1_and_fail_on_none_exits_0() {
    let dir = tree();
    let failing = frob(dir.path(), &["check", "--json"]);
    assert_eq!(code(&failing), 1);
    assert!(String::from_utf8_lossy(&failing.stdout).contains("TODO001"));
    let ok = frob(
        dir.path(),
        &["check", "--json", "--fail-on", "none", "--timing"],
    );
    assert_eq!(code(&ok), 0);
    let v: Value = serde_json::from_slice(&ok.stdout).expect("json");
    assert_eq!(v["data"]["counts"]["error"], 1);
    assert!(v["data"]["timing"]["stages"].is_array());
    assert_eq!(v["data"]["findings"][0]["rule"], "TODO001");
}

// frob:ticket 01M4FCZ19XSPWE1EDABY6GKQPS
#[test]
fn failing_check_json_carries_structured_findings_and_a_one_line_message() {
    let dir = tree();
    let failing = frob(dir.path(), &["check", "--json"]);
    assert_eq!(code(&failing), 1);
    let v: Value = serde_json::from_slice(&failing.stdout).expect("json");
    assert_eq!(v["ok"], false);
    let findings = v["findings"].as_array().expect("findings array");
    assert!(findings.iter().any(|f| f["rule"] == "TODO001"));
    let message = v["error"]["message"].as_str().expect("message");
    assert!(!message.contains('\n'), "message is one line: {message}");
    assert!(message.contains("1 error(s)"));
}

#[test]
fn explain_prints_the_rule_page_and_unknown_is_usage() {
    let dir = tree();
    let ok = frob(dir.path(), &["check", "--json", "--explain", "TODO001"]);
    assert_eq!(code(&ok), 0);
    let v: Value = serde_json::from_slice(&ok.stdout).expect("json");
    assert_eq!(v["data"]["explain"]["id"], "TODO001");
    assert_eq!(
        code(&frob(dir.path(), &["check", "--explain", "NOPE999"])),
        2
    );
    assert_eq!(code(&frob(dir.path(), &["check", "--only", "NOPE"])), 2);
}

/// `git status --porcelain` of `dir`, to prove a measurement run left the tree alone.
fn porcelain(dir: &Path) -> String {
    let out = gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
        .run(&gob_exec::Spec {
            program: gob_exec::Program::Git,
            args: vec!["status".to_owned(), "--porcelain".to_owned()],
            cwd: Some(dir.to_path_buf()),
            env: Vec::new(),
            timeout: std::time::Duration::from_secs(30),
            capture: true,
        })
        .expect("git status");
    out.stdout.clone()
}

// frob:ticket 01M3DG64CFWRYVDS3DGW91G8EK
#[test]
fn read_only_check_leaves_a_fixable_tree_untouched_while_fix_rewrites_it() {
    let dir = tree();
    let file = dir.path().join("lib.rs");
    std::fs::write(&file, "// frob:pure\nfn a() {}\n").expect("write");
    let git = |args: &[&str]| {
        gob_exec::Runner::new(gob_exec::Limits { jobs: 1 })
            .run(&gob_exec::Spec {
                program: gob_exec::Program::Git,
                args: args.iter().map(|a| (*a).to_owned()).collect(),
                cwd: Some(dir.path().to_path_buf()),
                env: vec![
                    ("GIT_AUTHOR_NAME".to_owned(), "t".to_owned()),
                    ("GIT_AUTHOR_EMAIL".to_owned(), "t@t".to_owned()),
                    ("GIT_COMMITTER_NAME".to_owned(), "t".to_owned()),
                    ("GIT_COMMITTER_EMAIL".to_owned(), "t@t".to_owned()),
                ],
                timeout: std::time::Duration::from_secs(30),
                capture: true,
            })
            .expect("git")
    };
    std::fs::write(dir.path().join(".gitignore"), ".frob/\n").expect("gitignore");
    git(&["add", "-A"]);
    git(&["commit", "-q", "-m", "seed"]);
    assert_eq!(porcelain(dir.path()), "");
    let before = std::fs::read_to_string(&file).expect("read");

    let plain = frob(dir.path(), &["check", "--json", "--fail-on", "none"]);
    assert!(String::from_utf8_lossy(&plain.stdout).contains("DSL003"));
    assert_eq!(porcelain(dir.path()), "", "a read-only check changed the tree");
    assert_eq!(std::fs::read_to_string(&file).expect("read"), before);

    let fixed = frob(dir.path(), &["check", "--fix", "--json", "--fail-on", "none"]);
    assert_eq!(code(&fixed), 0, "{}", String::from_utf8_lossy(&fixed.stderr));
    assert_ne!(std::fs::read_to_string(&file).expect("read"), before);
    assert!(porcelain(dir.path()).contains("lib.rs"));
}
