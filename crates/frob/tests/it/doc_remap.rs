//! `frob doc remap` through the real verb: a bad row refuses with exit 3 naming the row, a good map rewrites.
// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use crate::common;

use std::path::Path;

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// Stage and commit everything under `root`.
fn commit_all(root: &Path) {
    for args in [&["add", "-A"][..], &["commit", "-q", "-m", "fixture"][..]] {
        let status = std::process::Command::new("git")
            .args(args)
            .current_dir(root)
            .status()
            .expect("git");
        assert!(status.success(), "git {args:?}");
    }
}

/// A committed repo with a new doc, a citing doc and the given map.
fn repo_with(map: &str) -> tempfile::TempDir {
    let dir = common::git_repo();
    write(dir.path(), "frob.toml", "");
    write(dir.path(), "docs/new.md", "# New\n\n## Fresh\n");
    write(dir.path(), "docs/a.md", "# A\n\nSee [x](old.md#gone).\n");
    write(dir.path(), "docs/MOVED.toml", map);
    commit_all(dir.path());
    dir
}

// frob:tests crates/frob/src/doc_cmd.rs::DocRemap
#[test]
fn a_row_whose_target_is_not_a_heading_refuses_with_exit_3_and_names_the_row() {
    let dir = repo_with("[moved]\n\"docs/old.md#gone\" = \"docs/new.md#nowhere\"\n");
    let (code, stdout, stderr) =
        gob_cli::run_for_test(&frob_cli::cli(), &["doc", "remap", "--text"], dir.path());
    assert_eq!(code, 3, "{stdout}{stderr}");
    let all = format!("{stdout}{stderr}");
    assert!(all.contains("docs/old.md#gone"), "{all}");
    let text = std::fs::read_to_string(dir.path().join("docs/a.md")).unwrap();
    assert!(text.contains("old.md#gone"), "nothing written: {text}");
}

// frob:tests crates/frob/src/doc_cmd.rs::DocRemap
#[test]
fn a_good_map_rewrites_links_and_dry_run_writes_nothing() {
    let dir = repo_with("[moved]\n\"docs/old.md#gone\" = \"docs/new.md#fresh\"\n");
    let (code, out, err) =
        gob_cli::run_for_test(&frob_cli::cli(), &["doc", "remap", "--dry-run"], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    let before = std::fs::read_to_string(dir.path().join("docs/a.md")).unwrap();
    assert!(before.contains("old.md#gone"), "{before}");
    let (code, out, err) = gob_cli::run_for_test(&frob_cli::cli(), &["doc", "remap"], dir.path());
    assert_eq!(code, 0, "{out}{err}");
    let after = std::fs::read_to_string(dir.path().join("docs/a.md")).unwrap();
    assert!(
        after.contains("new.md#fresh") && !after.contains("old.md"),
        "{after}"
    );
}
