//! `frob ticket migrate --to-branch`: the legacy ledger moves onto the orphan branch with identical folded state.
// frob:ticket 01M3ZX82YQ43A8SWS4F128J4NT

mod common;

use std::path::Path;
use std::process::Output;

use serde_json::Value;

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .arg("--json")
        .args(args)
        .output()
        .expect("run frob")
}

fn ok(cwd: &Path, args: &[&str]) -> Value {
    let out = frob(cwd, args);
    let v: Value = serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "{args:?} not JSON ({e}): {}",
            String::from_utf8_lossy(&out.stdout)
        )
    });
    assert_eq!(out.status.code(), Some(0), "{args:?}: {v}");
    v
}

fn git(cwd: &Path, args: &[&str]) -> String {
    let out = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .output()
        .expect("git");
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

/// A repository with a legacy ledger: an epic, a child, a loose task and a cycle.
fn legacy_repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("code.txt"), "code\n").expect("write");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-qm", "code"]);
    ok(p, &["init"]);
    git(p, &["add", "-A"]);
    git(p, &["commit", "-qm", "init"]);
    let epic = ok(
        p,
        &[
            "ticket",
            "new",
            "--title",
            "Parser Rewrite",
            "--type",
            "epic",
        ],
    );
    let epic_id = epic["data"]["id"].as_str().expect("id").to_owned();
    ok(
        p,
        &[
            "ticket",
            "new",
            "--title",
            "Lex the input",
            "--parent",
            &epic_id,
            "--scope",
            "src/**",
        ],
    );
    ok(p, &["ticket", "new", "--title", "Loose end"]);
    ok(
        p,
        &[
            "cycle",
            "new",
            "--start",
            "2026-10-01",
            "--end",
            "2026-10-08",
            "--goal",
            "g",
            "--capacity",
            "5",
        ],
    );
    dir
}

/// The ticket list with the volatile fields kept: everything the fold produces.
fn listing(p: &Path) -> Value {
    ok(p, &["ticket", "list"])["data"]["tickets"].clone()
}

// frob:tests crates/frob/src/ticket/migrate_cmd.rs::Migrate
#[test]
fn migration_keeps_every_ticket_identical_and_is_repeatable() {
    let dir = legacy_repo();
    let p = dir.path();
    let before = listing(p);
    let code_tip = git(p, &["rev-parse", "HEAD"]);

    let dry = ok(p, &["ticket", "migrate", "--to-branch", "--dry-run"]);
    assert_eq!(dry["data"]["dry_run"], true);
    assert_eq!(dry["data"]["tickets"], 3);
    let paths: Vec<&str> = dry["data"]["mapping"]
        .as_array()
        .expect("mapping")
        .iter()
        .map(|m| m["path"].as_str().expect("path"))
        .collect();
    assert!(paths.contains(&"parser-rewrite/EPIC.md"), "{paths:?}");
    assert!(
        paths.contains(&"parser-rewrite/lex-the-input.md"),
        "{paths:?}"
    );
    assert!(paths.contains(&"_unfiled/loose-end.md"), "{paths:?}");
    assert_eq!(
        git(p, &["branch", "--list", "frob-tickets"]),
        "",
        "dry run writes nothing"
    );

    let done = ok(p, &["ticket", "migrate", "--to-branch"]);
    assert_eq!(done["already"], false);
    assert!(done["data"]["commit"].is_string());
    assert_eq!(done["data"]["drifted"], serde_json::json!([]));
    assert_eq!(
        git(p, &["rev-parse", "HEAD"]),
        code_tip,
        "the code branch is untouched"
    );

    // Switch the config to the orphan ledger: every ticket folds identically.
    let cfg = std::fs::read_to_string(p.join("frob.toml")).expect("frob.toml");
    std::fs::write(
        p.join("frob.toml"),
        cfg.replace("ref_mode = \"trunk\"", "ref_mode = \"orphan\""),
    )
    .expect("write");
    assert_eq!(listing(p), before);
    let doctor = ok(p, &["ticket", "doctor"]);
    assert_eq!(doctor["data"]["issues"], serde_json::json!([]));
    assert_eq!(doctor["data"]["tickets"], 3);
    assert_eq!(doctor["data"]["cycles"], 1);

    let tree = git(p, &["ls-tree", "-r", "--name-only", "frob-tickets"]);
    assert!(tree.contains("_cycles/"), "{tree}");
    assert!(tree.contains(".gitattributes"), "{tree}");
    assert!(!tree.lines().any(|l| l.starts_with("tickets/")), "{tree}");

    // A second run on the migrated ledger refuses (the config now reads the branch layout).
    let again = frob(p, &["ticket", "migrate", "--to-branch"]);
    assert_eq!(again.status.code(), Some(3));
}

// frob:tests crates/frob/src/ticket/migrate_cmd.rs::Migrate
#[test]
fn rerunning_before_the_config_switch_changes_nothing() {
    let dir = legacy_repo();
    let p = dir.path();
    ok(p, &["ticket", "migrate", "--to-branch"]);
    let tip = git(p, &["rev-parse", "frob-tickets"]);
    let again = ok(p, &["ticket", "migrate", "--to-branch"]);
    assert_eq!(again["already"], true);
    assert_eq!(git(p, &["rev-parse", "frob-tickets"]), tip);
}
