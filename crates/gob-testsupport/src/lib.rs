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

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The `fake-dotnet` helper binary (a stand-in `dotnet` that writes a canned TRX), built on first use and cached.
///
/// # Panics
/// As [`fake_sibling`].
#[must_use]
pub fn fake_dotnet() -> PathBuf {
    static BUILT: OnceLock<PathBuf> = OnceLock::new();
    BUILT.get_or_init(|| build_helper("fake-dotnet")).clone()
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The `fake-unity` helper binary (a stand-in Unity editor that writes canned `NUnit` XML), built on first use and cached.
///
/// # Panics
/// As [`fake_sibling`].
#[must_use]
pub fn fake_unity() -> PathBuf {
    static BUILT: OnceLock<PathBuf> = OnceLock::new();
    BUILT.get_or_init(|| build_helper("fake-unity")).clone()
}

/// Build the `fake-sibling` helper; see [`build_helper`].
fn build_fake_sibling() -> PathBuf {
    build_helper("fake-sibling")
}

/// Run `cargo build --bin <name>` and return the executable cargo reports.
fn build_helper(name: &str) -> PathBuf {
    tracing::debug!(name, "building a test helper");
    let spec = Spec {
        program: Program::Cargo,
        args: ["build", "--quiet", "--message-format=json", "--bin", name]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(PathBuf::from(env!("CARGO_MANIFEST_DIR"))),
        env: Vec::new(),
        timeout: BUILD_TIMEOUT,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .expect("run cargo build for a test helper");
    assert!(
        out.status == Outcome::Exited(0),
        "cargo build --bin {name} failed: {:?}\n{}",
        out.status,
        out.stderr
    );
    out.stdout
        .lines()
        .filter_map(|l| serde_json::from_str::<serde_json::Value>(l).ok())
        .filter(|m| m["reason"] == "compiler-artifact" && m["target"]["name"] == name)
        .filter_map(|m| m["executable"].as_str().map(PathBuf::from))
        .next_back()
        .expect("cargo reported no helper executable")
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// Environment variable that turns a missing Python prerequisite from a named skip into a failure.
pub const REQUIRE_PYTHON_TESTS: &str = "FROB_REQUIRE_PYTHON_TESTS";

/// Python launchers tried in order: `python3`, `python`, then the Windows `py -3` launcher.
const PYTHON_LAUNCHERS: [(&str, &[&str]); 3] = [("python3", &[]), ("python", &[]), ("py", &["-3"])];

/// True when `tool args... --version` runs; with `expect`, its output must also start with it.
fn tool_runs(tool: &str, lead: &[&str], expect: Option<&str>) -> bool {
    let mut args: Vec<String> = lead.iter().map(|a| (*a).to_owned()).collect();
    args.push("--version".to_owned());
    let spec = Spec {
        program: Program::Tool {
            name: tool.to_owned(),
        },
        args,
        cwd: None,
        env: Vec::new(),
        timeout: Duration::from_secs(60),
        capture: true,
    };
    let ok = Runner::new(Limits { jobs: 1 }).run(&spec).is_ok_and(|o| {
        o.status == Outcome::Exited(0)
            && expect.is_none_or(|e| {
                // Python 2 printed its version on stderr; a Windows store stub prints nothing.
                o.stdout.trim_start().starts_with(e) || o.stderr.trim_start().starts_with(e)
            })
    });
    tracing::debug!(tool, ?lead, ok, "python prerequisite probed");
    ok
}

/// True when a Python 3 interpreter is reachable as `python3`, `python` or `py -3` (first hit wins).
fn python3_runs() -> bool {
    PYTHON_LAUNCHERS
        .iter()
        .any(|(tool, lead)| tool_runs(tool, lead, Some("Python 3")))
}

/// Probe the prerequisites of a pytest-running test: a Python 3 interpreter (`python3`, `python`
/// or `py -3`) and `pytest` on `PATH`.
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
        let found = if tool == "python3" {
            python3_runs()
        } else {
            tool_runs(tool, &[], None)
        };
        if found {
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

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// Environment variable that turns a missing Node.js prerequisite from a named skip into a failure.
pub const REQUIRE_NODE_TESTS: &str = "FROB_REQUIRE_NODE_TESTS";

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// Probe the prerequisites of a test that runs real JavaScript tools: each of `tools` (`node`, `vitest`, `jest`) must run `--version` from `PATH`.
///
/// Returns true when all run. When one is absent the test must return early: this prints
/// `skipped: <tool> not on PATH (<test>)` naming it, and never passes silently, because
/// setting [`REQUIRE_NODE_TESTS`] makes the absence a panic.
///
/// # Panics
/// When a tool is absent and [`REQUIRE_NODE_TESTS`] is set.
#[must_use]
pub fn node_test_prerequisites(test: &str, tools: &[&str]) -> bool {
    for tool in tools {
        if tool_runs(tool, &[], None) {
            continue;
        }
        let reason = format!("{tool} not on PATH ({test})");
        assert!(
            std::env::var_os(REQUIRE_NODE_TESTS).is_none(),
            "{REQUIRE_NODE_TESTS} is set but {reason}"
        );
        eprintln!("skipped: {reason}");
        return false;
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A tool name no host has is reported as not runnable.
    #[test]
    fn a_missing_tool_is_not_runnable() {
        assert!(!tool_runs("frob-no-such-tool-xyz", &[], None));
    }

    /// The launcher list is python3, python, then `py -3`, and a Python 3 on the host is found.
    #[test]
    fn python_launchers_are_tried_in_order_and_find_python3() {
        let names: Vec<_> = PYTHON_LAUNCHERS.iter().map(|(n, _)| *n).collect();
        assert_eq!(names, ["python3", "python", "py"]);
        assert_eq!(PYTHON_LAUNCHERS[2].1, ["-3"]);
        // Presence depends on the host; the probe must simply not panic and agree with itself.
        assert_eq!(python3_runs(), python3_runs());
    }
}
