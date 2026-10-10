//! The product-neutral check pipeline that frob and grimble both drive
//! (design: `grimble-model.md` 9.7, `rules.md` sections 2 and 4, `cli.md`
//! section 2, decisions D27, D30, D61 and D62).
//!
//! A product implements [`Product`] and calls [`run`]. It never has to
//! re-implement the walk, the caches, tool stages, fixes, telemetry or the
//! report; it supplies its inputs, its rules and its scope semantics.
//!
//! # Pipeline
//!
//! [`run`] does, in order: walk (`[check] exclude`, `size_cap`); the product's
//! [`Product::collect`]; per-file rules in parallel against the findings cache;
//! repo rules against the repo-rule cache; the product's scoped rules when a
//! scope is requested; `must_measure` accounting; the `[[check.tool]]` stages;
//! the product's exceptions over the union; a final sort by file, line and
//! rule. The tool stages run through `gob-exec`, each timed and reported
//! outside the `[perf]` budget.
//!
//! # Cache keys
//!
//! | Layer | Key |
//! |---|---|
//! | per-file rule | file digest, rule id, rule version, side-input digest (path folded in) |
//! | repo rule | inputs digest (all file digests plus [`Product::repo_digest`]) with the rule version folded in, rule id |
//!
//! # Subject accounting
//!
//! Every pass reports how many subjects each rule examined
//! ([`CheckReport::subjects_examined`]): a per-file rule counts one subject per
//! file its check [examines](FileCheck::examines), a repo group counts through
//! [`RepoGroup::counting`], scoped rules through [`ScopedFindings::subjects`].
//! A rule flagged `must_measure` in its `#[derive(Rule)]` that examined zero
//! subjects, and whose scope is [applicable](Product::applicable), becomes one
//! Unresolved finding carrying [`gob_rules::RequiredReason::ZeroSubjects`], so
//! the gate fails (cli.md section 2). A scoped run skips this for per-file
//! rules: the scope may simply hold no file the rule applies to.
//!
//! # Fixes
//!
//! `--fix` writes every finding's Deterministic [`gob_rules::Fix`] (atomic
//! per fix; overlapping, out-of-range and unparsable fixes skipped; a file
//! changed since the check refused with `E-FIX-STALE` (`CheckError::FixStale`); files written by
//! temp-and-rename and restored when a later write fails), then runs the pipeline once more and
//! reports applied and remaining findings.
//!
//! # Boundaries
//!
//! This crate depends on no frob crate (a test enforces it with `cargo
//! metadata`), so grimble links it without pulling frob in.

pub mod applicability;
mod config;
mod core;
mod defs;
mod error;
mod filecheck;
mod fix;
mod options;
mod packages;
mod pipeline;
mod product;
mod product_rules;
mod repo;
mod report;
mod required;
mod rule_set;
mod rules;
pub mod sibling;
pub mod sibling_doc;
mod status;
mod store;
mod telemetry;
mod tool_parse;
mod tools;

pub use config::{CheckTable, FailOn, PerfTable, ToolParser, ToolStage};
pub use core::{Core, FileIndex};
pub use error::CheckError;
pub use filecheck::{CheckCtx, FileCheck, SharedCtx};
pub use gob_cache::ArtifactKey;
#[doc(hidden)]
pub use gob_rules as __rules;
pub use options::RunOptions;
pub use pipeline::run;
pub use product::{
    CollectCx, Collected, CountFn, External, NoScope, Product, RepoGroup, RunFn, ScopeView,
    ScopedFindings, Snapshot,
};
pub use report::{AppliedFix, CheckReport, Counts, FixOutcome, StageTime, Stats, Timing};
pub use rule_set::RuleSet;
pub use rules::{
    Ci001, Ci003, Ci006, Ci007, Ci010, Ci014, Perf001, Proc001, Read001, Tool001, Tool002,
};
pub use status::{
    FidelityReport, LanguageFidelity, OtherCopy, SiblingRow, SkippedReport, SubjectStatus,
    hole_caveat, is_binary, opaque_finding, subject_status, subject_status_for, unreadable_finding,
    unresolved_finding,
};
