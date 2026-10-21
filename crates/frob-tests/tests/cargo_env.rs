//! `frob test` hands the caller's cargo build-profile environment to the cargo it spawns (~P8YV3RW).

// frob:ticket 01M4K8HPJ38DWG338WBP8YV3RW

use std::time::Duration;

use frob_tests::{RunOptions, run};
use gob_exec::{Limits, Runner};

mod common;
use common::{git, write};

/// True for the variables that steer cargo's build profile and so the size of the test binaries.
fn is_build_env(name: &str) -> bool {
    name == "CARGO_INCREMENTAL" || name.starts_with("CARGO_PROFILE_")
}

/// A probe test that fails unless its own environment holds exactly the `expected` profile variables.
fn probe_lib(expected: &[(String, String)]) -> String {
    format!(
        "#[test]\nfn sees_build_env() {{\n    let want: Vec<(String, String)> = vec!{expected:?}\
         .into_iter().map(|(k, v): (&str, &str)| (k.to_owned(), v.to_owned())).collect();\n    \
         let mut got: Vec<(String, String)> = std::env::vars()\n        \
         .filter(|(k, _)| k == \"CARGO_INCREMENTAL\" || k.starts_with(\"CARGO_PROFILE_\"))\n        \
         .collect();\n    got.sort();\n    assert_eq!(got, want);\n}}\n",
        expected = expected
            .iter()
            .map(|(k, v)| (k.as_str(), v.as_str()))
            .collect::<Vec<_>>()
    )
}

#[test]
fn the_callers_cargo_profile_env_reaches_the_spawned_cargo() {
    // frob:tests crates/frob-tests/src/run.rs::run
    let mut expected: Vec<(String, String)> =
        std::env::vars().filter(|(k, _)| is_build_env(k)).collect();
    expected.sort();
    let dir = tempfile::tempdir().expect("tempdir");
    let p = dir.path();
    git(p, &["init", "-q"]);
    write(
        p,
        "Cargo.toml",
        "[package]\nname = \"frob_cargo_env_probe\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[workspace]\n",
    );
    write(p, "src/lib.rs", &probe_lib(&expected));
    let opts = RunOptions::new(
        p.to_path_buf(),
        Duration::from_secs(300),
        String::new(),
        Vec::new(),
        true,
    );
    let report = run(&Runner::new(Limits { jobs: 1 }), &[], &opts).expect("run");
    assert!(report.passed(), "{}", frob_tests::failure_cause(&report));
    assert_eq!(report.executed(), ["sees_build_env"]);
}
