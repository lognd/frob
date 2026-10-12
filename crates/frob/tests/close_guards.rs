//! `[pm] done_requires` enforced at close: criteria, children, docs, objective and fragment, plus the default frob tool.
// frob:ticket 01M40WS6200M99J09D5XGAS05X

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
    // References are POSIX-quoted (`split_args`); build the line with the one quoting function so a
    // Windows path's backslashes are not eaten as escapes.
    let reference = gob_exec::command_line(
        gob_exec::Shell::Posix,
        &[gob_exec::Arg::from(exe), gob_exec::Arg::from("--version")],
    );
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
    // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
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

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
// frob:tests crates/frob/src/ticket/write.rs::Close.run
#[test]
fn no_changelog_with_a_reason_closes_without_a_fragment_and_records_the_event() {
    let dir = repo(&["changelog_fragment"]);
    let id = chore(dir.path(), &[]);
    let closed = ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-changelog",
            "--reason",
            "design document only",
        ],
    );
    assert_eq!(closed["data"]["category"], "done");
    assert_eq!(closed["data"]["changelog_exempt"], "design document only");
    let shown = ok(dir.path(), &["ticket", "show", &id, "--events"]);
    let kinds: Vec<_> = shown["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .map(|e| e["kind"].as_str().expect("kind"))
        .collect();
    assert!(kinds.contains(&"changelog-exempt"), "{kinds:?}");
    let x = &shown["data"]["changelog_exempt"];
    assert_eq!(x["reason"], "design document only");
    assert!(x["actor"].as_str().is_some_and(|a| !a.is_empty()), "{x}");
    let md = common::ticket_markdown(dir.path(), &id);
    assert!(
        md.contains("## Changelog") && md.contains("design document only"),
        "{md}"
    );
}

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
// frob:tests crates/frob/src/ticket/write.rs::Close.run
#[test]
fn no_changelog_without_a_reason_is_a_usage_error_and_changes_nothing() {
    let dir = repo(&["changelog_fragment"]);
    let id = chore(dir.path(), &[]);
    let out = close(dir.path(), &id, &["--no-changelog"]);
    assert_eq!(code(&out), 2, "{}", String::from_utf8_lossy(&out.stdout));
    let text = json(&out)["error"]["message"].to_string();
    assert!(text.contains("--no-changelog needs --reason"), "{text}");
    let blank = close(dir.path(), &id, &["--no-changelog", "--reason", "  "]);
    assert_eq!(code(&blank), 2);
    let shown = ok(dir.path(), &["ticket", "show", &id]);
    assert_eq!(shown["data"]["summary"]["category"], "todo");
}

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
// frob:tests crates/frob/src/ticket/write.rs::Close.run
#[test]
fn a_refused_close_keeps_the_exemption_event_and_a_retry_does_not_repeat_it() {
    let dir = repo(&["criteria_evidenced", "changelog_fragment"]);
    let id = chore(dir.path(), &["--acceptance", "the widget works"]);
    let flags = ["--no-changelog", "--reason", "design only"];
    let refused = close(dir.path(), &id, &flags);
    assert_eq!(code(&refused), 3);
    assert_eq!(json(&refused)["error"]["code"], "E-DONE-CRITERIA-UNBOUND");
    let count = |dir: &Path| -> (usize, Value) {
        let shown = ok(dir, &["ticket", "show", &id, "--events"]);
        let n = shown["data"]["events"]
            .as_array()
            .expect("events")
            .iter()
            .filter(|e| e["kind"] == "changelog-exempt")
            .count();
        (n, shown)
    };
    let (n, shown) = count(dir.path());
    assert_eq!(n, 1, "the intent is recorded though the close was refused");
    assert_ne!(shown["data"]["summary"]["category"], "done");
    assert_eq!(shown["data"]["changelog_exempt"]["reason"], "design only");
    ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-changelog",
            "--no-evidence",
            "--reason",
            "design only",
        ],
    );
    let (n, shown) = count(dir.path());
    assert_eq!(n, 1, "the retry reused the event");
    assert_eq!(shown["data"]["summary"]["category"], "done");
}

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
// frob:tests crates/frob-evidence/src/done.rs::DoneGuard.check
#[test]
fn the_missing_fragment_remedy_names_both_the_fragment_verb_and_the_exemption() {
    let dir = repo(&["changelog_fragment"]);
    let id = chore(dir.path(), &[]);
    let text = refusal_text(&close(dir.path(), &id, &[]));
    assert!(text.contains("frob ticket fragment"), "{text}");
    assert!(text.contains("--no-changelog --reason"), "{text}");
}

#[test]
fn an_invalid_fragment_refuses_close_with_the_validation_message() {
    // frob:ticket 01M4069WD4P8ZZ5HGQ5HE2EX99
    let dir = repo(&["changelog_fragment"]);
    let id = chore(dir.path(), &[]);
    std::fs::create_dir_all(dir.path().join("changelog.d")).expect("mkdir");
    let bad_type = dir.path().join(format!("changelog.d/{id}.improved.md"));
    std::fs::write(&bad_type, "frob: Improved a thing.\n").expect("fragment");
    let out = close(dir.path(), &id, &[]);
    assert_eq!(code(&out), 3);
    assert_eq!(json(&out)["error"]["code"], "E-DONE-CHANGELOG-FRAGMENT");
    let text = refusal_text(&out);
    assert!(text.contains("unknown type `improved`"), "{text}");
    std::fs::remove_file(&bad_type).expect("remove");
    std::fs::write(
        dir.path().join(format!("changelog.d/{id}.changed.md")),
        "\n",
    )
    .expect("fragment");
    let out = close(dir.path(), &id, &[]);
    assert_eq!(code(&out), 3);
    assert!(
        refusal_text(&out).contains("empty fragment"),
        "{}",
        refusal_text(&out)
    );
    std::fs::write(
        dir.path().join(format!("changelog.d/{id}.changed.md")),
        "frob: Changed a thing.\n",
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

/// A bug with an unbound criterion in a repo enforcing every default requirement.
fn bug_with_criterion(dir: &Path) -> String {
    ok(
        dir,
        &[
            "ticket",
            "new",
            "--title",
            "b",
            "--type",
            "bug",
            "--acceptance",
            "it is fixed",
        ],
    )["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
// frob:tests crates/frob-evidence/src/done.rs::guards_apply
#[test]
fn invalid_duplicate_and_wont_fix_close_a_bug_on_a_reason_alone() {
    let dir = repo(&[
        "criteria_evidenced",
        "no_open_children",
        "changelog_fragment",
    ]);
    for outcome in ["invalid", "duplicate", "wont-fix"] {
        let id = bug_with_criterion(dir.path());
        let out = frob(
            dir.path(),
            &[
                "ticket",
                "close",
                &id,
                "--outcome",
                outcome,
                "--reason",
                "not a bug",
            ],
        );
        assert_eq!(
            code(&out),
            0,
            "{outcome}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
        let shown = ok(dir.path(), &["ticket", "show", &id]);
        assert_eq!(shown["data"]["summary"]["category"], "done");
        assert_eq!(shown["data"]["summary"]["outcome"], outcome);
    }
}

// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
// frob:tests crates/frob/src/ticket/write.rs::Close.run
#[test]
fn a_non_done_outcome_without_a_reason_is_a_usage_error_and_changes_nothing() {
    let dir = repo(&[]);
    let id = bug_with_criterion(dir.path());
    let out = frob(
        dir.path(),
        &["ticket", "close", &id, "--outcome", "invalid"],
    );
    assert_eq!(code(&out), 2, "{}", String::from_utf8_lossy(&out.stdout));
    let blank = frob(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "invalid",
            "--reason",
            " ",
        ],
    );
    assert_eq!(code(&blank), 2);
    let shown = ok(dir.path(), &["ticket", "show", &id]);
    assert_eq!(shown["data"]["summary"]["category"], "todo");
}

// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
// frob:tests crates/frob-evidence/src/guard.rs::EvidenceGuard.check
#[test]
fn fixed_on_a_bug_without_evidence_is_still_refused() {
    let dir = repo(&["changelog_fragment"]);
    let id = bug_with_criterion(dir.path());
    let out = frob(dir.path(), &["ticket", "close", &id, "--outcome", "fixed"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-EVIDENCE-MISSING");
}

// frob:ticket 01M41KT4RMYMMP9SSFN8RZK7QV
// frob:tests crates/frob-land/src/verb.rs::Land.from_matches
#[test]
fn land_with_a_non_done_outcome_needs_a_reason() {
    let dir = repo(&[]);
    let out = frob(dir.path(), &["land", "--outcome", "wont-fix"]);
    assert_eq!(code(&out), 2, "{}", String::from_utf8_lossy(&out.stdout));
    let text = json(&out)["error"]["message"].to_string();
    assert!(text.contains("needs --reason"), "{text}");
}

/// The handle (with `~`) of ticket `id`.
fn handle_of(dir: &Path, id: &str) -> String {
    ok(dir, &["ticket", "show", id])["data"]["summary"]["handle"]
        .as_str()
        .expect("handle")
        .to_owned()
}

/// Give ticket `id` a branch `ticket/<handle>` with one commit the base lacks; returns the handle.
fn unmerged_branch(dir: &Path, id: &str) -> String {
    let handle = handle_of(dir, id);
    let branch = format!("ticket/{}", handle.trim_start_matches('~'));
    git(dir, &["checkout", "-q", "-b", &branch]);
    let file = format!("work-{}.txt", handle.trim_start_matches('~'));
    std::fs::write(dir.join(&file), "work\n").expect("write");
    git(dir, &["add", &file]);
    git(dir, &["commit", "-q", "-m", "unmerged ticket work"]);
    git(dir, &["checkout", "-q", "main"]);
    handle
}

// frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
// frob:tests crates/frob-evidence/src/done.rs::MergedGuard.check
// frob:tests crates/frob-evidence/src/done.rs::MergedGuard.for_ticket
// frob:tests crates/frob-evidence/src/done.rs::ticket_branch
#[test]
fn a_done_close_with_an_unmerged_ticket_branch_is_refused_naming_commits_and_remedy() {
    let dir = repo(&[]);
    let id = chore(dir.path(), &[]);
    unmerged_branch(dir.path(), &id);
    let out = close(dir.path(), &id, &["--no-evidence", "--reason", "docs only"]);
    assert_eq!(code(&out), 3, "{}", String::from_utf8_lossy(&out.stdout));
    assert_eq!(json(&out)["error"]["code"], "E-DONE-UNMERGED");
    let text = refusal_text(&out);
    assert!(text.contains("unmerged ticket work"), "{text}");
    assert!(text.contains("--no-land --reason"), "{text}");
    assert!(text.contains("frob land"), "{text}");
    let shown = ok(dir.path(), &["ticket", "show", &id]);
    assert_ne!(shown["data"]["summary"]["category"], "done");
}

// frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
// frob:tests crates/frob-evidence/src/done.rs::MergedGuard.record_exemption
// frob:tests crates/frob-evidence/src/done.rs::MergedGuard.allow_no_land
// frob:tests crates/frob-ledger/src/event.rs::land_exemption
#[test]
fn no_land_with_a_reason_closes_and_audits_and_without_a_reason_is_a_usage_error() {
    let dir = repo(&[]);
    let id = chore(dir.path(), &[]);
    unmerged_branch(dir.path(), &id);
    let bare = close(dir.path(), &id, &["--no-evidence", "--no-land"]);
    assert_eq!(code(&bare), 2);
    let closed = ok(
        dir.path(),
        &[
            "ticket",
            "close",
            &id,
            "--outcome",
            "done",
            "--no-evidence",
            "--no-land",
            "--reason",
            "work continues on another branch",
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
    assert!(kinds.contains(&"land-exempt"), "{kinds:?}");
}

// frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
// frob:tests crates/frob-evidence/src/done.rs::unmerged_commits
#[test]
fn merged_and_deleted_ticket_branches_close_cleanly_and_non_done_outcomes_are_exempt() {
    let dir = repo(&[]);
    let merged = chore(dir.path(), &[]);
    let handle = unmerged_branch(dir.path(), &merged);
    git(
        dir.path(),
        &[
            "merge",
            "-q",
            "--ff-only",
            &format!("ticket/{}", handle.trim_start_matches('~')),
        ],
    );
    let out = close(dir.path(), &merged, &["--no-evidence", "--reason", "x"]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));

    let deleted = chore(dir.path(), &[]);
    let h2 = unmerged_branch(dir.path(), &deleted);
    git(
        dir.path(),
        &[
            "branch",
            "-q",
            "-D",
            &format!("ticket/{}", h2.trim_start_matches('~')),
        ],
    );
    let out = close(dir.path(), &deleted, &["--no-evidence", "--reason", "x"]);
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));

    let dropped = chore(dir.path(), &[]);
    unmerged_branch(dir.path(), &dropped);
    let out = frob(
        dir.path(),
        &[
            "ticket",
            "close",
            &dropped,
            "--outcome",
            "wont-fix",
            "--reason",
            "not needed",
        ],
    );
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
}

// frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
// frob:tests crates/frob/src/ticket/doctor_cmd.rs::unmerged_done_issues
#[test]
fn doctor_reports_a_done_ticket_whose_branch_is_unmerged_unless_exempted() {
    let dir = repo(&[]);
    let id = chore(dir.path(), &[]);
    // Closed while the branch was absent, then the branch appears with unmerged work.
    let closed = close(dir.path(), &id, &["--no-evidence", "--reason", "x"]);
    assert_eq!(code(&closed), 0);
    let clean = ok(dir.path(), &["ticket", "doctor"]);
    assert_eq!(clean["data"]["ok"], true);
    unmerged_branch(dir.path(), &id);
    let out = frob(dir.path(), &["ticket", "doctor"]);
    let v = json(&out);
    assert_eq!(v["data"]["ok"], false, "{v}");
    assert_eq!(v["data"]["issues"][0]["code"], "E-DOCTOR-UNMERGED", "{v}");
    assert!(
        v["data"]["issues"][0]["message"]
            .to_string()
            .contains("unmerged ticket work")
    );

    let exempt = chore(dir.path(), &[]);
    unmerged_branch(dir.path(), &exempt);
    let out = frob(
        dir.path(),
        &[
            "ticket",
            "close",
            &exempt,
            "--outcome",
            "done",
            "--no-evidence",
            "--no-land",
            "--reason",
            "elsewhere",
        ],
    );
    assert_eq!(code(&out), 0, "{}", String::from_utf8_lossy(&out.stdout));
    let v = json(&frob(dir.path(), &["ticket", "doctor"]));
    let issues = v["data"]["issues"].as_array().expect("issues");
    assert_eq!(issues.len(), 1, "{v}");
}

/// Create a ticket of `ty` with `extra` flags and return its id.
fn typed(dir: &Path, ty: &str, extra: &[&str]) -> String {
    let mut args = vec!["ticket", "new", "--title", "t", "--type", ty];
    args.extend_from_slice(extra);
    ok(dir, &args)["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned()
}

// frob:ticket 01M1T07NXZ5WQR200M5H1NWDN9
// frob:tests crates/frob-evidence/src/done.rs::DoneGuard.check
#[test]
fn story_bug_and_security_without_criteria_are_refused_on_that_close_naming_the_type() {
    let dir = repo(&["criteria_evidenced"]);
    for ty in ["story", "bug", "security"] {
        let id = typed(dir.path(), ty, &[]);
        // The evidence guard runs first, so clear it with the audited bypass to reach the criteria check.
        let out = close(dir.path(), &id, &["--no-evidence", "--reason", "x"]);
        assert_eq!(code(&out), 3, "{ty}");
        assert_eq!(json(&out)["error"]["code"], "E-DONE-NO-CRITERIA", "{ty}");
        assert!(
            refusal_text(&out).contains(&format!("a {ty} ticket")),
            "{ty}"
        );
        let shown = ok(dir.path(), &["ticket", "show", &id]);
        assert_ne!(shown["data"]["summary"]["category"], "done", "{ty}");
    }
}

// frob:ticket 01M1T07NXZ5WQR200M5H1NWDN9
// frob:tests crates/frob-evidence/src/done.rs::criteria_required
#[test]
fn exempt_types_and_tickets_with_criteria_still_close() {
    let dir = repo(&["criteria_evidenced"]);
    for ty in ["chore", "docs", "epic"] {
        let id = typed(dir.path(), ty, &[]);
        let closed = ok(dir.path(), &["ticket", "close", &id, "--outcome", "done"]);
        assert_eq!(closed["data"]["category"], "done", "{ty}");
    }
    let id = typed(dir.path(), "story", &["--acceptance", "it works"]);
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
            "1",
        ],
    );
    let closed = ok(dir.path(), &["ticket", "close", &id, "--outcome", "done"]);
    assert_eq!(closed["data"]["category"], "done");
}

// frob:ticket 01M4FDQFHJKT30DHZEEA6GWB4R
// frob:tests crates/frob/src/ticket/write.rs::Closeout
#[test]
fn closeout_needs_bound_evidence_and_a_reason_then_closes_done_without_a_lease() {
    let dir = repo(&["criteria_evidenced"]);
    let id = chore(dir.path(), &["--acceptance", "the widget works"]);
    let no_reason = frob(dir.path(), &["ticket", "closeout", &id]);
    assert_eq!(code(&no_reason), 2, "{}", refusal_text(&no_reason));
    let unbound = frob(
        dir.path(),
        &["ticket", "closeout", &id, "--reason", "shipped"],
    );
    assert_eq!(code(&unbound), 3);
    assert_eq!(json(&unbound)["error"]["code"], "E-DONE-CRITERIA-UNBOUND");
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
            "1",
        ],
    );
    let closed = ok(
        dir.path(),
        &["ticket", "closeout", &id, "--reason", "shipped last cycle"],
    );
    assert_eq!(closed["data"]["category"], "done");
    assert_eq!(closed["data"]["outcome"], "done");
    let shown = ok(dir.path(), &["ticket", "show", &id, "--events"]);
    let reasons: Vec<String> = shown["data"]["events"]
        .as_array()
        .expect("events")
        .iter()
        .filter(|e| e["kind"] == "transition")
        .filter_map(|e| e["body"]["reason"].as_str().map(str::to_owned))
        .collect();
    assert!(
        reasons
            .iter()
            .any(|r| r == "retroactive closeout: shipped last cycle"),
        "{reasons:?}"
    );
}
