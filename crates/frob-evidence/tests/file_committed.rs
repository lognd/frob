//! `evidence add --provider file` accepts only a regular file tracked and unmodified at HEAD (~AH1CKJF).

// frob:ticket 01M4HW9GZT9T70NGGAHAH1CKJF

use std::path::Path;
use std::time::Duration;

use frob_evidence::Workspace;
use frob_evidence::provider::require_committed;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};

fn git(dir: &Path, args: &[&str]) {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}",
        out.stderr
    );
}

fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
    git(p, &["config", "user.name", "Test User"]);
    git(p, &["config", "user.email", "test@example.com"]);
    git(p, &["config", "core.autocrlf", "false"]);
    std::fs::write(p.join(".gitignore"), "ignored.json\n").expect("ignore");
    std::fs::write(p.join("tracked.json"), "{}\n").expect("tracked");
    std::fs::write(p.join("with space.json"), "{}\n").expect("spaced");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-q", "-m", "base"]);
    dir
}

fn ws(dir: &Path) -> Workspace {
    Workspace::open(dir, std::sync::Arc::new(gob_time::SystemClock)).expect("workspace")
}

fn refusal(w: &Workspace, path: &str) -> String {
    let e = require_committed(w, path).expect_err("refused");
    assert!(
        matches!(e, frob_evidence::EvidenceError::FileNotCommitted { .. }),
        "{e}"
    );
    e.to_string()
}

#[test]
fn a_tracked_unmodified_file_is_accepted_including_a_spaced_name() {
    // frob:tests crates/frob-evidence/src/provider.rs::require_committed
    let dir = repo();
    let w = ws(dir.path());
    require_committed(&w, "tracked.json").expect("tracked");
    require_committed(&w, "./tracked.json").expect("dot-relative");
    require_committed(&w, "with space.json").expect("spaces");
}

#[test]
fn a_gitignored_untracked_or_staged_file_is_refused_with_a_remedy() {
    // frob:tests crates/frob-evidence/src/provider.rs::require_committed
    // frob:tests crates/frob-evidence/src/error.rs::EvidenceError.into_cli
    let dir = repo();
    let p = dir.path();
    std::fs::write(p.join("ignored.json"), "{}").expect("w");
    std::fs::write(p.join("untracked.json"), "{}").expect("w");
    std::fs::write(p.join("staged.json"), "{}").expect("w");
    git(p, &["add", "staged.json"]);
    let w = ws(p);
    for name in ["ignored.json", "untracked.json", "staged.json"] {
        let msg = refusal(&w, name);
        assert!(
            msg.contains("E-EVIDENCE-FILE-UNCOMMITTED") && msg.contains("not tracked"),
            "{msg}"
        );
    }
    let e = require_committed(&w, "ignored.json").expect_err("refused");
    let out = format!("{:?}", e.into_cli());
    assert!(out.contains("E-EVIDENCE-FILE-UNCOMMITTED"), "{out}");
    assert!(out.contains("command evidence"), "{out}");
}

#[test]
fn a_modified_symlinked_escaping_or_unborn_reference_is_refused() {
    // frob:tests crates/frob-evidence/src/provider.rs::require_committed
    let dir = repo();
    let p = dir.path();
    std::fs::write(p.join("tracked.json"), "{\"x\":1}").expect("modify");
    #[cfg(unix)]
    std::os::unix::fs::symlink(p.join("with space.json"), p.join("link.json")).expect("link");
    let w = ws(p);
    assert!(refusal(&w, "tracked.json").contains("modified"));
    #[cfg(unix)]
    assert!(refusal(&w, "link.json").contains("symlink"));
    assert!(refusal(&w, "../outside.json").contains("inside the repository"));
    assert!(refusal(&w, "/etc/hostname").contains("inside the repository"));

    let fresh = tempfile::tempdir().expect("tempdir");
    git(fresh.path(), &["init", "-q"]);
    std::fs::write(fresh.path().join("a.json"), "{}").expect("w");
    assert!(refusal(&ws(fresh.path()), "a.json").contains("no commit"));
}

#[test]
fn outside_a_git_repository_there_is_no_workspace_to_check_against() {
    // frob:tests crates/frob-evidence/src/workspace.rs::Workspace.open
    let dir = tempfile::tempdir().expect("tempdir");
    let opened = Workspace::open(dir.path(), std::sync::Arc::new(gob_time::SystemClock));
    assert!(matches!(
        opened,
        Err(frob_evidence::EvidenceError::NotARepo(_))
    ));
}
