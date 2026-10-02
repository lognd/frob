//! `cargo dev`: developer task runner for the frob monorepo.

use std::path::PathBuf;

use clap::{Parser, Subcommand};
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gen_check_parses() {
        let cli = Cli::try_parse_from(["gob-dev", "gen", "all", "--check"]).expect("parses");
        let Task::Gen { kind, check, .. } = cli.command;
        assert_eq!(kind, Kind::All);
        assert!(check);
    }
}
