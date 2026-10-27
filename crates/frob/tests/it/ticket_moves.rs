//! `TICK008`: only a reindex commit may move a ticket file or touch an existing event file.
// frob:ticket 01M3ZX86W1P62F80ZNR17Q0SQ9

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

/// Commit on the ticket branch a tree where `path` is renamed to `to` (no trailer).
fn rename_commit(p: &Path, path: &str, to: &str) {
    rename_commit_with(p, path, to, "tickets(hand): rename");
}

/// Like `rename_commit` with an explicit commit message.
fn rename_commit_with(p: &Path, path: &str, to: &str, message: &str) {
    let index = p.join(".git/moves-index");
    git(p, Some(&index), &["read-tree", "frob-tickets"]);
    let blob = git(p, None, &["rev-parse", &format!("frob-tickets:{path}")]);
    git(p, Some(&index), &["rm", "--cached", "-q", path]);
    let cache = format!("100644,{blob},{to}");
    git(
        p,
        Some(&index),
        &["update-index", "--add", "--cacheinfo", &cache],
    );
    let tree = git(p, Some(&index), &["write-tree"]);
    let commit = git(
        p,
        None,
        &["commit-tree", &tree, "-p", "frob-tickets", "-m", message],
    );
    git(p, None, &["update-ref", "refs/heads/frob-tickets", &commit]);
}

fn tick008(p: &Path) -> Vec<Value> {
    json(p, &["check", "--json", "--fail-on", "none"])["data"]["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "TICK008")
        .cloned()
        .collect()
}

#[test]
fn a_commit_that_only_adds_events_and_edits_frontmatter_does_not_fire() {
    let dir = fixture();
    let p = dir.path();
    let id = json(p, &["ticket", "new", "--title", "Second"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    json(p, &["ticket", "update", &id, "--priority", "high"]);
    json(p, &["ticket", "comment", &id, "--body", "note"]);
    assert!(tick008(p).is_empty());
}

#[test]
fn a_genuine_reindex_move_does_not_fire() {
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
    assert!(tick008(p).is_empty());
}

#[test]
fn a_commit_without_the_trailer_that_renames_a_ticket_file_fires_tick008() {
    let dir = fixture();
    let p = dir.path();
    rename_commit(p, "_unfiled/parser-rewrite.md", "_unfiled/renamed.md");
    let found = tick008(p);
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

// frob:tests frob_ledger::moves::Ledger::move_outside_reindex_findings
#[test]
fn an_allow_move_trailer_exempts_a_commit() {
    let dir = fixture();
    let p = dir.path();
    rename_commit_with(
        p,
        "_unfiled/parser-rewrite.md",
        "_unfiled/renamed.md",
        "tickets(hand): rename\n\nFrob-Allow-Move: one-off cleanup",
    );
    assert!(tick008(p).is_empty());
}

// frob:tests frob_ledger::moves::Ledger::move_outside_reindex_findings
#[test]
fn a_revert_of_an_earlier_ledger_commit_does_not_fire() {
    let dir = fixture();
    let p = dir.path();
    let original = git(p, None, &["rev-parse", "frob-tickets^{tree}"]);
    rename_commit_with(
        p,
        "_unfiled/parser-rewrite.md",
        "_unfiled/renamed.md",
        "tickets(hand): import\n\nFrob-Allow-Move: import",
    );
    let commit = git(
        p,
        None,
        &[
            "commit-tree",
            &original,
            "-p",
            "frob-tickets",
            "-m",
            "chore(tickets): revert duplicate import",
        ],
    );
    git(p, None, &["update-ref", "refs/heads/frob-tickets", &commit]);
    assert!(tick008(p).is_empty(), "{:?}", tick008(p));
}
