//! `.github/workflows/ci.yml` and `cargo dev ci` must run the same checks: every check in the
//! workflow is `cargo dev ci --step <name>` on Linux and `cargo dev-isolated ci --step <name>` on
//! Windows (no argv, flags or environment of its own), in the
//! order of `gob_dev::ci::steps`, on the platforms the step list says, and every step is run.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
// frob:ticket 01M41XFSAMMQXYZEKVY0G8QF7V
// frob:ticket 01M43FB0TFBNDFH1AEC1CTNHZG

use std::path::PathBuf;

use gob_dev::ci::{self, Step};
use serde_yaml_ng::Value;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The steps of the `rust` job, as (name, run, if, `has_env`) in file order.
fn workflow_steps(text: &str) -> Vec<(String, Option<String>, Option<String>, bool)> {
    let doc: Value = serde_yaml_ng::from_str(text).unwrap();
    doc["jobs"]["rust"]["steps"]
        .as_sequence()
        .unwrap()
        .iter()
        .map(|s| {
            let get = |k: &str| s.get(k).and_then(Value::as_str).map(str::to_owned);
            (
                get("name").unwrap_or_default(),
                get("run"),
                get("if"),
                s.get("env").is_some(),
            )
        })
        .collect()
}

/// Per-OS check invocations: Linux through `cargo dev`, Windows through `cargo dev-isolated`.
const LINUX_PREFIX: &str = "cargo dev ci --step ";
const WINDOWS_PREFIX: &str = "cargo dev-isolated ci --step ";

/// The first deviation of `ci.yml` from the `cargo dev ci` step list, naming the offending step.
///
/// Linux must run every step in order through `cargo dev`; Windows every non-Linux-only step in
/// order through `cargo dev-isolated`. Neither may set env or run a raw check.
fn parity(text: &str, steps: &[Step]) -> Result<(), String> {
    let mut linux = Vec::new();
    let mut windows = Vec::new();
    for (name, run, cond, has_env) in workflow_steps(text) {
        let Some(run) = run else { continue };
        let first = run.lines().next().unwrap_or_default().trim().to_owned();
        let raw_check = [
            "cargo fmt",
            "cargo clippy",
            "cargo nextest",
            "cargo doc",
            "cargo dev gen",
            "cargo run",
            "uvx",
        ]
        .iter()
        .any(|p| run.lines().any(|l| l.trim().starts_with(p)));
        if raw_check {
            return Err(format!(
                "ci.yml step {name:?} runs a check outside cargo dev ci: {first}"
            ));
        }
        let (prefix, os, seen) = if first.starts_with(LINUX_PREFIX) {
            (LINUX_PREFIX, "Linux", &mut linux)
        } else if first.starts_with(WINDOWS_PREFIX) {
            (WINDOWS_PREFIX, "Windows", &mut windows)
        } else {
            continue;
        };
        let step = steps
            .iter()
            .find(|s| first.strip_prefix(prefix).map(str::trim) == Some(s.name))
            .ok_or_else(|| {
                format!("ci.yml step {name:?} runs `{first}`, which is not a cargo dev ci step")
            })?;
        if has_env {
            return Err(format!(
                "ci.yml step {:?} sets env; environment belongs in cargo dev ci ({})",
                name, step.name
            ));
        }
        let on_os = cond.as_deref().is_some_and(|c| c.contains(os));
        if !on_os {
            return Err(format!(
                "step {}: `{first}` must be guarded by an {os} condition, ci.yml has if={cond:?}",
                step.name
            ));
        }
        seen.push(step.name);
    }
    let want: Vec<&str> = steps.iter().map(|s| s.name).collect();
    if linux != want {
        let missing: Vec<_> = want.iter().filter(|w| !linux.contains(w)).collect();
        return Err(format!(
            "ci.yml steps {linux:?} differ from cargo dev ci {want:?}; missing from ci.yml: {missing:?}"
        ));
    }
    let want_win: Vec<&str> = steps
        .iter()
        .filter(|s| !s.linux_only)
        .map(|s| s.name)
        .collect();
    if windows != want_win {
        let missing: Vec<_> = want_win.iter().filter(|w| !windows.contains(w)).collect();
        return Err(format!(
            "ci.yml windows steps {windows:?} differ from cargo dev-isolated {want_win:?}; \
             missing from ci.yml: {missing:?}"
        ));
    }
    Ok(())
}

/// First declared prerequisite of a Linux step whose install command `ci.yml` never runs.
fn missing_install(text: &str, steps: &[Step]) -> Result<(), String> {
    let code: String = text
        .lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .collect::<Vec<_>>()
        .join("\n");
    for step in steps.iter().filter(|s| s.linux_only) {
        for need in &step.needs {
            let cmd = need.install_command();
            if !code.contains(&cmd) {
                return Err(format!(
                    "ci.yml never runs `{cmd}`, a prerequisite of step {} ({need:?})",
                    step.name
                ));
            }
        }
    }
    Ok(())
}

fn real_steps() -> Vec<Step> {
    ci::steps(&root()).unwrap()
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::ci_yml_runs_exactly_the_cargo_dev_ci_steps
#[test]
fn ci_yml_runs_exactly_the_cargo_dev_ci_steps() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    parity(&text, &real_steps()).unwrap();
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::ci_yml_installs_the_windows_target
#[test]
fn ci_yml_installs_the_windows_target() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    assert!(text.contains(&format!("rustup target add {}", ci::WINDOWS_TARGET)));
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::a_check_missing_from_cargo_dev_ci_fails_naming_it
#[test]
fn a_check_missing_from_cargo_dev_ci_fails_naming_it() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let mut steps = real_steps();
    steps.retain(|s| s.name != "docs");
    let err = parity(&text, &steps).unwrap_err();
    assert!(
        err.contains("cargo dev ci --step docs") || err.contains("missing from ci.yml"),
        "{err}"
    );
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::a_raw_or_dropped_check_in_ci_yml_fails_naming_it
#[test]
fn a_raw_or_dropped_check_in_ci_yml_fails_naming_it() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let raw = text.replace("cargo dev ci --step fmt", "cargo fmt --all");
    let err = parity(&raw, &real_steps()).unwrap_err();
    assert!(
        err.contains("rustfmt") && err.contains("cargo fmt"),
        "{err}"
    );
    let dropped = text.replace("cargo dev ci --step docs", "echo skipped");
    let err = parity(&dropped, &real_steps()).unwrap_err();
    assert!(
        err.contains("missing from ci.yml") && err.contains("docs"),
        "{err}"
    );
    let with_env = text.replace(
        "        run: cargo dev ci --step docs",
        "        env:\n          RUSTDOCFLAGS: x\n        run: cargo dev ci --step docs",
    );
    assert!(
        parity(&with_env, &real_steps())
            .unwrap_err()
            .contains("sets env")
    );
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::ci_yml_installs_every_linux_step_prerequisite
#[test]
fn ci_yml_installs_every_linux_step_prerequisite() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    missing_install(&text, &real_steps()).unwrap();
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::a_missing_prerequisite_install_fails_naming_it
#[test]
fn a_missing_prerequisite_install_fails_naming_it() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let dropped = text.replace("gcc-mingw-w64-x86-64", "nothing");
    let err = missing_install(&dropped, &real_steps()).unwrap_err();
    assert!(
        err.contains("gcc-mingw-w64-x86-64") && err.contains("clippy-windows"),
        "{err}"
    );
    let no_target = text.replace("rustup target add", "echo");
    let err = missing_install(&no_target, &real_steps()).unwrap_err();
    assert!(
        err.contains("rustup target add x86_64-pc-windows-gnu"),
        "{err}"
    );
}

// frob:ticket 01M424BWCSSMVHA9X5DJ9BCSXD
// frob:tests crates/gob-dev/tests/ci_parity.rs::dev_alias_shares_the_workspace_target_dir
#[test]
fn dev_alias_shares_the_workspace_target_dir() {
    let text = std::fs::read_to_string(root().join(".cargo/config.toml")).unwrap();
    let cfg: toml::Table = text.parse().unwrap();
    let alias = cfg["alias"]["dev"].as_str().unwrap();
    assert!(
        !alias.contains("target-dir") && !alias.contains("target/dev-tool"),
        "dev alias {alias:?} builds a second copy of the workspace"
    );
}

// frob:ticket 01M42C6MJZRH5NZGARX3YYNHAC
// frob:tests crates/gob-dev/tests/ci_parity.rs::dev_isolated_alias_builds_the_tool_in_its_own_target_dir
#[test]
fn dev_isolated_alias_builds_the_tool_in_its_own_target_dir() {
    let text = std::fs::read_to_string(root().join(".cargo/config.toml")).unwrap();
    let cfg: toml::Table = text.parse().unwrap();
    let alias = cfg["alias"]["dev-isolated"].as_str().unwrap();
    assert!(
        alias.contains("--target-dir target/dev-tool"),
        "dev-isolated alias {alias:?} must use target/dev-tool"
    );
}

// frob:ticket 01M42C6MJZRH5NZGARX3YYNHAC
// frob:tests crates/gob-dev/tests/ci_parity.rs::windows_steps_use_the_isolated_alias_with_the_same_names_and_order
#[test]
fn windows_steps_use_the_isolated_alias_with_the_same_names_and_order() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    parity(&text, &real_steps()).unwrap();
    let broken = text.replace(
        "cargo dev-isolated ci --step nextest",
        "cargo dev ci --step nextest",
    );
    let err = parity(&broken, &real_steps()).unwrap_err();
    assert!(err.contains("nextest"), "{err}");
}

// frob:ticket 01M43FB0TFBNDFH1AEC1CTNHZG
// frob:tests crates/gob-dev/tests/ci_parity.rs::ci_definition_sets_require_python_tests_and_pins_pytest
#[test]
fn ci_definition_sets_require_python_tests_and_pins_pytest() {
    let steps = ci::steps_with(&root(), true).unwrap();
    let nextest = steps.iter().find(|s| s.name == "nextest").unwrap();
    assert!(
        nextest
            .env
            .contains(&("FROB_REQUIRE_PYTHON_TESTS".to_owned(), "1".to_owned())),
        "nextest env {:?}",
        nextest.env
    );
    let pytest = steps.iter().find(|s| s.name == "pytest").unwrap();
    assert!(
        pytest.args.iter().any(|a| a == ci::PYTEST_REQUIREMENT)
            && ci::PYTEST_REQUIREMENT.contains("=="),
        "pytest step must install a pinned version: {:?}",
        pytest.args
    );
    let lenient = ci::steps_with(&root(), false).unwrap();
    let nextest = lenient.iter().find(|s| s.name == "nextest").unwrap();
    assert!(
        nextest.env.is_empty(),
        "a local run must keep the named skips"
    );
}
