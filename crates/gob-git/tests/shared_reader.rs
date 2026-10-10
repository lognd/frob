//! One repository per worktree source: readers on many threads share it and still normalize content.

// frob:ticket 01M4D6NJCEYBXJKANS5BY7YNSY

use gob_git::{Repo, WorktreeSource};

#[test]
// frob:tests crates/gob-git/src/content.rs::WorktreeSource.with_reader
// frob:tests crates/gob-git/src/content.rs::WorktreeSource.is_open
fn readers_across_threads_share_one_opened_repository() {
    let dir = tempfile::tempdir().expect("tempdir");
    Repo::init(dir.path()).expect("git init");
    let cfg = dir.path().join(".git/config");
    let mut text = std::fs::read_to_string(&cfg).expect("config");
    text.push_str("[core]\n\tautocrlf = true\n");
    std::fs::write(cfg, text).expect("write config");
    std::fs::write(dir.path().join("a.txt"), "x\r\ny\r\n").expect("write");

    let source = WorktreeSource::locate(dir.path()).expect("inside a checkout");
    assert!(!source.is_open(), "nothing opened before the first read");
    std::thread::scope(|s| {
        for _ in 0..4 {
            let source = source.clone();
            s.spawn(move || {
                source.with_reader(|r| {
                    assert_eq!(r.read("a.txt").expect("read"), Some(b"x\ny\n".to_vec()));
                });
            });
        }
    });
    assert!(source.is_open(), "clones share the opened repository");
}
