//! `cargo dev profile`: time every leaf command of frob, grimble and crunk against a budget.
//!
//! Builds the three product binaries with the `profiling` cargo profile (release speed, line
//! tables), discovers each binary's leaf commands from its own `--help` ([`discover`]), runs the
//! scenario `profile.toml` declares for each ([`scenarios`]) inside a throwaway repository
//! ([`fixture`]: never the source checkout), measures wall time, peak memory and exit code
//! ([`measure`]), and writes `target/profile/report.json` plus a markdown table ([`render`]).
//! A command over `budget_ms x factor`, or exiting with an unexpected code, fails the run.
//! Design: `docs/design/build-test-ci.md` section 4 ("Command profile").
// frob:ticket 01M4CS7ZMEY096RVK91RWD03DW

pub mod discover;
pub mod fixture;
pub mod glob;
pub mod measure;
pub mod model;
pub mod render;
pub mod scenarios;

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

use fixture::Fixture;
use model::{Entry, Report, SCHEMA_VERSION};
use scenarios::{FixtureKind, ScenarioFile};

/// Cargo profile the product binaries are built with (root `Cargo.toml`).
pub const CARGO_PROFILE: &str = "profiling";
/// Where the report is written, relative to the workspace root.
pub const REPORT_PATH: &str = "target/profile/report.json";
/// Wall-clock limit for building the three binaries.
const BUILD_TIMEOUT: Duration = Duration::from_mins(60);
/// `(product, cargo package, binary)` of every profiled product.
const PRODUCTS: [(&str, &str); 3] = [
    ("frob", "frob-cli"),
    ("grimble", "grimble"),
    ("crunk", "crunk"),
];

/// Why a profile run could not produce a report.
#[derive(Debug, thiserror::Error)]
pub enum ProfileError {
    /// `profile.toml` is invalid.
    #[error(transparent)]
    Scenarios(#[from] scenarios::ScenarioError),
    /// A process could not be run, or a help call failed.
    #[error("{0}")]
    Spawn(String),
    /// A git call for a fixture failed.
    #[error("{0}")]
    Git(String),
    /// A file or directory operation failed.
    #[error("{0}")]
    Io(String),
    /// The cargo build of the product binaries failed.
    #[error("building the product binaries failed: {0}")]
    Build(String),
    /// Leaf commands exist that `profile.toml` neither runs nor skips with a reason.
    #[error("leaf commands with no scenario and no skip reason in profile.toml: {}", .0.join(", "))]
    Uncovered(Vec<String>),
    /// No ticket exists in the clone to substitute for `{ticket}`.
    #[error("the clone has no ticket to use for {{ticket}}: {0}")]
    NoTicket(String),
    /// A report file could not be read or written.
    #[error("{path}: {reason}")]
    Report {
        /// The file.
        path: String,
        /// What went wrong.
        reason: String,
    },
}

/// What one `cargo dev profile` invocation was asked to do.
#[derive(Debug, Clone)]
pub struct Options {
    /// Workspace root (the checkout the clone is taken from and `target/` lives in).
    pub root: PathBuf,
    /// Warm runs per command.
    pub runs: u32,
    /// Multiplier on every budget.
    pub budget_factor: f64,
    /// Only commands matching one of these globs (empty: all).
    pub only: Vec<String>,
    /// Directory holding built `frob`, `grimble` and `crunk`; `None` builds the profiling profile.
    pub bin_dir: Option<PathBuf>,
}

/// Binary file name of `product` on this host.
fn exe_name(product: &str) -> String {
    format!("{product}{}", std::env::consts::EXE_SUFFIX)
}

/// Build the three product binaries with the profiling profile and return their directory.
///
/// # Errors
/// [`ProfileError::Build`] when cargo fails.
pub fn build(runner: &Runner, root: &Path) -> Result<PathBuf, ProfileError> {
    let mut args: Vec<String> = ["build", "--profile", CARGO_PROFILE]
        .map(str::to_owned)
        .into();
    for (_, package) in PRODUCTS {
        args.push("-p".to_owned());
        args.push(package.to_owned());
    }
    let out = runner
        .run(&Spec {
            program: Program::Cargo,
            args,
            cwd: Some(root.to_path_buf()),
            env: Vec::new(),
            timeout: BUILD_TIMEOUT,
            capture: true,
        })
        .map_err(|e| ProfileError::Build(e.to_string()))?;
    if out.status != Outcome::Exited(0) {
        return Err(ProfileError::Build(out.stderr));
    }
    Ok(root.join("target").join(CARGO_PROFILE))
}

/// A handle of some ticket in the clone, for scenarios that need one.
fn pick_ticket(runner: &Runner, frob: &Path, repo: &Path) -> Result<String, ProfileError> {
    let out = runner
        .run(&Spec {
            program: Program::Hook {
                path: frob.to_path_buf(),
            },
            args: ["ticket", "list", "--json"].map(str::to_owned).into(),
            cwd: Some(repo.to_path_buf()),
            env: Vec::new(),
            timeout: Duration::from_mins(2),
            capture: true,
        })
        .map_err(|e| ProfileError::NoTicket(e.to_string()))?;
    let v: serde_json::Value = serde_json::from_str(&out.stdout)
        .map_err(|e| ProfileError::NoTicket(format!("unreadable list output: {e}")))?;
    v.pointer("/data/tickets")
        .and_then(serde_json::Value::as_array)
        .and_then(|t| t.first())
        .and_then(|t| t.get("handle"))
        .and_then(serde_json::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| ProfileError::NoTicket("`ticket list` returned none".to_owned()))
}

/// A fixture plus the ticket handle `{ticket}` expands to in it.
struct Prepared {
    fixture: Fixture,
    ticket: String,
}

/// Create a fixture of `kind` from `source`; a repo fixture also gets a ticket handle.
fn prepare(
    runner: &Runner,
    frob: &Path,
    source: &Path,
    kind: FixtureKind,
) -> Result<Prepared, ProfileError> {
    let fixture = fixture::create(runner, kind, source)?;
    let ticket = match kind {
        FixtureKind::Repo => pick_ticket(runner, frob, &fixture.path())?,
        FixtureKind::Tmp => String::new(),
    };
    Ok(Prepared { fixture, ticket })
}

/// Leaf commands of the three binaries in `dir`, as `product verb...`, sorted.
fn all_leaves(runner: &Runner, dir: &Path) -> Result<Vec<String>, ProfileError> {
    let mut out = Vec::new();
    for (product, _) in PRODUCTS {
        for leaf in discover::leaves(runner, product, &dir.join(exe_name(product)))? {
            out.push(format!("{product} {leaf}"));
        }
    }
    out.sort();
    Ok(out)
}

/// Fail naming every discovered leaf that has neither a scenario nor a skip reason.
///
/// Scenarios for commands help does not list (hidden verbs) are allowed; the coverage test
/// (`tests/profile_coverage.rs`) checks the file against the clap trees both ways.
///
/// # Errors
/// [`ProfileError::Uncovered`].
pub fn check_coverage(leaves: &[String], file: &ScenarioFile) -> Result<(), ProfileError> {
    let missing: Vec<String> = leaves
        .iter()
        .filter(|l| !file.scenario.contains_key(*l))
        .cloned()
        .collect();
    if missing.is_empty() {
        Ok(())
    } else {
        Err(ProfileError::Uncovered(missing))
    }
}

/// Run the profile described by `opts` and return the report; progress goes to `say`.
///
/// # Errors
/// [`ProfileError`] when the build, discovery, coverage check or a fixture fails. Budget and
/// exit-code failures are in the returned report; see [`model::violations`].
pub fn run(opts: &Options, say: &mut dyn FnMut(&str)) -> Result<Report, ProfileError> {
    let runner = Runner::new(Limits { jobs: 1 });
    let file = ScenarioFile::builtin()?;
    let dir = if let Some(d) = &opts.bin_dir {
        // Absolute, because commands run with the fixture as their working directory.
        gob_exec::canonical(d).map_err(|e| ProfileError::Io(format!("{}: {e}", d.display())))?
    } else {
        say("building frob, grimble and crunk with the profiling profile");
        build(&runner, &opts.root)?
    };
    let leaves = all_leaves(&runner, &dir)?;
    check_coverage(&leaves, &file)?;
    let selected: Vec<&String> = file
        .scenario
        .keys()
        .filter(|l| opts.only.is_empty() || opts.only.iter().any(|g| glob::matches(g, l)))
        .collect();
    say(&format!(
        "profiling {} of {} scenarios",
        selected.len(),
        file.scenario.len()
    ));

    let mut shared: Option<Prepared> = None;
    let mut entries = Vec::new();
    for command in selected {
        let scenario = &file.scenario[command];
        if let Some(reason) = &scenario.skip {
            entries.push(Entry::skipped(command, reason));
            continue;
        }
        let product = command.split(' ').next().unwrap_or_default();
        let exe = dir.join(exe_name(product));
        let frob = dir.join(exe_name("frob"));
        let shareable = scenario.fixture == FixtureKind::Repo && scenario.readonly;
        if shareable && shared.is_none() {
            shared = Some(prepare(&runner, &frob, &opts.root, FixtureKind::Repo)?);
        }
        let owned = if shareable {
            None
        } else {
            Some(prepare(&runner, &frob, &opts.root, scenario.fixture)?)
        };
        let prepared = owned
            .as_ref()
            .or(shared.as_ref())
            .ok_or_else(|| ProfileError::Io("no fixture prepared".to_owned()))?;
        let (fixture, ticket) = (&prepared.fixture, &prepared.ticket);
        say(&format!("  {command}"));
        let args = measure::expand(&scenario.args, ticket);
        entries.push(measure::measure(
            &runner,
            command,
            &exe,
            scenario,
            args,
            &fixture.path(),
            opts.runs,
        )?);
    }
    let commit = fixture::git(&runner, &opts.root, &["rev-parse", "HEAD"]).ok();
    Ok(Report {
        schema_version: SCHEMA_VERSION,
        os: std::env::consts::OS.to_owned(),
        arch: std::env::consts::ARCH.to_owned(),
        cargo_profile: CARGO_PROFILE.to_owned(),
        commit,
        runs: opts.runs,
        budget_factor: opts.budget_factor,
        entries,
    })
}

/// Read a report written by an earlier run.
///
/// # Errors
/// [`ProfileError::Report`] when the file is unreadable or not a report.
pub fn read_report(path: &Path) -> Result<Report, ProfileError> {
    let fail = |reason: String| ProfileError::Report {
        path: path.display().to_string(),
        reason,
    };
    let text = std::fs::read_to_string(path).map_err(|e| fail(e.to_string()))?;
    serde_json::from_str(&text).map_err(|e| fail(e.to_string()))
}

/// Write `report` as pretty JSON to `path`, creating its directory.
///
/// # Errors
/// [`ProfileError::Report`] when the file cannot be written.
pub fn write_report(path: &Path, report: &Report) -> Result<(), ProfileError> {
    let fail = |reason: String| ProfileError::Report {
        path: path.display().to_string(),
        reason,
    };
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| fail(e.to_string()))?;
    }
    let json = serde_json::to_string_pretty(report).map_err(|e| fail(e.to_string()))?;
    std::fs::write(path, format!("{json}\n")).map_err(|e| fail(e.to_string()))?;
    tracing::info!(path = %path.display(), entries = report.entries.len(), "profile report written");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn file(keys: &[&str]) -> ScenarioFile {
        let mut text = String::new();
        for k in keys {
            text.push_str(&format!("[scenario.\"{k}\"]\nbudget_ms = 1\n"));
        }
        ScenarioFile::parse(&text).unwrap()
    }

    // frob:tests crates/gob-dev/src/profile.rs::check_coverage
    #[test]
    fn a_leaf_without_a_scenario_is_named() {
        let leaves = vec![
            "frob a".to_owned(),
            "frob b".to_owned(),
            "crunk c".to_owned(),
        ];
        let err = check_coverage(&leaves, &file(&["frob a"])).unwrap_err();
        let text = err.to_string();
        assert!(
            text.contains("frob b") && text.contains("crunk c") && !text.contains("frob a,"),
            "{text}"
        );
    }

    // frob:tests crates/gob-dev/src/profile.rs::check_coverage
    #[test]
    fn a_scenario_for_a_hidden_verb_is_allowed() {
        let leaves = vec!["frob a".to_owned()];
        assert!(check_coverage(&leaves, &file(&["frob a", "frob hidden"])).is_ok());
    }

    // frob:tests crates/gob-dev/src/profile.rs::write_report
    #[test]
    fn report_round_trips() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("deep/report.json");
        let report = Report {
            schema_version: SCHEMA_VERSION,
            os: "linux".to_owned(),
            arch: "aarch64".to_owned(),
            cargo_profile: CARGO_PROFILE.to_owned(),
            commit: None,
            runs: 3,
            budget_factor: 1.5,
            entries: vec![Entry::skipped("frob land", "why")],
        };
        write_report(&path, &report).unwrap();
        assert_eq!(read_report(&path).unwrap(), report);
    }
}
