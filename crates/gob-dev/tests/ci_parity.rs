//! `.github/workflows/ci.yml` and `cargo dev ci` must run the same checks: every check in the
//! workflow is `cargo dev ci --step <name>` (no argv, flags or environment of its own), in the
//! order of `gob_dev::ci::steps`, on the platforms the step list says, and every step is run.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ

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

/// Names of the `--step` checks in `text`, or the first deviation naming the offending step.
fn parity(text: &str, steps: &[Step]) -> Result<(), String> {
    let mut seen = Vec::new();
    for (name, run, cond, has_env) in workflow_steps(text) {
        let Some(run) = run else { continue };
        let first = run.lines().next().unwrap_or_default().trim().to_owned();
        let in_dev = |c: &str| {
            first
                .strip_prefix("cargo dev ci --step ")
                .map(|s| s.trim() == c)
        };
        let is_check = first.starts_with("cargo dev ci");
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
        if !is_check {
            continue;
        }
        let step = steps
            .iter()
            .find(|s| in_dev(s.name) == Some(true))
            .ok_or_else(|| {
                format!("ci.yml step {name:?} runs `{first}`, which is not a cargo dev ci step")
            })?;
        if has_env {
            return Err(format!(
                "ci.yml step {:?} sets env; environment belongs in cargo dev ci ({})",
                name, step.name
            ));
        }
        let linux_in_yml = cond.as_deref().is_some_and(|c| c.contains("Linux"));
        if linux_in_yml != step.linux_only {
            return Err(format!(
                "step {}: linux_only is {} in cargo dev ci but ci.yml has if={cond:?}",
                step.name, step.linux_only
            ));
        }
        seen.push(step.name);
    }
    let want: Vec<&str> = steps.iter().map(|s| s.name).collect();
    if seen != want {
        let missing: Vec<_> = want.iter().filter(|w| !seen.contains(w)).collect();
        return Err(format!(
            "ci.yml steps {seen:?} differ from cargo dev ci {want:?}; missing from ci.yml: {missing:?}"
        ));
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
    assert!(err.contains("cargo dev ci --step docs"), "{err}");
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
