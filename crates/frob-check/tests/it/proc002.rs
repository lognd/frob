#![allow(
    clippy::disallowed_methods,
    reason = "a test reads fixtures and outputs, not a walked snapshot"
)]
//! PROC002 is a repository-local policy: inert unless `[check] output_presenters` lists crates.

use std::path::Path;

use frob_check::{CheckOptions, run};

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn proc002_files(root: &Path) -> Vec<String> {
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        only: vec!["PROC002".to_owned()],
        ..CheckOptions::default()
    };
    let report = run(root, &opts).expect("run");
    report
        .findings
        .iter()
        .filter(|f| f.rule.to_string() == "PROC002")
        .filter_map(|f| f.span.and_then(|s| report.files.path(s.file)))
        .map(str::to_owned)
        .collect()
}

/// A workspace whose `other` and `present` crates both print.
fn tree(root: &Path, config: &str) {
    write(root, "frob.toml", config);
    for krate in ["other", "present"] {
        write(
            root,
            &format!("crates/{krate}/src/lib.rs"),
            "//! Crate.\npub fn f() {\n    println!(\"x\");\n}\n",
        );
    }
}

// frob:tests crates/gob-check/src/repo.rs::proc002
#[test]
fn consumer_repository_without_a_declared_policy_sees_no_proc002() {
    let dir = tempfile::tempdir().expect("tempdir");
    tree(dir.path(), "");
    assert!(proc002_files(dir.path()).is_empty());
}

// frob:tests crates/gob-check/src/repo.rs::proc002
#[test]
fn print_outside_the_presenter_crates_fires() {
    let dir = tempfile::tempdir().expect("tempdir");
    tree(dir.path(), "[check]\noutput_presenters = [\"present\"]\n");
    assert_eq!(proc002_files(dir.path()), vec!["crates/other/src/lib.rs"]);
}
