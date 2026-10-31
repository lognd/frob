//! `crunk check` reads `frob-baseline.toml`: a baselined COLOR001 Error is muted, an unlisted key is not.

// frob:ticket 01M5XMJJHNP9GEX18NSBZF44PC

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A repository holding the default preset and one off-palette color.
fn repo() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "crunk.toml",
        crunk_spec::presets::preset("default").expect("default preset"),
    );
    write(dir.path(), "styles/a.css", ".a { color: #1b1b1b; }\n");
    dir
}

/// Baseline text listing `keys` under COLOR001.
fn baseline_text(keys: &[String]) -> String {
    let list = keys
        .iter()
        .map(|k| format!("\"{k}\""))
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "version = 1\n\n[rules.COLOR001]\nreason = \"legacy\"\nticket = \"~ZX7DH32\"\nfindings = [{list}]\n"
    )
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn a_baselined_finding_is_muted_and_reported_suppressed() {
    let dir = repo();
    let first = run(dir.path(), &CheckOptions::default()).expect("run");
    let keys: Vec<String> = first
        .report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "COLOR001")
        .map(|f| f.fingerprint.to_hex())
        .collect();
    assert!(!keys.is_empty(), "fixture must fire COLOR001");
    write(dir.path(), "frob-baseline.toml", &baseline_text(&keys));
    let second = run(dir.path(), &CheckOptions::default()).expect("run");
    assert!(
        second
            .report
            .findings
            .iter()
            .all(|f| f.rule.as_str() != "COLOR001")
    );
    assert_eq!(
        second
            .report
            .suppressed
            .iter()
            .filter(|(f, _)| f.rule.as_str() == "COLOR001")
            .count(),
        keys.len()
    );
}

// frob:tests crates/crunk-check/src/product.rs::Crunk
#[test]
fn an_unlisted_key_does_not_mute() {
    let dir = repo();
    write(
        dir.path(),
        "frob-baseline.toml",
        &baseline_text(&["0".repeat(64)]),
    );
    let r = run(dir.path(), &CheckOptions::default()).expect("run");
    assert!(
        r.report
            .findings
            .iter()
            .any(|f| f.rule.as_str() == "COLOR001")
    );
}
