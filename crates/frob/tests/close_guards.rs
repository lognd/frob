//! `[pm] done_requires` enforced at close: criteria, children, docs, objective and fragment, plus the default frob tool.
// frob:ticket 01M40WS6200M99J09D5XGAS05X

use std::path::Path;
use std::process::Output;
use std::time::Duration;

use assert_cmd::Command;
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

/// A trunk-mode repository with `frob init` run, `done_requires` set to `requires`, and one commit.
fn repo(requires: &[&str]) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    git(dir.path(), &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(dir.path(), &["config", "user.name", "Test User"]);
    git(dir.path(), &["config", "user.email", "test@example.com"]);
    git(dir.path(), &["config", "core.autocrlf", "false"]);
    assert_eq!(code(&frob(dir.path(), &["init"])), 0);
    common::set_done_requires(dir.path(), requires);
    git(dir.path(), &["add", "-A"]);
    git(dir.path(), &["commit", "-q", "-m", "base"]);
    dir
}

fn frob(dir: &Path, args: &[&str]) -> Output {
    Command::cargo_bin("frob")
        .expect("frob binary")
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

fn chore(dir: &Path, extra: &[&str]) -> String {
    let mut args = vec!["ticket", "new", "--title", "t", "--type", "chore"];
    args.extend_from_slice(extra);
    ok(dir, &args)["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

fn close(dir: &Path, id: &str, extra: &[&str]) -> Output {
    let mut args = vec!["ticket", "close", id, "--outcome", "done"];
    args.extend_from_slice(extra);
    frob(dir, &args)
}

fn refusal_text(out: &Output) -> String {
    let v = json(out);
    format!("{} {}", v["error"]["message"], v["error"]["remedy"])
}

// frob:tests crates/frob-evidence/src/done.rs::DoneGuard.check
#[test]
fn a_chore_with_an_unbound_criterion_is_refused_naming_the_criterion_and_the_bypass() {
    let dir = repo(&["criteria_evidenced"]);
    let id = chore(dir.path(), &["--acceptance", "the widget works"]);
    let out = close(dir.path(), &id, &[]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-CRITERIA-UNBOUND");
    let text = refusal_text(&out);
    assert!(text.contains("the widget works"), "{text}");
    assert!(text.contains("--no-evidence --reason"), "{text}");
}

#[test]
fn the_bypass_closes_and_records_the_event() {
    let dir = repo(&["criteria_evidenced"]);
    let id = chore(dir.path(), &["--acceptance", "the widget works"]);
    let closed = ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-evidence",
            "--reason",
            "measured by hand",
        ],
    );
    assert_eq!(closed["data"]["category"], "done");
    let shown = ok(dir.path(), &["ticket", "show", &id, "--events"]);
    let kinds: Vec<_> = shown["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .map(|e| e["kind"].as_str().expect("kind"))
        .collect();
    assert!(kinds.contains(&"evidence-bypass"), "{kinds:?}");
}

#[test]
fn all_criteria_bound_closes_and_a_ticket_without_criteria_warns() {
    let dir = repo(&["criteria_evidenced"]);
    let id = chore(dir.path(), &["--acceptance", "one", "--acceptance", "two"]);
    for n in ["1", "2"] {
        ok(
            dir.path(),
            &[
                "ticket",
                "evidence",
                "add",
                &id,
                "--provider",
                "file",
                "--ref",
                "frob.toml",
                "--accepts",
                n,
            ],
        );
    }
    // Both criteria bind through the same file reference (one record per criterion).
    let closed = ok(dir.path(), &["ticket", "close", &id, "--outcome", "done"]);
    assert_eq!(closed["data"]["category"], "done");

    let bare = chore(dir.path(), &[]);
    let closed = ok(dir.path(), &["ticket", "close", &bare, "--outcome", "done"]);
    let warnings = closed["warnings"].as_array().expect("warnings");
    assert!(
        warnings.iter().any(|w| w
            .as_str()
            .is_some_and(|w| w.contains("no acceptance criteria"))),
        "{warnings:?}"
    );
}

#[test]
fn an_open_child_refuses_the_parent_close_and_is_named() {
    let dir = repo(&["no_open_children"]);
    let parent = chore(dir.path(), &[]);
    let child = chore(dir.path(), &["--parent", &parent]);
    let out = close(dir.path(), &parent, &[]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-OPEN-CHILDREN");
    let handle = ok(dir.path(), &["ticket", "show", &child])["data"]["summary"]["handle"]
        .as_str()
        .expect("handle")
        .to_owned();
    assert!(
        refusal_text(&out).contains(&handle),
        "{}",
        refusal_text(&out)
    );
    ok(
        dir.path(),
        &["ticket", "close", &child, "--outcome", "done"],
    );
    ok(
        dir.path(),
        &["ticket", "close", &parent, "--outcome", "done"],
    );
}

#[test]
fn the_running_frob_is_an_allowed_command_tool_without_listing_it() {
    let dir = repo(&[]);
    let id = chore(dir.path(), &["--acceptance", "frob answers"]);
    let exe = assert_cmd::cargo::cargo_bin("frob");
    let reference = format!("{} --version", exe.display());
    let added = ok(
        dir.path(),
        &[
            "ticket",
            "evidence",
            "add",
            &id,
            "--provider",
            "command",
            "--ref",
            &reference,
            "--accepts",
            "1",
        ],
    );
    assert_eq!(added["ok"], true);
    let denied = frob(
        dir.path(),
        &[
            "ticket",
            "evidence",
            "add",
            &id,
            "--provider",
            "command",
            "--ref",
            "/bin/echo hi",
        ],
    );
    assert_ne!(code(&denied), 0, "an unlisted tool stays refused");
}

#[test]
fn a_missing_fragment_refuses_with_the_remedy_and_a_present_one_closes() {
    let dir = repo(&["changelog_fragment"]);
    let id = chore(dir.path(), &[]);
    let out = close(dir.path(), &id, &[]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-CHANGELOG-FRAGMENT");
    let text = refusal_text(&out);
    assert!(text.contains(&format!("changelog.d/{id}.")), "{text}");
    assert!(text.contains("~HE2EX99"), "{text}");
    std::fs::create_dir_all(dir.path().join("changelog.d")).expect("mkdir");
    std::fs::write(
        dir.path().join(format!("changelog.d/{id}.added.md")),
        "Added a thing.\n",
    )
    .expect("fragment");
    ok(dir.path(), &["ticket", "close", &id, "--outcome", "done"]);
}

#[test]
fn an_unevaluable_requirement_is_unresolved_and_the_bypass_does_not_cover_it() {
    let dir = repo(&["docs_touched_or_excepted"]);
    let id = chore(dir.path(), &[]);
    let out = close(dir.path(), &id, &["--no-evidence", "--reason", "x"]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-UNRESOLVED");
    assert!(refusal_text(&out).contains("Unresolved"));
}

#[test]
fn an_objective_flavour_is_unresolved_and_a_plain_ticket_passes() {
    let dir = repo(&["objective_target_met"]);
    let plain = chore(dir.path(), &[]);
    ok(
        dir.path(),
        &["ticket", "close", &plain, "--outcome", "done"],
    );
    let obj = chore(dir.path(), &["--flavour", "quality_objective"]);
    let out = close(dir.path(), &obj, &[]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-UNRESOLVED");
}
