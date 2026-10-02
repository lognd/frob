//! Touched-set test selection, nextest runs and the `TEST001` rule
//! (design: `build-test-ci.md`, `tickets.md` section 9).
//!
//! # Flow
//!
//! `frob test --base <ref>`: [`build_repo_graph`] builds the symbol graph of
//! the work tree, [`touched_set`] diffs it against `<ref>` (files, and the
//! symbols whose signature or body digest changed), [`select_tests`] keeps the
//! test functions that reach those symbols through `SymbolGraph::affects` plus
//! every test of a touched `tests/` file, and [`run()`] executes exactly those
//! through `cargo nextest run -p <pkg> -E '<filterset>'` via gob-exec. When the
//! working directory is a worktree holding a lease ([`lease_ticket`]) the run is
//! appended to that ticket as a nextest evidence event (`frob-evidence`).
//!
//! What counts as a test is a heuristic documented in [`catalog`]; `TEST001`
//! ([`test001`]) flags `frob:tests` directives that name nothing.

pub mod catalog;
pub mod error;
pub mod lease;
pub mod reach;
pub mod rule;
pub mod run;
pub mod select;
pub mod touched;
pub mod verb;

pub use error::{Result, TestsError};
pub use lease::lease_ticket;
pub use rule::{Test001, test001, test001_with_sources};
pub use run::{RunOptions, RunReport, nextest_args, run};
pub use select::{TestTarget, select_tests};
pub use touched::{TouchedSet, build_repo_graph, touched_set};

/// Register the `test` verb on `cli`, mirroring how the binary registers `ticket`.
#[must_use]
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<verb::TestVerb>()
}

/// In-place form of [`register`] for callers that hold `&mut Cli`.
pub fn register_mut(cli: &mut gob_cli::Cli) {
    let taken = std::mem::replace(cli, gob_cli::Cli::new("frob", env!("CARGO_PKG_VERSION")));
    *cli = register(taken);
}
