//! PROC001 is a repository-local policy: inert unless `[check] process_spawners` lists crates.

use std::path::Path;

use frob_check::{CheckOptions, run};

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

fn proc001_files(root: &Path) -> Vec<String> {
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        only: vec!["PROC001".to_owned()],
        ..CheckOptions::default()
    };
    let report = run(root, &opts).expect("run");
    report
        .findings
        .iter()
        .filter(|f| f.rule.to_string() == "PROC001")
        .filter_map(|f| f.span.and_then(|s| report.files.path(s.file)))
        .map(str::to_owned)
        .collect()
}

/// A workspace whose `other` crate uses both a spawn and an exit code.
fn tree(root: &Path, config: &str) {
    write(root, "frob.toml", config);
    write(
        root,
        "crates/other/src/lib.rs",
        "//! Other.\nuse std::process::ExitCode;\nuse std::process::Command;\n",
    );
    write(
        root,
        "crates/exit/src/lib.rs",
        "//! Exit.\nuse std::process::ExitCode;\n",
    );
    write(
        root,
        "crates/gob-exec/src/lib.rs",
        "//! Exec.\nuse std::process::Command;\n",
    );
}

// frob:tests crates/gob-check/src/repo.rs::proc001
#[test]
fn consumer_repository_without_a_declared_policy_sees_no_proc001() {
    let dir = tempfile::tempdir().expect("tempdir");
    tree(dir.path(), "");
    assert!(proc001_files(dir.path()).is_empty());
}

// frob:tests crates/gob-check/src/repo.rs::proc001
#[test]
fn declared_spawners_enforce_command_but_not_exit_code() {
    let dir = tempfile::tempdir().expect("tempdir");
    tree(
        dir.path(),
        "[check]\nprocess_spawners = [\"gob-exec\", \"gob-git\"]\n",
    );
    assert_eq!(
        proc001_files(dir.path()),
        vec!["crates/other/src/lib.rs".to_owned()]
    );
}

// frob:tests crates/gob-check/src/repo.rs::proc001
#[test]
fn this_repositorys_own_config_enforces_command_and_spares_exit_code() {
    let own = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../frob.toml");
    let config = std::fs::read_to_string(own).expect("frob.toml");
    let dir = tempfile::tempdir().expect("tempdir");
    tree(dir.path(), &config);
    assert_eq!(
        proc001_files(dir.path()),
        vec!["crates/other/src/lib.rs".to_owned()]
    );
}
