//! `frob check`: the check pipeline, its verb and the `[check]` and `[perf]` tables
//! (design: `rules.md` sections 4 and 6, `cli.md` section 2, decisions D27 and D30).
//!
//! # Pipeline
//!
//! [`run`] does, in order: walk (`[check] exclude`, `size_cap`); build the
//! symbol graph, scan directives, read `frob.lock` and the ledger once;
//! per-file rules in parallel against the findings cache; repo rules against
//! the repo-rule cache; `PROC001`, `TEST001`, the `TICK` rules and, with
//! `--ticket`, `SCOPE001`; exceptions over the union; a final sort by file,
//! line and rule. The `[[check.tool]]` stages run afterwards through
//! `gob-exec`, each timed and reported outside the `[perf]` budget.
//!
//! # Cache keys
//!
//! | Layer | Key |
//! |---|---|
//! | per-file rule | file digest, rule id, rule version, side-input digest |
//! | repo rule | inputs digest (all file digests, ledger tip, `[invariants]`) with the rule version folded in, rule id |
//!
//! Side inputs: `REF001` folds in the ledger tip, `DOC002` the state of every
//! link target; the other per-file rules read the file alone. A rule version
//! bump or a changed side input misses.
//!
//! # Collection overlap with `frob-ack` and `frob-obligations`
//!
//! Both crates carry a `collect` that walks and scans on its own. This crate
//! collects once and hands the same graph, lock, `frob:doc` list and
//! directives to each (`frob_ack::Inputs` is built directly;
//! `frob_obligations::ObligationInputs` borrows the same data), so the two
//! standalone collectors are only for their own verbs and tests. Folding
//! them into one shared input type is left to the reconciliation ticket.
//!
//! # Fixes
//!
//! `--fix` writes every finding's Deterministic [`gob_rules::Fix`] (atomic
//! per fix, overlapping fixes skipped), then runs the pipeline once more and
//! reports applied and remaining findings.

mod config;
mod error;
mod filecheck;
mod fix;
mod options;
mod pipeline;
mod repo;
mod report;
mod required;
mod rules;
mod scope;
mod snapshot;
mod store;
mod telemetry;
mod tools;
mod verb;

pub use config::{CheckTable, FailOn, PerfTable, ToolStage};
pub use error::CheckError;
pub use filecheck::{CheckCtx, FileCheck, SharedCtx};
pub use options::CheckOptions;
pub use pipeline::run;
pub use report::{AppliedFix, CheckReport, Counts, FixOutcome, StageTime, Stats, Timing};
pub use rules::{Perf001, Proc001, Tool001};
pub use verb::{Check, CheckData, Explained, TimingView, register};
