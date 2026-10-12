//! `ticket fragment` end to end: write, refuse, force, remedy naming the verb, guard passes.
// frob:ticket 01M4069WHH6KXYWDAJD3TXB8SR
// frob:ticket 01M4FDQXEST75DK0NHDH4P5H15

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde_json::Value;

mod common;

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(dir.path(), &["config", "user.name", "Test User"]);
    git(dir.path(), &["config", "user.email", "test@example.com"]);
    git(dir.path(), &["config", "core.autocrlf", "false"]);
    assert_eq!(code(&frob(dir.path(), &["init"])), 0);
    common::set_done_requires(dir.path(), &["changelog_fragment"]);
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "base"]);
    dir
}

fn frob(dir: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(dir)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(out: &Output) -> Value {
    serde_json::from_slice(&out.stdout)
        .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)))
}

fn code(out: &Output) -> i32 {
    out.status.code().expect("exit code")
}

fn ok(dir: &Path, args: &[&str]) -> Value {
    let out = frob(dir, args);
    assert_eq!(
        code(&out),
        0,
        "{args:?}: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    json(&out)
}

fn ticket(dir: &Path, ty: &str) -> (String, String) {
    let v = ok(
        dir,
        &["ticket", "new", "--title", "Teach the widget", "--type", ty],
    );
    let d = &v["data"];
    (
        d["id"].as_str().expect("id").to_owned(),
        d["handle"].as_str().expect("handle").to_owned(),
    )
}

// frob:tests crates/frob/src/ticket/fragment_cmd.rs::Fragment.run
#[test]
fn writes_a_valid_fragment_from_the_title_with_the_mapped_type() {
    let dir = repo();
    for (ty, kind) in [("task", "changed"), ("story", "added"), ("docs", "changed")] {
        let (id, handle) = ticket(dir.path(), ty);
        let v = ok(dir.path(), &["ticket", "fragment", &handle]);
        assert_eq!(v["data"]["kind"], kind, "{ty}");
        let file = dir.path().join(format!("changelog.d/{id}.{kind}.md"));
        assert_eq!(
            std::fs::read_to_string(file).expect("written"),
            "Teach the widget.\n"
        );
    }
    let out = frob(
        dir.path(),
        &["release", "changelog", "--version", "0.532.0", "--check"],
    );
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
}

// frob:tests crates/frob/src/ticket/fragment_cmd.rs::Fragment.run
#[test]
fn type_and_text_flags_override_and_an_existing_fragment_is_refused_until_force() {
    let dir = repo();
    let (id, handle) = ticket(dir.path(), "task");
    let v = ok(
        dir.path(),
        &[
            "ticket",
            "fragment",
            &handle,
            "--type",
            "added",
            "--sentence",
            "frob: You can now teach widgets.",
        ],
    );
    assert_eq!(v["data"]["file"], format!("{id}.added.md"));
    let out = frob(dir.path(), &["ticket", "fragment", &handle]);
    assert_eq!(code(&out), 3);
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-FRAGMENT-EXISTS");
    assert!(
        v["error"]["remedy"]
            .as_str()
            .unwrap()
            .contains(&format!("frob ticket fragment {handle} --force"))
    );
    let v = ok(dir.path(), &["ticket", "fragment", &handle, "--force"]);
    assert_eq!(v["data"]["kind"], "changed");
    assert_eq!(v["data"]["replaced"][0], format!("{id}.added.md"));
    assert!(
        !dir.path()
            .join(format!("changelog.d/{id}.added.md"))
            .exists()
    );
}

// frob:tests crates/frob-evidence/src/done.rs::DoneGuard.check
#[test]
fn the_close_remedy_names_the_verb_and_the_guard_passes_after_writing() {
    let dir = repo();
    let (id, handle) = ticket(dir.path(), "task");
    let out = frob(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-evidence",
            "--reason",
            "test",
        ],
    );
    assert_eq!(code(&out), 3);
    let v = json(&out);
    assert_eq!(v["error"]["code"], "E-DONE-CHANGELOG-FRAGMENT");
    let remedy = v["error"]["remedy"].as_str().expect("remedy");
    assert!(
        remedy.contains(&format!("frob ticket fragment {handle}")),
        "{remedy}"
    );
    ok(dir.path(), &["ticket", "fragment", &handle]);
    ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-evidence",
            "--reason",
            "test",
        ],
    );
}

// frob:tests crates/frob/src/ticket/fragment_cmd.rs::Fragment.run
#[test]
fn bug_security_and_incident_tickets_require_a_sentence() {
    let dir = repo();
    for (ty, kind) in [
        ("bug", "fixed"),
        ("security", "security"),
        ("incident", "fixed"),
    ] {
        let (id, handle) = ticket(dir.path(), ty);
        let out = frob(dir.path(), &["ticket", "fragment", &handle]);
        assert_eq!(code(&out), 2, "{ty}");
        let msg = json(&out)["error"]["message"].as_str().unwrap().to_owned();
        assert!(
            msg.contains(&format!(
                "frob ticket fragment {handle} --sentence \"<what changed for the user>\""
            )),
            "{msg}"
        );
        assert!(
            !dir.path()
                .join(format!("changelog.d/{id}.{kind}.md"))
                .exists()
        );
        let v = ok(
            dir.path(),
            &[
                "ticket",
                "fragment",
                &handle,
                "--sentence",
                "frob: Fixed it.",
            ],
        );
        assert_eq!(v["data"]["kind"], kind, "{ty}");
    }
}

// frob:tests crates/frob/src/ticket/fragment_cmd.rs::Fragment.run
#[test]
fn a_configured_fragment_prefix_starts_the_skeleton() {
    let dir = repo();
    let toml = dir.path().join("frob.toml");
    let text = std::fs::read_to_string(&toml)
        .expect("read frob.toml")
        .replacen(
            "[release]\n",
            "[release]\nfragment_prefix = \"frob: \"\n",
            1,
        );
    assert!(
        text.contains("fragment_prefix"),
        "init writes a [release] table"
    );
    std::fs::write(&toml, text).expect("write frob.toml");
    let (id, handle) = ticket(dir.path(), "task");
    ok(dir.path(), &["ticket", "fragment", &handle]);
    let file = dir.path().join(format!("changelog.d/{id}.changed.md"));
    assert_eq!(
        std::fs::read_to_string(file).expect("written"),
        "frob: Teach the widget.\n"
    );
}
