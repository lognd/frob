//! `git_common_dir` and `canonical` live in gob-fs, below gob-exec and gob-cache.

// frob:ticket 01M4M52WKHGXADHPQ08J1AS8BJ

use gob_fs::{canonical, git_common_dir};

// frob:tests crates/gob-fs/src/gitdir.rs::git_common_dir
#[test]
fn a_linked_worktree_and_its_primary_share_one_common_dir_and_a_plain_dir_has_none() {
    let dir = tempfile::tempdir().unwrap();
    let primary = dir.path().join("primary");
    let private = primary.join(".git/worktrees/wt");
    std::fs::create_dir_all(&private).unwrap();
    std::fs::write(private.join("commondir"), "../..\n").unwrap();
    let linked = dir.path().join("linked");
    std::fs::create_dir_all(&linked).unwrap();
    std::fs::write(
        linked.join(".git"),
        format!("gitdir: {}\n", gob_path::Shown::with_home(&private, None)),
    )
    .unwrap();
    let want = canonical(&primary.join(".git")).unwrap();
    assert_eq!(git_common_dir(&primary), Some(want.clone()));
    assert_eq!(git_common_dir(&linked), Some(want));
    let plain = dir.path().join("plain");
    std::fs::create_dir_all(&plain).unwrap();
    assert_eq!(git_common_dir(&plain), None);
}
