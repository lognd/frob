//! `diff_names` against a goway-style shallow overlay `.git` (tips' trees only, no history).
//! frob:ticket 01M49SWMDMB1TEHJ5Q1HRJ3KXT

use std::path::Path;
use std::process::Command;

use gob_git::{Repo, TreeRef};

fn git(dir: &Path, args: &[&str]) -> String {
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
    String::from_utf8_lossy(&out.stdout).trim().to_owned()
}

fn write(dir: &Path, rel: &str, body: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, body).unwrap();
}

/// Which tree objects the overlay leaves out.
#[derive(Clone, Copy)]
enum Omit {
    /// Nothing: every tree is present.
    Nothing,
    /// The `a/b` subtree (as goway drops a tree whose name looks secret).
    Subtree,
    /// The base commit's root tree (a shallow base).
    BaseRoot,
}

/// A work tree several commits ahead of `origin/experimental`, plus its goway-style overlay copy.
fn fixture(omit: Omit) -> (tempfile::TempDir, std::path::PathBuf) {
    let tmp = tempfile::tempdir().unwrap();
    let src = tmp.path().join("src");
    let dst = tmp.path().join("dst");
    std::fs::create_dir_all(&src).unwrap();
    std::fs::create_dir_all(&dst).unwrap();
    git(&src, &["init", "-q", "-b", "experimental"]);
    write(&src, "a/b/c.txt", "one\n");
    write(&src, "top.txt", "t\n");
    git(&src, &["add", "-A"]);
    git(&src, &["commit", "-q", "-m", "base"]);
    let base = git(&src, &["rev-parse", "HEAD"]);
    for i in 0..3 {
        write(&src, &format!("a/new{i}.txt"), "x\n");
        git(&src, &["add", "-A"]);
        git(&src, &["commit", "-q", "-m", &format!("c{i}")]);
    }
    let head = git(&src, &["rev-parse", "HEAD"]);
    // The overlay: objects of each tip only (no parents), the real index, HEAD and two refs.
    let listed = git(
        &src,
        &["rev-list", "--objects", "--no-walk=unsorted", &head, &base],
    );
    let base_root = git(&src, &["rev-parse", &format!("{base}^{{tree}}")]);
    let head_root = git(&src, &["rev-parse", &format!("{head}^{{tree}}")]);
    let oids: Vec<&str> = listed
        .lines()
        .filter(|l| match omit {
            Omit::Nothing => true,
            Omit::Subtree => l.split_once(' ').is_none_or(|(_, p)| p != "a/b"),
            Omit::BaseRoot => {
                let oid = l.split(' ').next().unwrap();
                oid != base_root || oid == head_root
            }
        })
        .map(|l| l.split(' ').next().unwrap())
        .collect();
    let list = tmp.path().join("objects.list");
    std::fs::write(&list, oids.join("\n") + "\n").unwrap();
    let pack = tmp.path().join("p.pack");
    let status = Command::new("git")
        .current_dir(&src)
        .args(["pack-objects", "--stdout", "-q"])
        .stdin(std::fs::File::open(&list).unwrap())
        .stdout(std::fs::File::create(&pack).unwrap())
        .status()
        .unwrap();
    assert!(status.success());
    git(&dst, &["init", "-q", "-b", "experimental"]);
    let out = Command::new("git")
        .current_dir(&dst)
        .args(["index-pack", "--stdin"])
        .stdin(std::fs::File::open(&pack).unwrap())
        .output()
        .unwrap();
    assert!(out.status.success());
    git(&dst, &["update-ref", "refs/heads/experimental", &head]);
    git(
        &dst,
        &["update-ref", "refs/remotes/origin/experimental", &base],
    );
    std::fs::copy(src.join(".git/index"), dst.join(".git/index")).unwrap();
    for rel in [
        "a/b/c.txt",
        "top.txt",
        "a/new0.txt",
        "a/new1.txt",
        "a/new2.txt",
    ] {
        let to = dst.join(rel);
        std::fs::create_dir_all(to.parent().unwrap()).unwrap();
        std::fs::copy(src.join(rel), to).unwrap();
    }
    (tmp, dst)
}

#[test]
fn diff_against_remote_tip_works_on_overlay() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dst) = fixture(Omit::Nothing);
    let repo = Repo::discover(&dst).unwrap();
    let got = repo
        .diff_names(
            &TreeRef::Ref("refs/remotes/origin/experimental".into()),
            &TreeRef::WorkTree,
        )
        .unwrap();
    let paths: Vec<&str> = got.iter().map(|c| c.path.as_str()).collect();
    assert_eq!(paths, ["a/new0.txt", "a/new1.txt", "a/new2.txt"], "{got:?}");
}

#[test]
fn missing_subtree_is_conservative_not_an_error() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dst) = fixture(Omit::Subtree);
    let repo = Repo::discover(&dst).unwrap();
    let got = repo
        .diff_names(
            &TreeRef::Ref("refs/remotes/origin/experimental".into()),
            &TreeRef::WorkTree,
        )
        .unwrap();
    let paths: Vec<&str> = got.iter().map(|c| c.path.as_str()).collect();
    assert_eq!(
        paths,
        ["a/b/c.txt", "a/new0.txt", "a/new1.txt", "a/new2.txt"],
        "{got:?}"
    );
}

#[test]
fn missing_base_tree_is_a_named_error() {
    // frob:tests crates/gob-git/src/status.rs::Repo.diff_names
    let (_t, dst) = fixture(Omit::BaseRoot);
    let repo = Repo::discover(&dst).unwrap();
    let err = repo
        .diff_names(
            &TreeRef::Ref("refs/remotes/origin/experimental".into()),
            &TreeRef::WorkTree,
        )
        .unwrap_err();
    assert_eq!(err.code(), "E-GIT-SHALLOW-BASE", "{err}");
}
