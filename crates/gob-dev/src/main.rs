//! `cargo dev`: developer task runner for the frob monorepo.

use std::path::PathBuf;

use clap::{Parser, Subcommand};
use gob_dev::import_v1::{self, ImportOptions};
use gob_dev::out::emit;
use gob_dev::{Kind, Mode, apply, ci, generate, publish, selfcopy, workspace_root};

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
    let plan = selfcopy::plan(
        cfg!(windows),
        std::env::var_os(selfcopy::MARKER).is_some(),
        cli.command.rebuilds_workspace(),
    );
    if plan == selfcopy::Plan::ReExec {
        let args: Vec<String> = std::env::args().skip(1).collect();
        return match selfcopy::reexec(&args) {
            Ok(code) => Ok(std::process::ExitCode::from(
                u8::try_from(code).unwrap_or(1),
            )),
            Err(e) => {
                tracing::error!(error = %e, "self-copy re-exec failed");
                Err(Failed(format!("error: {e}")))
            }
        };
    }
    run(cli.command).map(|()| std::process::ExitCode::SUCCESS)
}

impl Task {
    /// Whether the task runs a build that can replace `target/debug/gob-dev.exe`.
    fn rebuilds_workspace(&self) -> bool {
        matches!(self, Task::Ci { list: false, .. } | Task::Publish { .. })
    }
}

/// Run one task in this process.
fn run(command: Task) -> Result<(), Failed> {
    match command {
        Task::ImportV1Tickets {
            from,
            to,
            dry_run,
            map_out,
            report_md,
        } => import_tickets(
            &ImportOptions { from, to, dry_run },
            map_out.as_deref(),
            report_md.as_deref(),
        ),
        Task::Publish { dry_run } => publish_crates(dry_run),
        Task::Ci {
            steps,
            keep_going,
            list,
        } => ci_checks(&steps, keep_going, list),
        Task::Gen { kind, check, root } => {
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
fn publish_crates(dry_run: bool) -> Result<(), Failed> {
    let fail = |e: &dyn std::fmt::Display| {
        tracing::error!(error = %e, "publish failed");
        Failed(format!("error: {e}"))
    };
    let root = workspace_root().map_err(|e| fail(&e))?;
    let order = publish::read_metadata(&root)
        .and_then(|json| publish::plan(&json))
        .map_err(|e| fail(&e))?;
    let opts = publish::Options {
        dry_run,
        ..publish::Options::default()
    };
    publish::run(
        &order,
        &publish::CratesIo,
        &publish::CargoCli { root },
        &opts,
        &mut |line| emit(line),
        &std::thread::sleep,
    )
    .map(|_| ())
    .map_err(|e| fail(&e))
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
        assert!(matches!(cli.command, Task::Publish { dry_run: true }));
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
