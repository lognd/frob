//! `crunk check` keeps its telemetry out of the worktree: it goes to the shared cache directory.

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX

use crunk_check::{CheckOptions, run};

/// A git-shaped project with the default preset.
fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::create_dir(dir.path().join(".git")).expect("git dir");
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    std::fs::write(dir.path().join("crunk.toml"), spec).expect("write");
    dir
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn a_crunk_check_leaves_no_state_directory_in_the_worktree() {
    let dir = project();
    run(dir.path(), &CheckOptions::default()).expect("run");
    assert!(
        !dir.path().join(".crunk").exists(),
        "telemetry and cache must not land in the worktree"
    );
    let telemetry = dir.path().join(".git/frob/cache/crunk/telemetry.jsonl");
    let text = std::fs::read_to_string(&telemetry).expect("telemetry in the cache dir");
    assert_eq!(text.lines().count(), 1, "one line per run: {text}");
}
