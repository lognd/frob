//! A warm run over an unchanged repository re-extracts and rescans nothing.

// frob:ticket 01M41ZSWGC86TY3K0NSA8AMNGF

use std::path::Path;

use frob_check::{CheckOptions, run};

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn quiet() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

/// A tree with code, a test carrying a directive, markdown, and files no adapter claims.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "src/lib.rs",
        "//! Fixture.\n\n/// Adds one.\npub fn add(x: u32) -> u32 {\n    x + 1\n}\n",
    );
    write(
        dir.path(),
        "tests/add.rs",
        "// frob:tests src/lib.rs::add\n#[test]\nfn adds() {}\n",
    );
    write(
        dir.path(),
        "README.md",
        "# Fixture\n\nSee [code](src/lib.rs).\n",
    );
    write(dir.path(), "data/blob.dat", "opaque bytes\n");
    write(dir.path(), "data/other.dat", "more opaque bytes\n");
    dir
}

// frob:tests crates/frob-check/src/snapshot.rs::collect
#[test]
fn second_run_on_an_unchanged_repository_extracts_and_scans_zero_files() {
    let dir = fixture();
    let first = run(dir.path(), &quiet()).expect("first run");
    assert!(first.stats.graph_extracted > 0, "cold run extracts");
    assert!(first.stats.directives_scanned > 0, "cold run scans");
    assert_eq!(first.stats.graph_cached, 0);
    assert_eq!(first.stats.directives_cached, 0);

    let second = run(dir.path(), &quiet()).expect("second run");
    assert_eq!(second.stats.graph_extracted, 0, "graph stage re-extracted");
    assert_eq!(
        second.stats.directives_scanned, 0,
        "directive stage rescanned"
    );
    assert!(second.stats.graph_cached > 0);
    assert!(second.stats.directives_cached > 0);
    assert_eq!(first.findings, second.findings, "warm output equals cold");
}

// frob:tests crates/frob-check/src/snapshot.rs::collect
#[test]
fn editing_one_file_rescans_only_that_file() {
    let dir = fixture();
    run(dir.path(), &quiet()).expect("first run");
    write(
        dir.path(),
        "tests/add.rs",
        "// frob:tests src/lib.rs::add\n#[test]\nfn adds_again() {}\n",
    );
    let second = run(dir.path(), &quiet()).expect("second run");
    assert_eq!(second.stats.graph_extracted, 1);
    assert_eq!(second.stats.directives_scanned, 1);
}
