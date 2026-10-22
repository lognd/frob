//! `frob-docgen`: run `gob-dev gen` in a process that links frob (see the library docs).

use std::path::PathBuf;

use clap::Parser;
use gob_dev::Kind;
use gob_dev::out::emit;

/// Command-line interface; mirrors `cargo dev gen`.
#[derive(Debug, Parser)]
#[command(
    name = "frob-docgen",
    about = "Generate derived files with frob linked"
)]
struct Cli {
    /// Which family of files to generate.
    kind: Kind,
    /// Write nothing; exit 1 with a unified diff if any file differs.
    #[arg(long)]
    check: bool,
    /// Output root (defaults to the workspace root).
    #[arg(long)]
    root: Option<PathBuf>,
}

/// Failure outcome; `main` returning it makes the process exit 1.
struct Failed(String);

impl std::fmt::Debug for Failed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

fn main() -> Result<(), Failed> {
    gob_git::install_content_backend();
    let cli = Cli::parse();
    if let Err(e) = gob_log::init("docgen", 0, false) {
        emit(&format!("warning: logging not initialised: {e}"));
    }
    frob_docgen::register();
    gob_dev::genrun::generate_files(cli.kind, cli.check, cli.root).map_err(Failed)
}
