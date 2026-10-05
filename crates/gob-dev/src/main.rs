//! `cargo dev`: developer task runner for the frob monorepo.

use std::path::PathBuf;
use std::time::Duration;

use clap::{Parser, Subcommand};
use gob_dev::import_v1::{self, ImportOptions};
use gob_dev::out::emit;
use gob_dev::{Kind, Mode, apply, ci, generate, isolation, publish, workspace_root};

/// Command-line interface of the developer task runner.
#[derive(Debug, Parser)]
#[command(
    name = "gob-dev",
    about = "Developer task runner for the frob monorepo"
)]
struct Cli {
    /// The task to run.
    #[command(subcommand)]
    command: Task,
}

/// Category an imported open v1 ticket is created in.
#[derive(Debug, Clone, Copy, clap::ValueEnum)]
enum OpenCategory {
    /// Ready to start.
    Todo,
    /// Awaiting triage.
    Triage,
}

impl From<OpenCategory> for frob_ledger::model::Category {
    fn from(c: OpenCategory) -> Self {
        match c {
            OpenCategory::Todo => Self::Todo,
            OpenCategory::Triage => Self::Triage,
        }
    }
}

/// Tasks the runner can perform.
#[derive(Debug, Subcommand)]
enum Task {
    /// Regenerate derived files; with `--check`, diff instead of writing (GEN001).
    Gen {
        /// Which family of files to generate.
        kind: Kind,
        /// Write nothing; exit 1 with a unified diff if any file differs.
        #[arg(long)]
        check: bool,
        /// Output root (defaults to the workspace root).
        #[arg(long)]
        root: Option<PathBuf>,
    },
    /// Run locally exactly the checks `.github/workflows/ci.yml` runs (all, or the named steps).
    Ci {
        /// Run only this step (repeatable); `ci.yml` runs one step per workflow step.
        #[arg(long = "step")]
        steps: Vec<String>,
        /// Run every step even after a failure, then report them all.
        #[arg(long)]
        keep_going: bool,
        /// Print the step names and exit.
        #[arg(long)]
        list: bool,
    },
    /// Publish the workspace crates to crates.io in dependency order; resumable.
    Publish {
        /// Print the order and publish nothing.
        #[arg(long)]
        dry_run: bool,
        /// Instead publish a 0.0.0 placeholder for each crate name missing from crates.io
        /// (paced to the new-crate limit, resumable); lists them unless `--apply`.
        #[arg(long)]
        reserve: bool,
        /// With `--reserve`: really publish the placeholders.
        #[arg(long, requires = "reserve")]
        apply: bool,
        /// Longest total wait for crates.io rate limits, in minutes, before stopping
        /// resumably (exit 75, naming the next crate and the retry time).
        #[arg(long, default_value_t = 30)]
        max_wait: u64,
    },
    /// Convert the v1 YAML ledger into v2 ULID tickets (one-off, T-0025).
    ImportV1Tickets {
        /// The v1 ledger directory.
        #[arg(long, default_value = "tickets")]
        from: PathBuf,
        /// Where to write the v2 tree (must be empty or absent).
        #[arg(long)]
        to: PathBuf,
        /// Convert and verify in memory; write nothing.
        #[arg(long)]
        dry_run: bool,
        /// The selection file naming which open v1 tickets import (generated from the v1 gap report).
        #[arg(long, default_value = "docs/migration/v1-selection.toml")]
        selection: PathBuf,
        /// Import every v1 ticket as open work, ignoring the selection (the pre-selection behaviour).
        #[arg(long)]
        all: bool,
        /// `--to` may be an existing v2 ledger: write only new ticket directories; refuse on any id or alias collision.
        #[arg(long)]
        merge: bool,
        /// Category recorded in the create event of imported open tickets.
        #[arg(long, value_enum, default_value = "todo")]
        open_category: OpenCategory,
        /// Also write the `T-NNNN<TAB>ulid` id map to this file.
        #[arg(long)]
        map_out: Option<PathBuf>,
        /// Also write the migration report markdown (docs/migration/v1-import.md) here.
        #[arg(long)]
        report_md: Option<PathBuf>,
    },
}

/// Failure outcome of a run; `main` returning it makes the process exit 1.
struct Failed(String);

impl std::fmt::Debug for Failed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

// Returning Err from main exits 1 without std::process (PROC001 keeps it out of this crate).
fn main() -> Result<std::process::ExitCode, Failed> {
    let cli = Cli::parse();
    if let Err(e) = gob_log::init("dev", 0, false) {
        emit(&format!("warning: logging not initialised: {e}"));
    }
    if cli.command.rebuilds_workspace() {
        let guard = workspace_root()
            .map_err(|e| Failed(format!("error: {e}")))
            .and_then(|root| {
                let exe = std::env::current_exe()
                    .map_err(|e| Failed(format!("error: current_exe: {e}")))?;
                isolation::check(cfg!(windows), true, &exe, &root).map_err(|e| {
                    tracing::error!(error = %e, "refusing to rebuild the running tool");
                    Failed(format!("error: {e}"))
                })
            });
        guard?;
    }
    run(cli.command)
}

impl Task {
    /// Whether the task runs a build that can replace the running gob-dev executable.
    fn rebuilds_workspace(&self) -> bool {
        matches!(self, Task::Ci { list: false, .. } | Task::Publish { .. })
    }
}

/// Run one task in this process; the exit code is success unless a task asks for another.
fn run(command: Task) -> Result<std::process::ExitCode, Failed> {
    let ok = std::process::ExitCode::SUCCESS;
    match command {
        Task::ImportV1Tickets {
            from,
            to,
            dry_run,
            selection,
            all,
            merge,
            open_category,
            map_out,
            report_md,
        } => import_tickets(
            &ImportOptions {
                from,
                to,
                dry_run,
                selection: (!all).then_some(selection),
                merge,
                open_category: open_category.into(),
                privacy_dir: gob_git::Repo::discover(".")
                    .ok()
                    .map(|r| r.common_dir().to_path_buf()),
            },
            map_out.as_deref(),
            report_md.as_deref(),
        )
        .map(|()| ok),
        Task::Publish {
            dry_run,
            reserve,
            apply,
            max_wait,
        } => publish_crates(dry_run, reserve, apply, Duration::from_mins(max_wait)),
        Task::Ci {
            steps,
            keep_going,
            list,
        } => ci_checks(&steps, keep_going, list).map(|()| ok),
        Task::Gen { kind, check, root } => generate_files(kind, check, root).map(|()| ok),
    }
}

/// Regenerate (or with `check`, diff) the derived files.
fn generate_files(kind: Kind, check: bool, root: Option<PathBuf>) -> Result<(), Failed> {
    let workspace = match workspace_root() {
        Ok(w) => w,
        Err(e) => return Err(Failed(format!("error: {e}"))),
    };
    let root = root.unwrap_or_else(|| workspace.clone());
    let mode = if check { Mode::Check } else { Mode::Write };
    let files = generate(kind, &workspace.join("crates"));
    match apply(&root, &files, mode) {
        Ok(applied) if mode == Mode::Check && applied.differing > 0 => {
            emit(&format!(
                "GEN001: {} of {} generated files are stale; run `cargo dev gen all`",
                applied.differing, applied.total
            ));
            Err(Failed("check failed".to_owned()))
        }
        Ok(applied) => {
            emit(&format!("{} generated files up to date", applied.total));
            Ok(())
        }
        Err(e) => {
            tracing::error!(error = %e, "generation failed");
            Err(Failed(format!("error: {e}")))
        }
    }
}

/// Run the CI checks from the workspace root and print the step summary.
fn ci_checks(names: &[String], keep_going: bool, list: bool) -> Result<(), Failed> {
    let fail = |e: &dyn std::fmt::Display| {
        tracing::error!(error = %e, "ci failed");
        Failed(format!("error: {e}"))
    };
    let root = workspace_root().map_err(|e| fail(&e))?;
    let selected =
        ci::select(ci::steps(&root).map_err(|e| fail(&e))?, names).map_err(|e| fail(&e))?;
    if list {
        for step in &selected {
            emit(step.name);
        }
        return Ok(());
    }
    let results = ci::run(
        &root,
        &selected,
        &ci::ExecRunner,
        keep_going,
        ci::host_is_linux(),
        &mut |line| emit(line),
    );
    let (lines, ok) = ci::summary(&results);
    for line in &lines {
        emit(line);
    }
    if ok {
        Ok(())
    } else {
        Err(Failed("ci failed".to_owned()))
    }
}

/// Plan and run the crates.io publish from the workspace root.
///
/// A run stopped by the rate limit prints its message and exits `RESUMABLE_EXIT`.
fn publish_crates(
    dry_run: bool,
    reserve: bool,
    apply: bool,
    max_wait: Duration,
) -> Result<std::process::ExitCode, Failed> {
    let fail = |e: &dyn std::fmt::Display| {
        tracing::error!(error = %e, "publish failed");
        Failed(format!("error: {e}"))
    };
    let root = workspace_root().map_err(|e| fail(&e))?;
    let order = publish::read_metadata(&root)
        .and_then(|json| publish::plan(&json))
        .map_err(|e| fail(&e))?;
    let cargo = publish::CargoCli {
        root,
        clock: std::sync::Arc::new(gob_time::SystemClock::pin()),
    };
    let say = &mut |line: &str| emit(line);
    let result = if reserve {
        let opts = publish::ReserveOptions {
            apply,
            max_wait,
            ..publish::ReserveOptions::default()
        };
        publish::reserve(
            &order,
            &publish::CratesIo,
            &cargo,
            &opts,
            say,
            &std::thread::sleep,
        )
        .map(|_| ())
    } else {
        let opts = publish::Options {
            dry_run,
            max_wait,
            ..publish::Options::default()
        };
        publish::run(
            &order,
            &publish::CratesIo,
            &cargo,
            &opts,
            say,
            &std::thread::sleep,
        )
        .map(|_| ())
    };
    match result {
        Ok(()) => Ok(std::process::ExitCode::SUCCESS),
        Err(e @ publish::PublishError::RateLimitBudget { .. }) => {
            tracing::warn!(error = %e, "stopped on the rate limit; resumable");
            emit(&format!("stopped (resumable): {e}"));
            Ok(std::process::ExitCode::from(publish::RESUMABLE_EXIT))
        }
        Err(e) => Err(fail(&e)),
    }
}

/// Run the v1 import and print its summary table, counts and dropped fields.
fn import_tickets(
    opts: &ImportOptions,
    map_out: Option<&std::path::Path>,
    report_md: Option<&std::path::Path>,
) -> Result<(), Failed> {
    let report = import_v1::run(opts).map_err(|e| {
        tracing::error!(error = %e, "import failed");
        Failed(format!("error: {e}"))
    })?;
    for line in import_v1::render_table(&report.rows) {
        emit(&line);
    }
    emit("");
    for line in import_v1::render_selection(&report.dispositions, &report.open, &report.skipped) {
        emit(&line);
    }
    emit("");
    emit(&format!(
        "== redaction: private-term rules loaded: {}; tickets rewritten: {}; blocked: {} ==",
        report.private_rules_loaded,
        report.redactions.len(),
        report.blocked.len()
    ));
    for (id, what) in &report.redactions {
        emit(&format!("{id}: {what}"));
    }
    for id in &report.blocked {
        emit(&format!(
            "{id}: BLOCKED, an absolute home path survived redaction"
        ));
    }
    emit(&format!(
        "{} tickets, {} events{}",
        report.rows.len(),
        report.events,
        if opts.dry_run {
            " (dry run, nothing written)"
        } else {
            ""
        }
    ));
    emit(&format!("by type: {:?}", report.by_type));
    emit(&format!("by category: {:?}", report.by_category));
    for (field, count) in &report.dropped {
        emit(&format!(
            "dropped v1 field {field}: {count} tickets carried a value"
        ));
    }
    for warning in &report.warnings {
        emit(&format!("warning: {warning}"));
    }
    let write = |path: &std::path::Path, text: String| {
        std::fs::write(path, text).map_err(|e| Failed(format!("error: {}: {e}", path.display())))
    };
    if let Some(path) = map_out {
        write(path, import_v1::render_id_map(&report.rows))?;
    }
    if let Some(path) = report_md {
        write(path, import_v1::render_report_md(&report))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gen_check_parses() {
        let cli = Cli::try_parse_from(["gob-dev", "gen", "all", "--check"]).expect("parses");
        let Task::Gen { kind, check, .. } = cli.command else {
            panic!("not a gen task");
        };
        assert_eq!(kind, Kind::All);
        assert!(check);
    }

    #[test]
    fn publish_parses() {
        let cli = Cli::try_parse_from(["gob-dev", "publish", "--dry-run"]).expect("parses");
        assert!(matches!(
            cli.command,
            Task::Publish {
                dry_run: true,
                reserve: false,
                max_wait: 30,
                ..
            }
        ));
    }

    #[test]
    fn publish_reserve_parses_and_apply_needs_reserve() {
        let cli =
            Cli::try_parse_from(["gob-dev", "publish", "--reserve", "--apply"]).expect("parses");
        assert!(matches!(
            cli.command,
            Task::Publish {
                reserve: true,
                apply: true,
                ..
            }
        ));
        assert!(Cli::try_parse_from(["gob-dev", "publish", "--apply"]).is_err());
    }

    #[test]
    fn import_parses() {
        let cli = Cli::try_parse_from(["gob-dev", "import-v1-tickets", "--to", "x", "--dry-run"])
            .expect("parses");
        assert!(matches!(
            cli.command,
            Task::ImportV1Tickets { dry_run: true, .. }
        ));
    }
}
