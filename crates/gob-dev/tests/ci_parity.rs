//! `.github/workflows/ci.yml` and `cargo dev ci` must run the same checks: every check in the
//! workflow is `cargo $DEV ci --step <name>` on both OSes (the matrix sets `DEV` to `dev` on Linux
//! and `dev-isolated` on Windows), or a Linux-only `cargo dev ci --step <name>` (no argv, flags or
//! environment of its own), in the
//! order of `gob_dev::ci::steps`, on the platforms the step list says, and every step is run.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
// frob:ticket 01M41XFSAMMQXYZEKVY0G8QF7V
// frob:ticket 01M43FB0TFBNDFH1AEC1CTNHZG
// frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3

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

/// Check invocations: both OSes through `cargo $DEV` (matrix `dev`), or Linux alone through `cargo dev`.
const LINUX_PREFIX: &str = "cargo dev ci --step ";
const BOTH_PREFIX: &str = "cargo $DEV ci --step ";

/// The first deviation of `ci.yml` from the `cargo dev ci` step list, naming the offending step.
///
/// Linux must run every step in order (through `cargo dev`); Windows every non-Linux-only step in
/// order, through the shared `cargo $DEV` step, which the matrix points at `dev-isolated`. Neither
/// may set env or run a raw check.
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
        let both = first.starts_with(BOTH_PREFIX);
        let prefix = if both {
            BOTH_PREFIX
        } else if first.starts_with(LINUX_PREFIX) {
            LINUX_PREFIX
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
        if both {
            if step.linux_only {
                return Err(format!(
                    "step {}: `{first}` runs on Windows too, but the step is Linux-only",
                    step.name
                ));
            }
            windows.push(step.name);
        } else if !cond.as_deref().is_some_and(|c| c.contains("Linux")) {
            return Err(format!(
                "step {}: `{first}` must be guarded by a Linux condition, ci.yml has if={cond:?}",
                step.name
            ));
        }
        linux.push(step.name);
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
        err.contains("cargo dev ci --step docs")
            || err.contains("not a cargo dev ci step")
            || err.contains("missing from ci.yml"),
        "{err}"
    );
}

// frob:tests crates/gob-dev/tests/ci_parity.rs::a_raw_or_dropped_check_in_ci_yml_fails_naming_it
#[test]
fn a_raw_or_dropped_check_in_ci_yml_fails_naming_it() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let raw = text.replace("cargo $DEV ci --step fmt", "cargo fmt --all");
    let err = parity(&raw, &real_steps()).unwrap_err();
    assert!(
        err.contains("rustfmt") && err.contains("cargo fmt"),
        "{err}"
    );
    let dropped = text.replace("cargo $DEV ci --step docs", "echo skipped");
    let err = parity(&dropped, &real_steps()).unwrap_err();
    assert!(
        err.contains("missing from ci.yml") && err.contains("docs"),
        "{err}"
    );
    let with_env = text.replace(
        "        run: cargo $DEV ci --step docs",
        "        env:\n          RUSTDOCFLAGS: x\n        run: cargo $DEV ci --step docs",
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
        "cargo $DEV ci --step nextest",
        "cargo dev ci --step nextest",
    );
    let err = parity(&broken, &real_steps()).unwrap_err();
    assert!(err.contains("nextest"), "{err}");
}

/// The matrix is what makes `cargo $DEV` mean `dev` on Linux and `dev-isolated` on Windows.
// frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3
// frob:tests crates/gob-dev/tests/ci_parity.rs::the_matrix_points_dev_at_the_right_alias_per_os
#[test]
fn the_matrix_points_dev_at_the_right_alias_per_os() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let doc: Value = serde_yaml_ng::from_str(&text).unwrap();
    let include = doc["jobs"]["rust"]["strategy"]["matrix"]["include"]
        .as_sequence()
        .unwrap();
    let alias = |os: &str| {
        include
            .iter()
            .find(|e| e["os"].as_str() == Some(os))
            .and_then(|e| e["dev"].as_str())
            .map(str::to_owned)
    };
    assert_eq!(alias("ubuntu-latest").as_deref(), Some("dev"));
    assert_eq!(alias("windows-latest").as_deref(), Some("dev-isolated"));
    assert_eq!(
        doc["jobs"]["rust"]["env"]["DEV"].as_str(),
        Some("${{ matrix.dev }}")
    );
}

/// Superseded runs are cancelled per job (never the publisher), every job has a timeout, and a
/// prose-only push skips the Rust jobs through the `changes` job, not a workflow `paths:` filter
/// (a workflow that never starts leaves the commit with no checks, which the land gate reads as
/// Unresolved).
// frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3
// frob:tests crates/gob-dev/tests/ci_parity.rs::ci_cancels_superseded_runs_has_timeouts_and_filters_by_job
#[test]
fn ci_cancels_superseded_runs_has_timeouts_and_filters_by_job() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let doc: Value = serde_yaml_ng::from_str(&text).unwrap();
    let jobs = doc["jobs"].as_mapping().unwrap();
    for (name, job) in jobs {
        let name = name.as_str().unwrap();
        if job["uses"].is_string() {
            continue; // a called workflow carries its own timeouts
        }
        assert!(
            job["timeout-minutes"].as_u64().is_some_and(|m| m > 0),
            "job {name:?} lacks timeout-minutes"
        );
    }
    assert!(
        doc["concurrency"].is_null(),
        "a workflow-level group would cancel dev-publish mid-upload"
    );
    for name in ["rust", "profile"] {
        let group = doc["jobs"][name]["concurrency"]["group"].as_str().unwrap();
        assert!(
            group.contains("github.workflow") && group.contains("github.ref"),
            "{name}: {group}"
        );
        assert_eq!(
            doc["jobs"][name]["concurrency"]["cancel-in-progress"].as_bool(),
            Some(true),
            "{name}"
        );
        let cond = doc["jobs"][name]["if"].as_str().unwrap();
        assert!(
            cond.contains("needs.changes.outputs.rust"),
            "{name}: {cond}"
        );
    }
    assert!(
        doc["jobs"]["rust"]["concurrency"]["group"]
            .as_str()
            .unwrap()
            .contains("matrix.os"),
        "matrix legs must not cancel each other"
    );
    assert_eq!(
        doc["jobs"]["dev-publish"]["concurrency"]["cancel-in-progress"].as_bool(),
        Some(false)
    );
    let on = doc["on"].as_mapping().unwrap();
    for trigger in ["push", "pull_request"] {
        let t = &on[trigger];
        assert!(
            t["paths"].is_null() && t["paths-ignore"].is_null(),
            "{trigger}: a trigger-level paths filter leaves ledger-only commits without checks"
        );
    }
    assert!(doc["jobs"]["docs"]["if"].is_null(), "docs must always run");
    assert!(
        text.contains(&format!("uvx typos=={}", ci::TYPOS_VERSION)),
        "the docs job must run the pinned typos"
    );
    let cond = doc["jobs"]["dev-artifacts"]["if"].as_str().unwrap();
    assert!(cond.contains("needs.dev-gate.outputs.build"), "{cond}");
}

/// Workspace crates are cached by content (sccache on the GitHub Actions backend), in every job
/// that compiles Rust.
// frob:ticket 01M4CTE2T943ATA1PKVBN7DCP3
// frob:tests crates/gob-dev/tests/ci_parity.rs::rust_jobs_cache_workspace_crates_with_sccache
#[test]
fn rust_jobs_cache_workspace_crates_with_sccache() {
    let text = std::fs::read_to_string(root().join(".github/workflows/ci.yml")).unwrap();
    let doc: Value = serde_yaml_ng::from_str(&text).unwrap();
    for name in ["rust", "profile"] {
        let job = &doc["jobs"][name];
        assert_eq!(
            job["env"]["RUSTC_WRAPPER"].as_str(),
            Some("sccache"),
            "{name}"
        );
        assert_eq!(
            job["env"]["SCCACHE_GHA_ENABLED"].as_str(),
            Some("true"),
            "{name}"
        );
        assert_eq!(
            job["env"]["CARGO_INCREMENTAL"].as_str(),
            Some("0"),
            "{name}"
        );
        let installs = job["steps"].as_sequence().unwrap().iter().any(|s| {
            s["uses"]
                .as_str()
                .is_some_and(|u| u.starts_with("mozilla-actions/sccache-action@"))
        });
        assert!(installs, "{name} never installs sccache");
    }
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
        !nextest
            .env
            .iter()
            .any(|(k, _)| k == "FROB_REQUIRE_PYTHON_TESTS"),
        "a local run must keep the named skips"
    );
}

// frob:ticket 01M44M58PKEM2HMKZF2CANFHAW
// frob:tests crates/gob-dev/tests/ci_parity.rs::pytest_step_installs_with_uv_not_pip_and_nextest_sees_it
#[test]
fn pytest_step_installs_with_uv_not_pip_and_nextest_sees_it() {
    let steps = ci::steps_with(&root(), true).unwrap();
    let pytest = steps.iter().find(|s| s.name == "pytest").unwrap();
    assert_eq!(pytest.program.label(), "uv");
    assert_eq!(
        pytest.args,
        ["tool", "install", "--force", ci::PYTEST_REQUIREMENT],
        "pytest must be installed with uv, never pip"
    );
    let nextest = steps.iter().find(|s| s.name == "nextest").unwrap();
    assert!(
        nextest.uv_tools_on_path,
        "nextest must find the uv-installed pytest"
    );
}

// frob:ticket 01M44M58PKEM2HMKZF2CANFHAW
// frob:tests crates/gob-dev/tests/ci_parity.rs::goway_toml_declares_uv_as_a_required_tool
#[test]
fn goway_toml_declares_uv_as_a_required_tool() {
    let text = std::fs::read_to_string(root().join("goway.toml")).unwrap();
    let table: toml::Table = text.parse().unwrap();
    let tools = table["toolchain"]["tools"].as_array().unwrap();
    assert!(tools.iter().any(|t| t.as_str() == Some("uv")), "{tools:?}");
}
