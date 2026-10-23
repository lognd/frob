//! The DUP001 `dup_min_tokens` and `dup_min_occurrences` knobs of `[grimble]` reach the clone pass.

// frob:ticket 01M5HMKRFRZYFQC6HVNPHC3Z2P

use std::fmt::Write as _;
use std::path::Path;

use grimble_check::{CheckOptions, run};

/// Write `text` to the repo-relative `rel` under `root`, creating parents.
fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A block of about sixty tokens, the same for every copy.
fn block() -> String {
    let mut out = String::new();
    for i in 1..=6 {
        let _ = writeln!(out, "x{i} = alpha + beta * gamma - delta + {i};");
    }
    out
}

/// A repo with `copies` files holding the block and `config` as its `grimble.toml`.
fn repo(copies: usize, config: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    for i in 0..copies {
        let body = format!("export function f() {{}}\n{}", block());
        write(dir.path(), &format!("src/f{i}.ts"), &body);
    }
    write(dir.path(), "grimble.toml", config);
    dir
}

/// How many DUP001 findings a run over `dir` reports.
fn dup_count(dir: &tempfile::TempDir) -> usize {
    let done = run(dir.path(), &CheckOptions::default()).expect("run");
    done.report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DUP001")
        .count()
}

/// Lowering `dup_min_occurrences` to 2 makes two copies fire, and the knob reaches the pass.
// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn config_knobs_reach_the_dup001_pass() {
    assert_eq!(
        dup_count(&repo(2, "[grimble]\ndup_min_occurrences = 2\n")),
        1
    );
    // A window longer than any copy, or a zero window, finds nothing even with three copies.
    let long = "[grimble]\ndup_min_tokens = 100000\n";
    assert_eq!(dup_count(&repo(3, long)), 0);
    let zero = "[grimble]\ndup_min_tokens = 0\n";
    assert_eq!(dup_count(&repo(3, zero)), 0);
    // Fewer than two occurrences is no clone at all, and an absurd count is just never met.
    assert_eq!(
        dup_count(&repo(3, "[grimble]\ndup_min_occurrences = 1\n")),
        0
    );
    let huge = "[grimble]\ndup_min_occurrences = 9223372036854775807\n";
    assert_eq!(dup_count(&repo(3, huge)), 0);
    // Changing a knob on the same tree is not served from the report cache.
    let dir = repo(2, "[grimble]\n");
    assert_eq!(dup_count(&dir), 0);
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\ndup_min_occurrences = 2\n",
    );
    assert_eq!(dup_count(&dir), 1);
}

/// Omitting the knobs keeps 50 tokens and 3 occurrences.
// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn omitted_dup_knobs_keep_the_defaults() {
    let table = grimble_check::config::GrimbleTable::load(repo(2, "").path()).expect("load");
    assert_eq!((table.dup_min_tokens, table.dup_min_occurrences), (50, 3));
    assert_eq!(dup_count(&repo(2, "")), 0);
    assert_eq!(dup_count(&repo(3, "")), 1);
    assert_eq!(dup_count(&repo(3, "[grimble]\nlarge_lines = 10\n")), 1);
}

/// A negative or non-integer knob is a config error, not a silent default.
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn invalid_dup_knobs_are_rejected() {
    for bad in ["dup_min_tokens = -1", "dup_min_occurrences = \"three\""] {
        let dir = repo(1, &format!("[grimble]\n{bad}\n"));
        assert!(
            grimble_check::config::GrimbleTable::load(dir.path()).is_err(),
            "{bad} accepted"
        );
    }
}
