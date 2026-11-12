//! The LOG report is served from the report cache on an unchanged tree and never when a walked
//! file or the `[log]` table changed.

// frob:ticket 01M6AW0G2F3JHWZ2YFA4Y7KVMW


use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

/// Write `text` to the repo-relative `rel` under `root`, creating parents.
// frob:accept LOG001 because="test fixture writes a temp source file, not log output"
fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// The sorted LOG001 messages a run over `root` reports.
fn log001(root: &Path) -> Vec<String> {
    let done = run(root, &CheckOptions::default()).expect("run");
    let doc = sibling_document(&done);
    let mut out: Vec<String> = doc["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "LOG001")
        .map(|f| format!("{}:{}", f["file"], f["message"]))
        .collect();
    out.sort();
    out
}

/// A warm rerun repeats the cold findings, and an edit or a `[log]` change invalidates them.
// frob:tests crates/grimble-check/src/product.rs::cached_log_report
// frob:tests crates/grimble-check/src/product.rs::log_kind
#[test]
fn log_report_is_cached_and_invalidated() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "grimble.toml", "[check]\n");
    write(dir.path(), "app.py", "print('x')\n");
    let cold = log001(dir.path());
    assert_eq!(cold.len(), 1, "{cold:?}");
    assert_eq!(log001(dir.path()), cold, "warm run differs from cold");
    // A new offending file is seen, so the cached report is keyed by the tree.
    write(dir.path(), "other.py", "print('y')\n");
    assert_eq!(log001(dir.path()).len(), 2);
    // Exempting the files through `[log]` is seen, so the cached report is keyed by the table.
    write(
        dir.path(),
        "grimble.toml",
        "[check]\n\n[log]\nexempt = [\"*.py\", \"**/*.py\"]\n",
    );
    let after = log001(dir.path());
    assert!(
        after.iter().all(|m| m.starts_with("null:")),
        "an exempted file is still judged: {after:?}"
    );
}
