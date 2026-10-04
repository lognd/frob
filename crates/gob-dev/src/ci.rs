//! `cargo dev ci`: run locally exactly the checks `.github/workflows/ci.yml` runs.
//!
//! [`steps`] is the single definition of every CI check (name, argv, environment, platform).
//! `ci.yml` invokes `cargo dev ci --step <name>` for each check and holds no argv of its own;
//! `tests/ci_parity.rs` fails when the workflow and this list disagree, so a check added to one
//! cannot be missing from the other. Process spawning goes through `gob-exec` (PROC001).
//! Design: `docs/design/build-test-ci.md`.
// frob:ticket 01M41T8KP0769YYXP8CAHBKXAZ
// frob:ticket 01M41XFSAMMQXYZEKVY0G8QF7V
// frob:ticket 01M41ZSW6DZMBE5QWNGB6VY10G

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
    /// Prerequisites checked before the step runs; `ci.yml` must install each (parity test).
    pub needs: Vec<Prerequisite>,
}

/// Something a step needs on the host, checked before it runs and installed by `ci.yml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Prerequisite {
    /// A rustup target for the active toolchain.
    RustTarget(&'static str),
    /// An executable on `PATH`, with the command that installs it.
    SystemTool {
        /// Executable name looked up on `PATH`.
        tool: &'static str,
        /// Exact install command (Debian/Ubuntu), printed on failure and required in `ci.yml`.
        install: &'static str,
    },
}

impl Prerequisite {
    /// The command that satisfies this prerequisite; `ci.yml` must contain it verbatim.
    #[must_use]
    pub fn install_command(&self) -> String {
        match self {
            Self::RustTarget(t) => format!("rustup target add {t}"),
            Self::SystemTool { install, .. } => (*install).to_owned(),
        }
    }
}

/// MinGW C compiler that `libsqlite3-sys` needs to build for [`WINDOWS_TARGET`] from Linux.
pub const MINGW_GCC: Prerequisite = Prerequisite::SystemTool {
    tool: "x86_64-w64-mingw32-gcc",
    install: "sudo apt-get install -y gcc-mingw-w64-x86-64",
};

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
    /// A required system tool is not on `PATH`.
    #[error("{tool} is not installed (needed by the {step} step); run: {install}")]
    ToolMissing {
        /// The missing executable.
        tool: String,
        /// Step that needs it.
        step: String,
        /// Command that installs it.
        install: String,
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
        needs: Vec::new(),
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
            needs: Vec::new(),
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
    clippy_windows.needs = vec![Prerequisite::RustTarget(WINDOWS_TARGET), MINGW_GCC];
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
    /// [`CiError::TargetMissing`] or [`CiError::ToolMissing`] when a prerequisite is absent, [`CiError::Spawn`] on any
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

/// Fail with the install command when `tool` is not an executable file on `PATH`.
fn require_tool(step: &str, tool: &str, install: &str) -> Result<(), CiError> {
    let found = std::env::var_os("PATH").is_some_and(|path| {
        std::env::split_paths(&path).any(|dir| {
            dir.join(tool).is_file()
                || dir
                    .join(format!("{tool}{}", std::env::consts::EXE_SUFFIX))
                    .is_file()
        })
    });
    if found {
        Ok(())
    } else {
        tracing::error!(tool, step, "required system tool missing");
        Err(CiError::ToolMissing {
            tool: tool.to_owned(),
            step: step.to_owned(),
            install: install.to_owned(),
        })
    }
}

/// Check every prerequisite of `step`, stopping at the first missing one.
fn require_all(root: &Path, step: &Step) -> Result<(), CiError> {
    for need in &step.needs {
        match need {
            Prerequisite::RustTarget(t) => require_target(root, t)?,
            Prerequisite::SystemTool { tool, install } => require_tool(step.name, tool, install)?,
        }
    }
    Ok(())
}

impl StepRunner for ExecRunner {
    fn run(&self, root: &Path, step: &Step) -> Result<(), CiError> {
        require_all(root, step)?;
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

/// Where nextest's `ci` profile writes its junit report, relative to the workspace root.
pub const JUNIT_PATH: &str = "target/nextest/ci/junit.xml";

/// Value of the XML attribute `name` in `tag` (a `<testcase .../>` or `<testsuites ...>` element).
fn attr<'a>(tag: &'a str, name: &str) -> Option<&'a str> {
    let needle = format!(" {name}=\"");
    let start = tag.find(&needle)? + needle.len();
    let len = tag[start..].find('"')?;
    Some(&tag[start..start + len])
}

/// Suite wall time in seconds and the `n` slowest tests (`classname name`, seconds), slowest first.
///
/// Reads the junit XML nextest writes; `None` when it has no suite time.
#[must_use]
pub fn junit_report(junit: &str, n: usize) -> Option<(f64, Vec<(String, f64)>)> {
    let suite = attr(junit.lines().find(|l| l.contains("<testsuites"))?, "time")?
        .parse()
        .ok()?;
    let mut tests: Vec<(String, f64)> = junit
        .lines()
        .filter(|l| l.trim_start().starts_with("<testcase"))
        .filter_map(|l| {
            let secs = attr(l, "time")?.parse().ok()?;
            Some((
                format!("{} {}", attr(l, "classname")?, attr(l, "name")?),
                secs,
            ))
        })
        .collect();
    tests.sort_by(|a, b| b.1.total_cmp(&a.1));
    tests.truncate(n);
    Some((suite, tests))
}

/// Number of slowest tests `cargo dev ci` lists after the nextest step.
const SLOWEST: usize = 5;

/// Say the nextest suite wall time and the five slowest tests, from the junit report under `root`.
fn report_nextest(root: &Path, say: &mut dyn FnMut(&str)) {
    let path = root.join(JUNIT_PATH);
    let Ok(junit) = std::fs::read_to_string(&path) else {
        tracing::warn!(path = %path.display(), "no nextest junit report to summarise");
        return;
    };
    let Some((suite, slowest)) = junit_report(&junit, SLOWEST) else {
        tracing::warn!(path = %path.display(), "nextest junit report is unparsable");
        return;
    };
    say(&format!(
        "   nextest suite wall time {suite:.1}s; slowest tests:"
    ));
    for (name, secs) in slowest {
        say(&format!("   {secs:>8.1}s  {name}"));
    }
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
        if step.name == "nextest" && !matches!(status, StepStatus::Skipped(_)) {
            report_nextest(root, say);
        }
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

    // frob:tests crates/gob-dev/src/ci.rs::junit_report
    #[test]
    fn junit_report_gives_suite_time_and_slowest_tests_first() {
        let xml = concat!(
            "<testsuites name=\"nextest-run\" tests=\"3\" time=\"12.5\">\n",
            "  <testsuite name=\"a::b\">\n",
            "    <testcase name=\"fast\" classname=\"a::b\" time=\"0.1\"/>\n",
            "    <testcase name=\"slow\" classname=\"a::b\" time=\"9.0\"/>\n",
            "    <testcase name=\"mid\" classname=\"a::b\" time=\"3.0\"/>\n",
            "  </testsuite>\n</testsuites>\n"
        );
        let (suite, top) = junit_report(xml, 2).unwrap();
        assert!((suite - 12.5).abs() < 1e-9);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0].0, "a::b slow");
        assert_eq!(top[1].0, "a::b mid");
        assert!(junit_report("not xml", 5).is_none());
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

    // frob:tests crates/gob-dev/src/ci.rs::ExecRunner
    #[test]
    fn missing_system_tool_fails_before_running_and_names_the_install_command() {
        // Test hook: the prerequisite points at a name that cannot exist; the program is also
        // nonexistent, so a spawn attempt would produce a different error.
        let step = Step {
            name: "needs-ghost",
            program: Program::Tool {
                name: "no-such-program-0g8qf7v".to_owned(),
            },
            args: Vec::new(),
            env: Vec::new(),
            linux_only: false,
            needs: vec![Prerequisite::SystemTool {
                tool: "no-such-tool-0g8qf7v",
                install: "sudo apt-get install -y ghost-pkg",
            }],
        };
        let e = ExecRunner.run(Path::new("."), &step).unwrap_err();
        assert!(matches!(e, CiError::ToolMissing { .. }), "{e}");
        let text = e.to_string();
        assert!(text.contains("no-such-tool-0g8qf7v"), "{text}");
        assert!(text.contains("sudo apt-get install -y ghost-pkg"), "{text}");
    }

    #[test]
    fn clippy_windows_declares_target_and_mingw() {
        let all = real();
        let s = all.iter().find(|s| s.name == "clippy-windows").unwrap();
        assert!(s.needs.contains(&Prerequisite::RustTarget(WINDOWS_TARGET)));
        assert!(s.needs.contains(&MINGW_GCC));
        assert_eq!(
            MINGW_GCC.install_command(),
            "sudo apt-get install -y gcc-mingw-w64-x86-64"
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
