//! `frob check`: frob's driver over the shared [`gob_check`] pipeline, its verb and
//! its inputs (design: `rules.md` sections 4 and 6, `cli.md` section 2,
//! `grimble-model.md` 9.7, decisions D27, D30 and D62).
//!
//! The pipeline itself (walk, caches, per-file and repo passes, tool stages,
//! fixes, telemetry, report) lives in `gob-check` and is documented there.
//! This crate supplies what is frob-specific as the [`Frob`] product:
//!
//! - inputs: the symbol graph, the directive scan, `frob.lock`, the ticket
//!   ledger and `[invariants]`, collected once and shared with `frob-ack` and
//!   `frob-obligations` (both crates carry a standalone `collect` that only
//!   their own verbs and tests use; folding them into one input type is left
//!   to the reconciliation ticket);
//! - rules: the obligation file rules, the `frob-obligations`, `frob-ack`,
//!   `frob-tests` and ledger repo groups;
//! - `--ticket` scoping: the lease and ticket file set, `SCOPE001` and
//!   `TICK002`;
//! - exceptions: `frob:accept` and `frob:defer` through `frob-obligations`;
//! - the `check` verb and its JSON data.
//!
//! # `must_measure` rules
//!
//! | Rule | Subjects | Applicable when |
//! |---|---|---|
//! | `REF001` | files examined (needs a ledger) | a ledger is open or `frob.toml` has `[tickets]` |
//! | `TODO002` | tickets in the ledger | the same |
//! | `TICK002` | tickets in the ledger (scoped runs) | the same |
//! | `COV001` | functions and methods in the graph | the walk holds a Rust file |
//!
//! A repository with no ledger configured and no test-capable language is not
//! failed for silence; a configured ledger that cannot be read is.

mod filecheck;
mod options;
mod product;
mod scope;
mod snapshot;
mod verb;

use std::path::Path;

pub use gob_check::{
    AppliedFix, CheckError, CheckReport, CheckTable, Ci001, Ci003, Ci006, Ci007, Ci010, Ci014,
    Counts, FailOn, FileCheck, FixOutcome, Perf001, PerfTable, Proc001, StageTime, Stats, Timing,
    Tool001, Tool002, ToolParser, ToolStage,
};
pub use options::CheckOptions;
pub use product::Frob;
pub use scope::TicketScope;
pub use snapshot::{FrobInputs, FrobShared};
pub use verb::{Check, CheckData, Explained, TimingView, register};

/// A check's context in frob's pipeline.
pub type CheckCtx<'a> = gob_check::CheckCtx<'a, Frob>;

/// A check's thread-safe context in frob's pipeline.
pub type SharedCtx<'a> = gob_check::SharedCtx<'a, Frob>;

/// Run the whole `frob check` for the repository at `root`.
///
/// Drives [`gob_check::run`] with the [`Frob`] product: per-file rules cached
/// per file digest, repo rules per inputs digest, exceptions, then the
/// `[[check.tool]]` stages outside the time budget. With `opts.fix` the
/// Deterministic fixes are written and the pipeline runs once more.
///
/// # Errors
///
/// [`CheckError`] for a bad `frob.toml`, a failed walk, a malformed lock, an
/// unknown `--only` name, an unresolvable `--ticket`, a refused `--fix` or a
/// fix that cannot be written. Findings are never errors.
pub fn run(root: &Path, opts: &CheckOptions) -> Result<CheckReport, CheckError> {
    gob_check::run(&Frob::new(opts.clone()), root, &opts.run_options())
}
