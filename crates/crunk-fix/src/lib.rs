//! `crunk fix`: the Tier A autofix engine over `gob-fix`.
//!
//! Rules attach [`gob_rules::Fix`] payloads to findings. This crate collects the
//! machine-applicable ones, keeps only stylesheet sites (JSX style-prop sites are never
//! fixed), plans them with [`gob_fix::plan`] at [`gob_fix::Tier::A`] and applies the plan
//! atomically. A dry run computes exactly the same plan and diff and writes nothing, so its
//! output is byte-identical to the real run's.
//!
//! Tolerance gating (`fix_tolerance`, `color_tolerance`) is the rule's job: a rule attaches a
//! fix only for an in-tolerance value, so an out-of-tolerance finding carries no fix and is
//! left alone here.

// frob:ticket 01M43ATCQVX9A1TJ6A4AE48FDX

mod collect;
mod run;

pub use collect::{Collected, collect, is_stylesheet};
pub use run::{FixError, FixReport, apply_findings, run};
