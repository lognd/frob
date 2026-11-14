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
        writeln!(out, "x{i} = alpha + beta * gamma - delta + {i};").ok();
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
}

// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn config_knobs_reach_the_dup001_pass_part_2() {
    let zero = "[grimble]\ndup_min_tokens = 0\n";
    assert_eq!(dup_count(&repo(3, zero)), 0);
    // Fewer than two occurrences is no clone at all, and an absurd count is just never met.
    assert_eq!(
        dup_count(&repo(3, "[grimble]\ndup_min_occurrences = 1\n")),
        0
    );
}

// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn config_knobs_reach_the_dup001_pass_part_3() {
    let huge = "[grimble]\ndup_min_occurrences = 9223372036854775807\n";
    assert_eq!(dup_count(&repo(3, huge)), 0);
}

// frob:tests crates/grimble-check/src/lib.rs::run
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn config_knobs_reach_the_dup001_pass_part_4() {
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

/// A TypeScript function named `name` with four statements in the given order.
fn shaped_fn(name: &str, order: [usize; 4]) -> String {
    let stmts = [
        "const v1 = a + b * c - a;",
        "const v2 = v1 * b + c - a;",
        "const v3 = v2 * v1 + b - c;",
        "const v4 = v3 + v2 * v1 - a + b;",
    ];
    let body: Vec<_> = order.iter().map(|&i| format!("  {}", stmts[i])).collect();
    format!(
        "export function {name}(a: number, b: number, c: number) {{\n{}\n  return v4 * 2;\n}}\n",
        body.join("\n")
    )
}

/// How many DUP005 findings a run over a reordered pair reports, given the `grimble.toml` text.
fn scan_count(config: &str) -> usize {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "src/a.ts", &shaped_fn("first", [0, 1, 2, 3]));
    write(dir.path(), "src/b.ts", &shaped_fn("second", [3, 2, 1, 0]));
    write(dir.path(), "grimble.toml", config);
    let done = run(dir.path(), &CheckOptions::default()).expect("run");
    done.report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DUP005")
        .count()
}

/// The `dup_scan` knob turns the whole-repo structural scan on; off it finds nothing and is not applicable.
// frob:ticket 01M4P0SXJRVQ0ADAAH3FMYPAR6
// frob:tests crates/grimble-check/src/config.rs::GrimbleTable.scan_enabled
// frob:tests crates/grimble-check/src/lib.rs::run
#[test]
fn dup_scan_knob_reaches_the_dup005_pass() {
    let on = "[grimble]\ndup_scan = true\ndup_min_tokens = 20\n";
    assert_eq!(scan_count(on), 1);
    assert_eq!(scan_count("[grimble]\ndup_min_tokens = 20\n"), 0);
}

/// DUP005 findings of one scan run, as (live fingerprints, baseline-muted count).
fn scan_run(dir: &Path) -> (Vec<String>, usize) {
    let done = run(dir, &CheckOptions::default()).expect("run");
    let live: Vec<String> = done
        .report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DUP005")
        .map(|f| f.fingerprint.to_hex())
        .collect();
    let muted = done
        .report
        .suppressed
        .iter()
        .filter(|(f, _)| f.rule.as_str() == "DUP005")
        .count();
    (live, muted)
}

/// A baseline of the DUP005 keys adopted today mutes them, and a cluster added later still fails (the ratchet).
// frob:ticket 01M4P0SXJRVQ0ADAAH3FMYPAR6
// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn dup005_baseline_mutes_existing_clusters_and_only_new_ones_fail() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "src/a.ts", &shaped_fn("first", [0, 1, 2, 3]));
    write(dir.path(), "src/b.ts", &shaped_fn("second", [3, 2, 1, 0]));
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\ndup_scan = true\ndup_min_tokens = 20\n",
    );
    let (keys, _) = scan_run(dir.path());
    assert_eq!(keys.len(), 1);
    let list = keys.iter().map(|k| format!("\"{k}\"")).collect::<Vec<_>>();
    let baseline = format!(
        "version = 1\n\n[rules.DUP005]\nreason = \"legacy\"\nticket = \"~FMYPAR6\"\nfindings = [{}]\n",
        list.join(", ")
    );
    write(dir.path(), "frob-baseline.toml", &baseline);
    assert_eq!(scan_run(dir.path()), (Vec::new(), 1));

    // A second, differently shaped pair is a new cluster: it is not in the file and fails.
    let other = |name, order| shaped_fn(name, order).replace("v4 * 2", "v4 - 2");
    write(dir.path(), "src/c.ts", &other("third", [0, 1, 2, 3]));
    write(dir.path(), "src/d.ts", &other("fourth", [3, 2, 1, 0]));
    let (live, muted) = scan_run(dir.path());
    assert_eq!((live.len(), muted), (1, 1));
    assert!(!keys.contains(&live[0]));
}
