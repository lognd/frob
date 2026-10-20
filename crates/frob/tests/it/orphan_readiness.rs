//! `ref_mode = "orphan"` readiness: check and the generators never look for `tickets/` in the work tree (DT04 audit).
// frob:ticket 01M5D1GP019PAH0KZPFNH0VAHZ

use std::path::Path;
use std::process::Output;

use serde_json::Value;

use crate::common;

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .env_remove("FROB_LOG")
        .args(args)
        .output()
        .expect("run frob")
}

fn json(cwd: &Path, args: &[&str]) -> Value {
    let out = frob(cwd, args);
    serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "{args:?}: {e}: {}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        )
    })
}

fn git(cwd: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

/// An orphan-mode repository (no `tickets/` in the work tree) with one ticket on the ledger branch.
fn orphan_repo() -> tempfile::TempDir {
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    std::fs::create_dir_all(p.join("src")).expect("src");
    std::fs::write(p.join("src/lib.rs"), "/// A.\npub fn a() {}\n").expect("lib");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-qm", "code"]);
    json(p, &["ticket", "branch", "init"]);
    json(p, &["ticket", "new", "--title", "Do the thing"]);
    assert!(
        !p.join("tickets").exists(),
        "orphan mode keeps tickets/ off the tree"
    );
    dir
}

// frob:tests crates/frob-check/src/product.rs::is_frob_owned
#[test]
fn check_in_orphan_mode_reports_no_missing_tickets_path() {
    let dir = orphan_repo();
    let p = dir.path();
    let data = json(p, &["check", "--json", "--fail-on", "none"]);
    let findings = data["data"]["findings"].as_array().expect("findings");
    let bad: Vec<_> = findings
        .iter()
        .filter(|f| {
            let text = format!("{} {}", f["file"].as_str().unwrap_or(""), f["message"]);
            text.contains("tickets/") || f["rule"].as_str().is_some_and(|r| r.starts_with("TICK"))
        })
        .collect();
    assert!(
        bad.is_empty(),
        "ledger-path findings in orphan mode: {bad:?}"
    );
}

// frob:tests crates/frob/src/ticket/reindex_cmd.rs::Reindex
#[test]
fn generators_in_orphan_mode_write_to_the_branch_and_never_need_a_tickets_dir() {
    let dir = orphan_repo();
    let p = dir.path();
    let out = frob(p, &["ticket", "reindex"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    );
    let check = frob(p, &["ticket", "reindex", "--check"]);
    assert_eq!(
        check.status.code(),
        Some(0),
        "branch is current after reindex"
    );
    assert!(
        !p.join("tickets").exists(),
        "generation left the work tree alone"
    );
}
