//! `cargo dev ci`: run locally exactly the checks `.github/workflows/ci.yml` runs.
//!
//! [`steps`] is the single definition of every CI check (name, argv, environment, platform).
//! `ci.yml` invokes `cargo dev ci --step <name>` for each check and holds no argv of its own;
//! `tests/ci_parity.rs` fails when the workflow and this list disagree, so a check added to one
//! cannot be missing from the other. Process spawning goes through `gob-exec` (PROC001).
//! Design: `docs/design/build-test-ci.md`.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ

use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

/// Rust target whose clippy run catches Windows-only breakage from a Linux host.
pub const WINDOWS_TARGET: &str = "x86_64-pc-windows-gnu";

/// Wall-clock limit for one step (a cold nextest run is the longest).
const STEP_TIMEOUT: Duration = Duration::from_mins(60);
/// Wall-clock limit for the installed-target query.
const QUERY_TIMEOUT: Duration = Duration::from_mins(2);

/// One CI check, defined once for both `cargo dev ci` and `ci.yml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Step {
    /// Name used by `--step` and by `ci.yml`.
    pub name: &'static str,
    /// Program to run.
    pub program: Program,
    /// Arguments, exactly as CI passes them.
    pub args: Vec<String>,
    /// Environment additions, exactly as CI sets them.
    pub env: Vec<(String, String)>,
    /// Only the Linux CI job runs it; other hosts report it as skipped.
    pub linux_only: bool,
    /// Rust target that must be installed before the step can run.
    pub needs_target: Option<&'static str>,
}

/// Why the step list or a run could not proceed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum CiError {
    /// `frob.toml` is unreadable or lacks a tool stage the CI steps derive their pins from.
    #[error("frob.toml: {0}")]
    Config(String),
    /// `--step` named a check that does not exist.
    #[error("unknown step {name:?}; known steps: {known}")]
    UnknownStep {
        /// Requested name.
        name: String,
        /// Comma-separated valid names.
        known: String,
    },
    /// A required Rust target is not installed.
    #[error("rust target {target} is not installed; run: rustup target add {target}")]
    TargetMissing {
        /// The missing target triple.
        target: String,
    },
    /// A process could not be run at all.
    #[error("{0}")]
    Spawn(String),
}

/// How one step ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StepStatus {
    /// Exited 0.
    Passed,
    /// Failed, with the reason.
    Failed(String),
    /// Not run on this host, with the reason (never silent).
    Skipped(String),
}

/// A step and how it ended.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StepResult {
    /// Step name.
    pub name: &'static str,
    /// Outcome.
    pub status: StepStatus,
    /// Wall-clock time spent.
    pub elapsed: Duration,
}

fn strings(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| (*s).to_owned()).collect()
}

fn cargo(name: &'static str, args: &[&str]) -> Step {
    Step {
        name,
        program: Program::Cargo,
        args: strings(args),
        env: Vec::new(),
        linux_only: false,
        needs_target: None,
    }
}

/// `version_args` of the `[[check.tool]]` named `tool` in `frob.toml`: the pinned uvx invocation.
fn pinned_uvx(frob_toml: &toml::Table, tool: &str) -> Result<Vec<String>, CiError> {
    let bad = |what: &str| CiError::Config(format!("tool {tool}: {what}"));
    let entry = frob_toml
        .get("check")
        .and_then(|c| c.get("tool"))
        .and_then(toml::Value::as_array)
        .and_then(|a| {
            a.iter()
                .filter_map(toml::Value::as_table)
                .find(|t| t.get("name").and_then(toml::Value::as_str) == Some(tool))
        })
        .ok_or_else(|| bad("no [[check.tool]] entry"))?;
    entry
        .get("version_args")
        .and_then(toml::Value::as_array)
        .ok_or_else(|| bad("no version_args"))?
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_owned)
                .ok_or_else(|| bad("non-string version_args"))
        })
        .collect()
}

/// Every CI check in the order `ci.yml` runs it; zizmor and actionlint pins come from `frob.toml`.
///
/// # Errors
/// [`CiError::Config`] when `frob.toml` cannot supply the pinned tool versions.
pub fn steps(root: &Path) -> Result<Vec<Step>, CiError> {
    let text = std::fs::read_to_string(root.join("frob.toml")).map_err(|e| {
        tracing::error!(error = %e, "frob.toml unreadable");
        CiError::Config(e.to_string())
    })?;
    let frob_toml: toml::Table = text.parse().map_err(|e: toml::de::Error| {
        tracing::error!(error = %e, "frob.toml unparsable");
        CiError::Config(e.to_string())
    })?;
    let uvx = |name: &'static str, tool: &str| -> Result<Step, CiError> {
        Ok(Step {
            name,
            program: Program::Tool {
                name: "uvx".to_owned(),
            },
            args: pinned_uvx(&frob_toml, tool)?,
            env: Vec::new(),
            linux_only: true,
            needs_target: None,
        })
    };
    let linux = |mut s: Step| {
        s.linux_only = true;
        s
    };
    let mut clippy_windows = cargo(
        "clippy-windows",
        &[
            "clippy",
            "--all-targets",
            "--all-features",
            "--target",
            WINDOWS_TARGET,
            "--",
            "-D",
            "warnings",
        ],
    );
    clippy_windows.linux_only = true;
    clippy_windows.needs_target = Some(WINDOWS_TARGET);
    let mut docs = cargo("docs", &["doc", "--no-deps", "--all-features"]);
    docs.env = vec![("RUSTDOCFLAGS".to_owned(), "-D warnings".to_owned())];
    Ok(vec![
        cargo("fmt", &["fmt", "--all", "--check"]),
        cargo(
            "clippy",
            &[
                "clippy",
                "--all-targets",
                "--all-features",
                "--",
                "-D",
                "warnings",
            ],
        ),
        clippy_windows,
        docs,
        cargo("nextest", &["nextest", "run", "--profile", "ci"]),
        cargo("gen", &["dev", "gen", "all", "--check"]),
        uvx("zizmor", "zizmor")?,
        uvx("actionlint", "actionlint")?,
        linux(cargo("doctor", &["run", "-p", "frob-cli", "--", "doctor"])),
        linux(cargo("check", &["run", "-p", "frob-cli", "--", "check"])),
        linux(cargo(
            "test-dry-run",
            &[
                "run",
                "-p",
                "frob-cli",
                "--",
                "test",
                "--base",
                "origin/experimental",
                "--dry-run",
            ],
        )),
    ])
}

/// Executes one step; a trait so tests drive the flow without spawning anything.
pub trait StepRunner {
    /// Run `step` in `root`, returning `Ok(())` when it exits 0.
    ///
    /// # Errors
    /// [`CiError::TargetMissing`] when a required target is absent, [`CiError::Spawn`] on any
    /// other failure to run or a non-zero exit.
    fn run(&self, root: &Path, step: &Step) -> Result<(), CiError>;
}

/// The real [`StepRunner`], spawning through `gob-exec`.
#[derive(Debug, Default)]
pub struct ExecRunner;

fn runner() -> Runner {
    Runner::new(Limits { jobs: 1 })
}

fn spec(root: &Path, step: &Step, timeout: Duration, capture: bool) -> Spec {
    Spec {
        program: step.program.clone(),
        args: step.args.clone(),
        cwd: Some(root.to_path_buf()),
        env: step.env.clone(),
        timeout,
        capture,
    }
}

/// Fail with the exact `rustup` command when `target` is not installed for the active toolchain.
fn require_target(root: &Path, target: &str) -> Result<(), CiError> {
    let query = Spec {
        program: Program::Tool {
            name: "rustup".to_owned(),
        },
        args: strings(&["target", "list", "--installed"]),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: QUERY_TIMEOUT,
        capture: true,
    };
    let out = runner()
        .run(&query)
        .map_err(|e| CiError::Spawn(format!("rustup target list: {e}")))?;
    if out.status == Outcome::Exited(0) && out.stdout.lines().any(|l| l.trim() == target) {
        Ok(())
    } else {
        tracing::error!(target, "required rust target missing");
        Err(CiError::TargetMissing {
            target: target.to_owned(),
        })
    }
}

impl StepRunner for ExecRunner {
    fn run(&self, root: &Path, step: &Step) -> Result<(), CiError> {
        if let Some(target) = step.needs_target {
            require_target(root, target)?;
        }
        let out = runner()
            .run(&spec(root, step, STEP_TIMEOUT, false))
            .map_err(|e| CiError::Spawn(format!("{}: {e}", step.name)))?;
        match out.status {
            Outcome::Exited(0) => Ok(()),
            other => Err(CiError::Spawn(format!("ended {other:?}"))),
        }
    }
}

/// Whether this host is the Linux CI job's platform.
#[must_use]
pub fn host_is_linux() -> bool {
    cfg!(target_os = "linux")
}

/// Run `selected` in order through `exec`, stopping at the first failure unless `keep_going`.
///
/// `linux` says whether linux-only steps run; they are reported as skipped otherwise. Steps
/// after a stop are not listed.
pub fn run(
    root: &Path,
    selected: &[Step],
    exec: &dyn StepRunner,
    keep_going: bool,
    linux: bool,
    say: &mut dyn FnMut(&str),
) -> Vec<StepResult> {
    let mut results = Vec::new();
    let total = selected.len();
    for (i, step) in selected.iter().enumerate() {
        let started = std::time::Instant::now();
        let status = if step.linux_only && !linux {
            tracing::warn!(step = step.name, "linux-only step skipped on this host");
            StepStatus::Skipped("linux-only step, this host is not Linux".to_owned())
        } else {
            say(&format!(
                "== [{}/{total}] {}: {} {}",
                i + 1,
                step.name,
                step.program.label(),
                step.args.join(" ")
            ));
            match exec.run(root, step) {
                Ok(()) => StepStatus::Passed,
                Err(e) => {
                    tracing::error!(step = step.name, error = %e, "ci step failed");
                    StepStatus::Failed(e.to_string())
                }
            }
        };
        let failed = matches!(status, StepStatus::Failed(_));
        results.push(StepResult {
            name: step.name,
            status,
            elapsed: started.elapsed(),
        });
        if failed && !keep_going {
            break;
        }
    }
    results
}

/// Select steps by `names` (all when empty), keeping the canonical order.
///
/// # Errors
/// [`CiError::UnknownStep`] when a name matches no step.
pub fn select(all: Vec<Step>, names: &[String]) -> Result<Vec<Step>, CiError> {
    if let Some(bad) = names
        .iter()
        .find(|n| !all.iter().any(|s| s.name == n.as_str()))
    {
        return Err(CiError::UnknownStep {
            name: bad.clone(),
            known: all.iter().map(|s| s.name).collect::<Vec<_>>().join(", "),
        });
    }
    Ok(all
        .into_iter()
        .filter(|s| names.is_empty() || names.iter().any(|n| n == s.name))
        .collect())
}

/// One summary line per result plus a verdict line; true when nothing failed.
#[must_use]
pub fn summary(results: &[StepResult]) -> (Vec<String>, bool) {
    let mut lines = Vec::new();
    for r in results {
        let (mark, note) = match &r.status {
            StepStatus::Passed => ("ok     ", String::new()),
            StepStatus::Failed(why) => ("FAILED ", format!("  {why}")),
            StepStatus::Skipped(why) => ("skipped", format!("  {why}")),
        };
        lines.push(format!(
            "{mark} {:<15} {:>7.1}s{note}",
            r.name,
            r.elapsed.as_secs_f64()
        ));
    }
    let ok = !results
        .iter()
        .any(|r| matches!(r.status, StepStatus::Failed(_)));
    lines.push(if ok {
        "ci: all steps passed".to_owned()
    } else {
        "ci: FAILED".to_owned()
    });
    (lines, ok)
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use super::*;

    struct Fake {
        fail: &'static str,
        seen: RefCell<Vec<&'static str>>,
    }

    impl StepRunner for Fake {
        fn run(&self, _: &Path, step: &Step) -> Result<(), CiError> {
            self.seen.borrow_mut().push(step.name);
            if step.name == self.fail {
                Err(CiError::Spawn("boom".to_owned()))
            } else {
                Ok(())
            }
        }
    }

    fn real() -> Vec<Step> {
        let root = crate::find_workspace_root(&std::env::current_dir().unwrap()).unwrap();
        steps(&root).unwrap()
    }

    #[test]
    fn stops_at_first_failure_and_keep_going_continues() {
        let all = real();
        let n = all.len();
        let f = Fake {
            fail: "clippy",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &all, &f, false, true, &mut |_| {});
        assert_eq!(r.last().unwrap().name, "clippy");
        assert!(!summary(&r).1);
        let f = Fake {
            fail: "clippy",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &all, &f, true, true, &mut |_| {});
        assert_eq!(r.len(), n);
        assert_eq!(f.seen.borrow().len(), n);
    }

    #[test]
    fn linux_only_steps_are_reported_skipped_elsewhere() {
        let f = Fake {
            fail: "",
            seen: RefCell::new(Vec::new()),
        };
        let r = run(Path::new("."), &real(), &f, false, false, &mut |_| {});
        let skipped: Vec<_> = r
            .iter()
            .filter(|r| matches!(r.status, StepStatus::Skipped(_)))
            .collect();
        assert!(skipped.iter().any(|r| r.name == "clippy-windows"));
        assert!(!f.seen.borrow().contains(&"check"));
    }

    #[test]
    fn docs_step_sets_rustdocflags_and_nextest_uses_ci_profile() {
        let all = real();
        let docs = all.iter().find(|s| s.name == "docs").unwrap();
        assert_eq!(
            docs.env,
            vec![("RUSTDOCFLAGS".to_owned(), "-D warnings".to_owned())]
        );
        let nextest = all.iter().find(|s| s.name == "nextest").unwrap();
        assert!(nextest.args.windows(2).any(|w| w == ["--profile", "ci"]));
    }

    // frob:tests crates/gob-dev/src/ci.rs::host_is_linux
    #[test]
    fn host_platform_matches_the_target_os() {
        assert_eq!(host_is_linux(), std::env::consts::OS == "linux");
    }

    #[test]
    fn unknown_step_names_the_valid_ones() {
        let e = select(real(), &["nope".to_owned()]).unwrap_err();
        assert!(e.to_string().contains("clippy-windows"));
    }

    #[test]
    fn missing_target_error_carries_the_rustup_command() {
        let e = CiError::TargetMissing {
            target: WINDOWS_TARGET.to_owned(),
        };
        assert!(
            e.to_string()
                .contains("rustup target add x86_64-pc-windows-gnu")
        );
    }

    #[test]
    fn pins_come_from_frob_toml() {
        let all = real();
        let z = all.iter().find(|s| s.name == "zizmor").unwrap();
        assert!(z.args[0].starts_with("zizmor@"));
        let a = all.iter().find(|s| s.name == "actionlint").unwrap();
        assert!(a.args.iter().any(|x| x.starts_with("actionlint-py==")));
    }
}
