//! `grimble check` reads `frob-baseline.toml`: a baselined Error is muted, an unlisted one still fails.

// frob:ticket 01M5XMJJHNP9GEX18NSBZF44PC

use std::path::Path;

use grimble_check::{CheckOptions, run};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// A repo whose one source file fires PATH001.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    write(dir.path(), "grimble.toml", "[check]\n");
    write(
        dir.path(),
        "src/lib.rs",
        "fn f() -> &'static str {\n    \"/home/ann/data.txt\"\n}\n",
    );
    dir
}

/// Baseline text listing `keys` under PATH001.
fn baseline_text(keys: &[String]) -> String {
    let list = keys
        .iter()
        .map(|k| format!("\"{k}\""))
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "version = 1\n\n[rules.PATH001]\nreason = \"legacy\"\nticket = \"~ZX7DH32\"\nfindings = [{list}]\n"
    )
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_baselined_finding_is_muted_and_reported_suppressed() {
    let dir = repo();
    let first = run(dir.path(), &CheckOptions::default()).unwrap();
    let keys: Vec<String> = first
        .report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "PATH001")
        .map(|f| f.fingerprint.to_hex())
        .collect();
    assert!(!keys.is_empty(), "fixture must fire PATH001");
    write(dir.path(), "frob-baseline.toml", &baseline_text(&keys));
    let second = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(
        second
            .report
            .findings
            .iter()
            .all(|f| f.rule.as_str() != "PATH001"),
        "{:?}",
        second.report.findings
    );
    assert_eq!(
        second
            .report
            .suppressed
            .iter()
            .filter(|(f, _)| f.rule.as_str() == "PATH001")
            .count(),
        keys.len()
    );
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn an_unlisted_key_does_not_mute() {
    let dir = repo();
    write(
        dir.path(),
        "frob-baseline.toml",
        &baseline_text(&["0".repeat(64)]),
    );
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(
        r.report
            .findings
            .iter()
            .any(|f| f.rule.as_str() == "PATH001")
    );
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_conflicted_baseline_is_a_config_error() {
    let dir = repo();
    write(dir.path(), "frob-baseline.toml", "<<<<<<< HEAD\n");
    assert!(run(dir.path(), &CheckOptions::default()).is_err());
}

// frob:tests crates/grimble-check/src/config.rs::GrimbleTable
#[test]
fn the_deprecated_strict_knob_is_still_accepted_and_changes_nothing() {
    let dir = repo();
    let plain = run(dir.path(), &CheckOptions::default()).unwrap();
    write(dir.path(), "grimble.toml", "[grimble]\nstrict = true\n");
    let strict = run(dir.path(), &CheckOptions::default()).unwrap();
    let ids = |r: &grimble_check::GrimbleRun| {
        r.report
            .findings
            .iter()
            .map(|f| (f.rule.as_str().to_owned(), f.severity))
            .collect::<Vec<_>>()
    };
    assert_eq!(ids(&plain), ids(&strict));
}
