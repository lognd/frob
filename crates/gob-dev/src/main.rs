//! `cargo dev`: developer task runner for the frob monorepo.

use clap::error::ErrorKind;
use clap::{CommandFactory, Parser, Subcommand};

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
    /// Regenerate derived files (not implemented yet).
    Gen,
}

/// Message reported for a task that has no implementation yet.
fn not_implemented(task: &Task) -> String {
    match task {
        Task::Gen => "gen: not implemented yet".to_owned(),
    }
}

fn main() {
    let cli = Cli::parse();
    // clap's error path prints to stderr and exits with status 2, which is the
    // contract for not-implemented tasks (and keeps std::process out of the tree).
    Cli::command()
        .error(ErrorKind::Io, not_implemented(&cli.command))
        .exit()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gen_reports_not_implemented() {
        let cli = Cli::try_parse_from(["gob-dev", "gen"]).expect("gen parses");
        assert_eq!(not_implemented(&cli.command), "gen: not implemented yet");
    }
}
