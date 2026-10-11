//! `TICK009`: every ticket file on the branch tip sits at its computed path.
// frob:ticket 01M3ZX86ZX0SCN2FHTDBQF97FD

use std::path::Path;

use serde_json::Value;

mod common;

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
    let index = p.join(".git/misfiled-index");
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
        &[
            "commit-tree",
            &tree,
            "-p",
            "frob-tickets",
            "-m",
            "tickets(hand): rename",
        ],
    );
    git(p, None, &["update-ref", "refs/heads/frob-tickets", &commit]);
}

fn tick009(p: &Path) -> Vec<Value> {
    json(p, &["check", "--json", "--fail-on", "none"])["data"]["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "TICK009")
        .cloned()
        .collect()
}

#[test]
fn a_ticket_file_at_a_stale_path_fires_tick009_and_names_the_reindex_fix() {
    let dir = fixture();
    let p = dir.path();
    rename_commit(p, "_unfiled/parser-rewrite.md", "_unfiled/stale.md");
    let found = tick009(p);
    assert_eq!(found.len(), 1, "{found:?}");
    let msg = found[0]["message"].as_str().unwrap_or_default();
    assert!(msg.contains("_unfiled/stale.md"), "{msg}");
    assert!(msg.contains("`frob ticket reindex`"), "{msg}");

    json(p, &["ticket", "reindex"]);
    assert!(tick009(p).is_empty(), "reindex clears the finding");
}

#[test]
fn files_at_their_computed_paths_do_not_fire() {
    let dir = fixture();
    let p = dir.path();
    assert!(tick009(p).is_empty());
    let epic = json(p, &["ticket", "new", "--title", "Beta", "--type", "epic"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    let task = json(p, &["ticket", "new", "--title", "Move me"])["data"]["id"]
        .as_str()
        .expect("id")
        .to_owned();
    json(p, &["ticket", "update", &task, "--parent", &epic]);
    assert!(tick009(p).is_empty());
}
