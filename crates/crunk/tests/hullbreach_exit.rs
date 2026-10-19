//! Phase 1 exit: a hullbreach-shaped project passes the Rust `crunk check`, and the migration
//! page lists every divergence with a reason.

// frob:ticket 01M4CXSH25SNDV9NGGJ1DF39BA

use std::path::{Path, PathBuf};

use gob_cli::run_for_test;

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn migration_page() -> String {
    let path: PathBuf =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/crunk/hullbreach-migration.md");
    std::fs::read_to_string(path).expect("read migration page")
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn the_ci_step_passes_on_a_scaffolded_web_project() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(
        dir.path().join("package.json"),
        "{\"dependencies\":{\"vite\":\"5\"}}\n",
    )
    .expect("package.json");
    let (code, out, err) = crunk(dir.path(), &["init"]);
    assert_eq!(code, 0, "init: {out} {err}");
    let (code, out, err) = crunk(dir.path(), &["check"]);
    assert_eq!(code, 0, "check: {out} {err}");
    let (code, out, err) = crunk(dir.path(), &["tokens", "--check"]);
    assert_eq!(code, 0, "tokens --check: {out} {err}");
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn every_divergence_row_has_a_nonempty_reason() {
    let page = migration_page();
    let mut rows = 0;
    for line in page.lines().filter(|l| l.starts_with("| ")) {
        let cells: Vec<&str> = line.trim_matches('|').split('|').map(str::trim).collect();
        if cells.iter().all(|c| c.chars().all(|ch| ch == '-')) || cells[0] == "Divergence" {
            continue;
        }
        if cells.len() == 3 && cells[2].contains('/') || cells.len() == 3 && cells[2].contains('`')
        {
            rows += 1;
            assert!(cells[1].len() > 10, "row without a reason: {line}");
        }
    }
    assert!(
        rows >= 20,
        "expected the full divergence list, found {rows} rows"
    );
}

// frob:tests crates/crunk/src/lib.rs::cli
#[test]
fn every_known_divergence_module_doc_is_covered_by_the_page() {
    let page = migration_page();
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for (src, needle) in [
        (
            "crates/crunk-ingest/src/lib.rs",
            "crates/crunk-ingest/src/lib.rs",
        ),
        ("crates/crunk-ingest/src/jsx/mod.rs", "jsx/mod.rs"),
        ("crates/crunk-ingest/src/tailwind/mod.rs", "tailwind/mod.rs"),
        (
            "crates/crunk-values/src/lib.rs",
            "crates/crunk-values/src/lib.rs",
        ),
        (
            "crates/crunk-spec/src/lib.rs",
            "crates/crunk-spec/src/lib.rs",
        ),
        ("crates/crunk-rules/src/rules/waive001.rs", "waive001.rs"),
        ("crates/crunk-rules/src/rules/color001.rs", "color001.rs"),
        ("crates/crunk-rules/src/rules/space001.rs", "space001.rs"),
    ] {
        assert!(root.join(src).exists(), "{src} moved");
        assert!(page.contains(needle), "page omits {src}");
    }
}
