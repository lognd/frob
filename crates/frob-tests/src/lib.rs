//! Touched-set test selection, nextest and pytest runs and the `TEST001` rule
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
//! appended to that ticket as one evidence event per runner (`frob-evidence`).
//!
//! Python tests are selected the same way (their symbols and calls are in the
//! graph) and run through `pytest <node id>...` via gob-exec; a pytest run needs
//! `pytest` in `[evidence] allowed_tools`.
//!
//! TypeScript tests are selected as units (`test$<title>`, `suite$<title>`) and run by file through
//! `vitest run` or `jest` in the member's directory ([`node`]); a missing `node` or runner is a
//! refusal, never a skip, and their names in evidence are the units' node ids.
//!
//! C# tests are selected as `Namespace.Type.Method` ids and owned by their project: a `.csproj`
//! project runs through `dotnet test` (the `dotnet` evidence provider), a Unity `.asmdef` assembly
//! needs the unity provider, which does not exist yet, so a run that selects one refuses before
//! running anything and prints the selection (`E-TESTS-UNITY-PROVIDER`).
//!
//! What counts as a test is a heuristic documented in [`catalog`]; `TEST001`
//! ([`test001`]) flags `frob:tests` directives that name nothing.

pub mod catalog;
pub mod error;
pub mod lease;
pub mod node;
pub mod reach;
pub mod rule;
pub mod run;
pub mod select;
pub mod touched;
pub mod verb;

pub use error::{Result, TestsError};
pub use lease::lease_ticket;
pub use rule::{Test001, test001, test001_with_sources};
pub use run::{
    DotnetGroup, FrameworkRun, JsGroup, RunOptions, RunReport, dotnet_groups, js_groups,
    nextest_args, pytest_args, run, unity_assemblies,
};
pub use select::{CsharpOwner, CsharpOwners, Framework, TestTarget, select_tests};
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
