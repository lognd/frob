//! `cargo dev`: developer task runner for the frob monorepo.

use std::path::PathBuf;

use clap::{Parser, Subcommand};
use gob_dev::import_v1::{self, ImportOptions};
use gob_dev::out::emit;
use gob_dev::{Kind, Mode, apply, generate, workspace_root};

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
fn main() -> Result<(), Failed> {
    let cli = Cli::parse();
    if let Err(e) = gob_log::init("dev", 0, false) {
        emit(&format!("warning: logging not initialised: {e}"));
    }
    match cli.command {
        Task::ImportV1Tickets {
            from,
            to,
            dry_run,
            map_out,
        } => import_tickets(&ImportOptions { from, to, dry_run }, map_out.as_deref()),
        Task::Gen { kind, check, root } => {
            let workspace = workspace_root();
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

/// Run the v1 import and print its summary table, counts and dropped fields.
fn import_tickets(opts: &ImportOptions, map_out: Option<&std::path::Path>) -> Result<(), Failed> {
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
    if let Some(path) = map_out {
        std::fs::write(path, import_v1::render_id_map(&report.rows))
            .map_err(|e| Failed(format!("error: {}: {e}", path.display())))?;
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
    fn import_parses() {
        let cli = Cli::try_parse_from(["gob-dev", "import-v1-tickets", "--to", "x", "--dry-run"])
            .expect("parses");
        assert!(matches!(
            cli.command,
            Task::ImportV1Tickets { dry_run: true, .. }
        ));
    }
}
