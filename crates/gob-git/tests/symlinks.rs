//! `diff_names(merge_base, WorkTree)` must agree with `git status` on symlinks and line endings.
#![cfg(unix)]

use std::path::Path;
use std::process::Command;

use gob_git::{ChangeKind, ChangedPath, Repo, TreeRef};

fn git(dir: &Path, args: &[&str]) {
    let out = Command::new("git")
        .current_dir(dir)
        .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
        .args(args)
        .output()
        .expect("git runs");
    assert!(
        out.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
}

fn write(dir: &Path, rel: &str, body: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, body).unwrap();
}

fn link(dir: &Path, rel: &str, target: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    let _ = std::fs::remove_file(&p);
    std::os::unix::fs::symlink(target, p).unwrap();
}

/// A repo shaped like the cloc report: file and directory symlinks (relative and absolute), a CRLF text file.
fn fixture(autocrlf: bool) -> (tempfile::TempDir, std::path::PathBuf) {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path().to_path_buf();
    git(&dir, &["init", "-q", "-b", "main"]);
    git(
        &dir,
        &[
            "config",
            "core.autocrlf",
            if autocrlf { "true" } else { "false" },
        ],
    );
    write(&dir, "280/L/hello_1.c", "int main(void) { return 0; }\n");
    write(&dir, "notes.txt", "one\ntwo\n");
    link(&dir, "513/L/hello_1.c", "../../280/L/hello_1.c");
    link(&dir, "513/D", "../280/L");
    let abs = dir.join("280/L/hello_1.c");
    link(&dir, "abs_link.c", abs.to_str().unwrap());
    link(&dir, "dangling", "nowhere/at/all");
    git(&dir, &["add", "-A"]);
    git(&dir, &["commit", "-q", "-m", "base"]);
    git(&dir, &["checkout", "-q", "-b", "ticket"]);
    write(&dir, "unrelated.txt", "x\n");
    git(&dir, &["add", "-A"]);
    git(&dir, &["commit", "-q", "-m", "unrelated"]);
    (tmp, dir)
}

fn changes(dir: &Path) -> Vec<ChangedPath> {
    let repo = Repo::discover(dir).unwrap();
    let mb = repo.merge_base("main", "HEAD").unwrap().unwrap();
    repo.diff_names(&TreeRef::Oid(mb), &TreeRef::WorkTree)
        .unwrap()
}

fn paths(c: &[ChangedPath]) -> Vec<&str> {
    c.iter().map(|c| c.path.as_str()).collect()
}

#[test]
fn untouched_symlinks_are_not_reported() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    for autocrlf in [false, true] {
        let (_t, dir) = fixture(autocrlf);
        let got = changes(&dir);
        assert_eq!(
            paths(&got),
            ["unrelated.txt"],
            "autocrlf={autocrlf}: {got:?}"
        );
    }
}

#[test]
fn crlf_checkout_without_content_change_is_not_reported() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dir) = fixture(true);
    // Let git itself rewrite the file with CRLF (blob stays LF), as a WSL checkout does.
    std::fs::remove_file(dir.join("notes.txt")).unwrap();
    git(&dir, &["checkout", "--", "notes.txt"]);
    let on_disk = std::fs::read(dir.join("notes.txt")).unwrap();
    assert_eq!(on_disk, b"one\r\ntwo\r\n", "checkout applied autocrlf");
    let got = changes(&dir);
    assert_eq!(paths(&got), ["unrelated.txt"], "{got:?}");
}

#[test]
fn retargeted_symlink_is_reported_committed_and_uncommitted() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dir) = fixture(true);
    link(&dir, "513/L/hello_1.c", "../../notes.txt");
    let got = changes(&dir);
    assert_eq!(
        got,
        [
            ChangedPath {
                path: "513/L/hello_1.c".into(),
                kind: ChangeKind::Modified
            },
            ChangedPath {
                path: "unrelated.txt".into(),
                kind: ChangeKind::Added
            },
        ]
    );
    git(&dir, &["add", "-A"]);
    git(&dir, &["commit", "-q", "-m", "retarget"]);
    assert_eq!(paths(&changes(&dir)), ["513/L/hello_1.c", "unrelated.txt"]);
}

#[test]
fn symlink_replaced_by_regular_file_with_target_text_is_reported() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dir) = fixture(false);
    std::fs::remove_file(dir.join("513/L/hello_1.c")).unwrap();
    write(&dir, "513/L/hello_1.c", "../../280/L/hello_1.c");
    let got = changes(&dir);
    assert!(paths(&got).contains(&"513/L/hello_1.c"), "{got:?}");
}

#[test]
fn worktree_content_as_git_matches_what_git_would_store() {
    // frob:tests crates/gob-git/src/content.rs::Repo.worktree_content_as_git
    let (_t, dir) = fixture(true);
    std::fs::remove_file(dir.join("notes.txt")).unwrap();
    git(&dir, &["checkout", "--", "notes.txt"]);
    let repo = Repo::discover(&dir).unwrap();
    let get = |p: &str| repo.worktree_content_as_git(p).unwrap();
    assert_eq!(get("notes.txt").unwrap(), b"one\ntwo\n");
    assert_eq!(get("513/L/hello_1.c").unwrap(), b"../../280/L/hello_1.c");
    assert_eq!(get("513/D").unwrap(), b"../280/L");
    assert_eq!(get("dangling").unwrap(), b"nowhere/at/all");
    assert_eq!(get("missing.txt"), None);
}
