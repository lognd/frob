//! Test-only helpers shared across the monorepo.
//!
//! This crate is `publish = false` and not a distributed product, so the helper
//! binaries it declares (`fake-sibling`) never reach crates.io or a release archive.
// frob:ticket 01M422D5YRH5TG4499Z24K7SMT

use std::path::PathBuf;
use std::sync::OnceLock;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

/// Wall-clock limit for the helper build (a cold build of the helper and its dependencies).
const BUILD_TIMEOUT: Duration = Duration::from_mins(15);

/// The `fake-sibling` helper binary, built on first use and cached for the process.
///
/// Cargo builds a package's `[[bin]]` targets only for that package's own tests, so a
/// test in another crate cannot read `CARGO_BIN_EXE_*`; this builds the helper with the
/// same cargo, target directory and profile defaults the test run itself uses.
///
/// # Panics
/// When cargo cannot be run or does not report the built executable (a broken
/// development checkout, never a runtime condition).
#[must_use]
pub fn fake_sibling() -> PathBuf {
    static BUILT: OnceLock<PathBuf> = OnceLock::new();
    BUILT.get_or_init(build_fake_sibling).clone()
}

/// Run `cargo build --bin fake-sibling` and return the executable cargo reports.
fn build_fake_sibling() -> PathBuf {
    tracing::debug!("building the fake-sibling helper");
    let spec = Spec {
        program: Program::Cargo,
        args: [
            "build",
            "--quiet",
            "--message-format=json",
            "--bin",
            "fake-sibling",
        ]
        .map(str::to_owned)
        .to_vec(),
        cwd: Some(PathBuf::from(env!("CARGO_MANIFEST_DIR"))),
        env: Vec::new(),
        timeout: BUILD_TIMEOUT,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .expect("run cargo build for fake-sibling");
    assert!(
        out.status == Outcome::Exited(0),
        "cargo build --bin fake-sibling failed: {:?}\n{}",
        out.status,
        out.stderr
    );
    out.stdout
        .lines()
        .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
        .filter(|m| m["reason"] == "compiler-artifact" && m["target"]["name"] == "fake-sibling")
        .filter_map(|m| m["executable"].as_str().map(PathBuf::from))
        .next_back()
        .expect("cargo reported no fake-sibling executable")
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// Environment variable that turns a missing Python prerequisite from a named skip into a failure.
pub const REQUIRE_PYTHON_TESTS: &str = "FROB_REQUIRE_PYTHON_TESTS";

/// True when `tool --version` runs on this host.
fn tool_runs(tool: &str) -> bool {
    let spec = Spec {
        program: Program::Tool {
            name: tool.to_owned(),
        },
        args: vec!["--version".to_owned()],
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(60),
        capture: true,
    };
    let ok = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .is_ok_and(|o| o.status == Outcome::Exited(0));
    tracing::debug!(tool, ok, "python prerequisite probed");
    ok
}

/// Probe the prerequisites of a pytest-running test: `python3` and `pytest` on `PATH`.
///
/// Returns true when both run. When one is absent the test must return early: this
/// prints `skipped: <tool> not on PATH (<test>)` naming the missing tool, and never
/// passes silently, because setting [`REQUIRE_PYTHON_TESTS`] makes the absence a panic
/// (CI sets it where the tools are installed).
///
/// # Panics
/// When a tool is absent and [`REQUIRE_PYTHON_TESTS`] is set.
#[must_use]
pub fn python_test_prerequisites(test: &str) -> bool {
    for tool in ["python3", "pytest"] {
        if tool_runs(tool) {
            continue;
        }
        let reason = format!("{tool} not on PATH ({test})");
        assert!(
            std::env::var_os(REQUIRE_PYTHON_TESTS).is_none(),
            "{REQUIRE_PYTHON_TESTS} is set but {reason}"
        );
        eprintln!("skipped: {reason}");
        return false;
    }
    true
}
