//! `TICK007`: a reindex commit must equal the pure reindex of its parent tree.
// frob:ticket 01M3ZX86R5V67MT726K3X7KVWM

use std::path::Path;

use serde_json::Value;

use crate::common;

fn json(cwd: &Path, args: &[&str]) -> Value {
    let out = common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob");
    serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "{args:?}: {e}: {}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        )
    })
}

/// Run git with its own identity and an optional alternate index; stdout trimmed.
fn git(cwd: &Path, index: Option<&Path>, args: &[&str]) -> String {
    let mut cmd = std::process::Command::new("git");
    cmd.args(args)
        .current_dir(cwd)
        .env("GIT_AUTHOR_NAME", "T")
        .env("GIT_AUTHOR_EMAIL", "t@example.invalid")
        .env("GIT_COMMITTER_NAME", "T")
        .env("GIT_COMMITTER_EMAIL", "t@example.invalid");
    if let Some(i) = index {
        cmd.env("GIT_INDEX_FILE", i);
    }
    let out = cmd.output().expect("git");
    assert!(out.status.success(), "git {args:?}");
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

/// A ticket-branch repository with one task "Parser rewrite".
fn fixture() -> tempfile::TempDir {
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    git(p, None, &["add", "-A"]);
    git(p, None, &["commit", "-qm", "code"]);
    json(p, &["ticket", "branch", "init"]);
    json(p, &["ticket", "new", "--title", "Parser rewrite"]);
    dir
}

/// Append a line to the task body and commit it on the ticket branch with the given subject and trailer.
fn hand_edited_commit(p: &Path, trailer: &str) {
    let index = p.join(".git/replay-index");
    git(p, Some(&index), &["read-tree", "frob-tickets"]);
    let path = "_unfiled/parser-rewrite.md";
    let mut body = git(p, None, &["show", &format!("frob-tickets:{path}")]);
    body.push_str("\nhand edit\n");
    let src = p.join("replay-body.md");
    std::fs::write(&src, body).expect("write");
    let blob = git(
        p,
        None,
        &[
            "hash-object",
            "-w",
            gob_path::Shown::with_home(&src, None).as_str(),
        ],
    );
    let cache = format!("100644,{blob},{path}");
    git(
        p,
        Some(&index),
        &["update-index", "--add", "--cacheinfo", &cache],
    );
    let tree = git(p, Some(&index), &["write-tree"]);
    let msg = format!("tickets(reindex): after X\n\n{trailer}\n");
    let commit = git(
        p,
        None,
        &["commit-tree", &tree, "-p", "frob-tickets", "-m", &msg],
    );
    git(p, None, &["update-ref", "refs/heads/frob-tickets", &commit]);
}

fn tick007(p: &Path) -> Vec<Value> {
    json(p, &["check", "--json", "--fail-on", "none"])["data"]["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "TICK007")
        .cloned()
        .collect()
}

#[test]
fn a_reindex_commit_with_one_hand_edited_ticket_body_fires_tick007() {
    let dir = fixture();
    let p = dir.path();
    assert!(tick007(p).is_empty(), "no reindex commit, no finding");
    hand_edited_commit(p, &format!("Frob-Reindex: {}", env!("CARGO_PKG_VERSION")));
    let found = tick007(p);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "error");
    assert!(
        found[0]["message"]
            .as_str()
            .unwrap_or_default()
            .contains("_unfiled/parser-rewrite.md"),
        "{found:?}"
    );
}

#[test]
fn a_reindex_trailer_naming_an_unavailable_version_is_unresolved_generator_version() {
    let dir = fixture();
    let p = dir.path();
    hand_edited_commit(p, "Frob-Reindex: 0.0.1");
    let found = tick007(p);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0]["severity"], "unresolved");
    assert!(
        found[0].to_string().contains("generator-version"),
        "{found:?}"
    );
}

#[test]
fn a_genuine_reindex_commit_replays_clean() {
    let dir = fixture();
    let p = dir.path();
    let epic = json(p, &["ticket", "new", "--title", "Beta", "--type", "epic"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let task = json(p, &["ticket", "new", "--title", "Move me"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    json(p, &["ticket", "update", &task, "--parent", &epic]);
    let log = git(p, None, &["log", "-1", "--format=%B", "frob-tickets"]);
    assert!(log.contains("Frob-Reindex: "), "{log}");
    assert!(tick007(p).is_empty());
}
