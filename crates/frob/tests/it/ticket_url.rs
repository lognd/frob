//! `frob ticket url`: the blob URL on the ticket branch and the mirrored issue URL (`navigation.md` section 1).
// frob:ticket 01M3ZX88FHDWF9C082QZR1PXXA

use std::path::Path;

use serde_json::Value;

use crate::common;

/// The ticket branch name, kept apart from the URLs so this source holds no literal branch link.
const BRANCH: &str = "frob-tickets";

fn frob(cwd: &Path, args: &[&str]) -> (Option<i32>, Value) {
    let out = common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob");
    let json = serde_json::from_slice(&out.stdout).expect("stdout is JSON");
    (out.status.code(), json)
}

fn git(cwd: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

/// A ticket-branch repository with epic "Alpha" and its child task "Move me"; returns (dir, epic, task).
fn fixture() -> (tempfile::TempDir, String, String) {
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-qm", "code"]);
    assert_eq!(frob(p, &["ticket", "branch", "init"]).0, Some(0));
    let new = |title: &str, extra: &[&str]| {
        let mut args = vec!["ticket", "new", "--title", title];
        args.extend_from_slice(extra);
        let (code, v) = frob(p, &args);
        assert_eq!(code, Some(0), "{v}");
        v["data"]["id"].as_str().expect("id").to_owned()
    };
    let alpha = new("Alpha", &["--type", "epic"]);
    let task = new("Move me", &["--parent", &alpha]);
    (dir, alpha, task)
}

#[test]
fn url_prints_the_blob_url_of_the_current_path_and_follows_a_move() {
    let (dir, _alpha, task) = fixture();
    let p = dir.path();
    git(
        p,
        &["remote", "add", "origin", "git@github.com:acme/widgets.git"],
    );
    let (code, v) = frob(p, &["ticket", "url", &task]);
    assert_eq!(code, Some(0), "{v}");
    assert_eq!(
        v["data"]["url"],
        format!("https://github.com/acme/widgets/blob/{BRANCH}/alpha/move-me.md")
    );
    assert!(v["data"].get("issue_url").is_none(), "{v}");

    let (_, beta) = {
        let (code, v) = frob(p, &["ticket", "new", "--title", "Beta", "--type", "epic"]);
        assert_eq!(code, Some(0), "{v}");
        (code, v["data"]["id"].as_str().expect("id").to_owned())
    };
    let (code, v) = frob(p, &["ticket", "update", &task, "--parent", &beta]);
    assert_eq!(code, Some(0), "{v}");
    let (_, v) = frob(p, &["ticket", "url", &task]);
    assert_eq!(
        v["data"]["url"],
        format!("https://github.com/acme/widgets/blob/{BRANCH}/beta/move-me.md")
    );
}

#[test]
fn url_adds_the_issue_url_for_a_mirrored_ticket() {
    let (dir, _alpha, task) = fixture();
    let p = dir.path();
    git(
        p,
        &["remote", "add", "origin", "https://github.com/acme/widgets"],
    );
    let repo = gob_git::Repo::discover(p).expect("repo");
    let id: frob_ledger::TicketId = task.parse().expect("ulid");
    repo.commit_paths(
        "refs/heads/frob-tickets",
        &[(
            gob_git::RelPath::new(frob_ledger::mirror_map::shard_path(id)).expect("path"),
            Some(b"issue = 17\n".to_vec()),
        )],
        "mirror: bind issue",
        &gob_git::CommitOptions {
            author: Some(("Test".to_owned(), "test@example.com".to_owned())),
            ..gob_git::CommitOptions::default()
        },
    )
    .expect("commit shard");
    let (code, v) = frob(p, &["ticket", "url", &task]);
    assert_eq!(code, Some(0), "{v}");
    assert_eq!(
        v["data"]["issue_url"],
        "https://github.com/acme/widgets/issues/17"
    );
}

#[test]
fn url_without_an_origin_remote_is_refused_with_a_remedy() {
    let (dir, _alpha, task) = fixture();
    let (code, v) = frob(dir.path(), &["ticket", "url", &task]);
    assert_eq!(code, Some(3), "{v}");
    assert_eq!(v["error"]["code"], "E-TICKET-URL-NO-REMOTE");
}
