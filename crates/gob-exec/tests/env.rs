//! A scrubbed child sees only the allowlisted and the explicitly added variables, and a
//! secret-looking variable in the parent never reaches it.

// frob:ticket 01M40VH6HES1X3P57WZS0S9G93

#![cfg(unix)]

use std::collections::BTreeMap;
use std::time::Duration;

use gob_exec::{EnvPolicy, Limits, Outcome, Program, Runner, Spec};

const PROBE_MARK: &str = "GOB_EXEC_ENV_PROBE";

/// Run `env` under `policy` with `added` per-spawn variables and return what it printed.
fn child_env(policy: &EnvPolicy, added: &[(&str, &str)]) -> BTreeMap<String, String> {
    let spec = Spec {
        program: Program::Tool { name: "env".into() },
        args: vec![],
        cwd: None,
        env: added
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect(),
        timeout: Duration::from_secs(10),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run_with_env(&spec, policy)
        .expect("env runs");
    assert_eq!(out.status, Outcome::Exited(0));
    out.stdout
        .lines()
        .filter_map(|l| l.split_once('='))
        .map(|(k, v)| (k.to_owned(), v.to_owned()))
        .collect()
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.run_with_env
#[test]
fn the_child_prints_only_allowlisted_and_added_variables() {
    // cargo and nextest always set CARGO_MANIFEST_DIR in the parent of a test.
    assert!(std::env::var_os("CARGO_MANIFEST_DIR").is_some());
    let seen = child_env(
        &EnvPolicy::Scrub {
            allow: vec!["PATH".into()],
        },
        &[("EXPLICIT_ADDITION", "yes")],
    );
    let names: Vec<&str> = seen.keys().map(String::as_str).collect();
    assert_eq!(names, ["EXPLICIT_ADDITION", "PATH"], "{seen:?}");
    assert_eq!(seen["EXPLICIT_ADDITION"], "yes");
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.run_with_env
#[test]
fn inherit_keeps_the_parent_environment() {
    let seen = child_env(&EnvPolicy::Inherit, &[]);
    assert!(seen.contains_key("CARGO_MANIFEST_DIR"), "{seen:?}");
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.run_with_env
#[test]
fn an_explicit_addition_may_carry_a_secret_shaped_name() {
    let seen = child_env(
        &EnvPolicy::scrubbed::<[&str; 0], &str>([]),
        &[("GH_TOKEN", "t")],
    );
    // The child received it; the runner's output redactor then masks the printed value.
    assert_eq!(
        seen.get("GH_TOKEN").map(String::as_str),
        Some(gob_log::REDACTED)
    );
}

/// Child half of [`a_secret_looking_parent_variable_never_reaches_a_scrubbed_child`]: when the
/// parent test re-executes this binary with the probe mark, print what a scrubbed child sees.
#[test]
fn secret_probe() {
    if std::env::var_os(PROBE_MARK).is_none() {
        return;
    }
    let policy = EnvPolicy::scrubbed(["MY_API_TOKEN", "AWS_SECRET_ACCESS_KEY", "PLAIN_VARIABLE"]);
    for (name, value) in child_env(&policy, &[]) {
        println!("PROBE {name}={value}");
    }
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.run_with_env
// frob:tests crates/gob-exec/src/env.rs::EnvPolicy.resolve
#[test]
fn a_secret_looking_parent_variable_never_reaches_a_scrubbed_child() {
    // The standard library spawn is allowed inside gob-exec's own tests (PROC001 exempts the crate).
    let out = std::process::Command::new(std::env::current_exe().expect("test binary"))
        .args(["--exact", "secret_probe", "--nocapture", "--test-threads=1"])
        .env(PROBE_MARK, "1")
        .env("MY_API_TOKEN", "hunter2")
        .env("AWS_SECRET_ACCESS_KEY", "hunter2")
        .env("GITHUB_TOKEN", "hunter2")
        .env("PLAIN_VARIABLE", "kept-only-if-allowed")
        .output()
        .expect("re-exec the test binary");
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.contains("PROBE PATH="), "the probe ran: {text}");
    assert!(
        text.contains("PROBE PLAIN_VARIABLE=kept-only-if-allowed"),
        "an allowlisted plain name is kept: {text}"
    );
    assert!(
        !text.contains("hunter2"),
        "a secret reached the child: {text}"
    );
    assert!(!text.contains("MY_API_TOKEN"), "{text}");
}
