//! Prefilter by node kind: skip a file that cannot satisfy a plan (plugins.md section 6.2).
//!
//! A plan lists the kinds its top-level `find` clauses bind. A file with no node of one of them
//! has no candidate for that clause, so the rule cannot fire and the evaluation is skipped. A
//! skip is a different answer from "examined and clean": it is counted apart ([`Tally`]). A file
//! with unread regions can hide members of any kind, and a kind the executor has no test for
//! must be refused, so neither is ever skipped; they run and answer as the unfiltered run does.

// frob:ticket 01M3ZX7F57JCT6CZXY5VS9RHTR
use super::core::{ExecError, Input, KindTest, may_hide_members};
use super::outcome::{Outcomes, outcomes};
use super::relations::Relations;
use crate::plan::Plan;

/// What running a plan behind the prefilter produced for one file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Filtered {
    /// The file has no node of `kind`, so the plan was not evaluated.
    Skipped {
        /// The first prefilter kind the file lacks.
        kind: String,
    },
    /// The plan was evaluated; the outcomes equal those of an unfiltered run.
    Ran(Outcomes),
}

impl Filtered {
    /// Whether the plan was skipped without being evaluated.
    pub fn is_skipped(&self) -> bool {
        matches!(self, Self::Skipped { .. })
    }
}

/// Counts of files by what the prefilter did, kept apart so a skip never reads as a clean file.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Tally {
    /// Files the plan was evaluated on (clean or not).
    pub examined: usize,
    /// Files skipped by the prefilter.
    pub skipped: usize,
}

impl Tally {
    /// Count one file's result.
    pub fn record(&mut self, result: &Filtered) {
        if result.is_skipped() {
            self.skipped += 1;
        } else {
            self.examined += 1;
        }
    }
}

/// The first prefilter kind of `plan` that `input` provably lacks, or `None` when the plan must run.
pub fn missing_kind(plan: &Plan, input: &Input<'_>) -> Option<String> {
    if may_hide_members(input.model) {
        return None;
    }
    let term = input.model.term();
    for word in plan.prefilter_kinds() {
        let test = KindTest::from_word(word)?;
        if !term.ids().any(|n| test.member(input.model, n).is_some()) {
            return Some(word.to_string());
        }
    }
    None
}

/// Runs `plan` to outcomes unless the prefilter shows the file cannot match.
///
/// # Errors
/// As [`outcomes`]; a plan with a kind the executor cannot test is never skipped, so it fails
/// exactly as the unfiltered run does.
pub fn outcomes_prefiltered(
    plan: &Plan,
    input: &Input<'_>,
    rels: &Relations,
) -> Result<Filtered, ExecError> {
    if let Some(kind) = missing_kind(plan, input) {
        tracing::debug!(rule = %plan.parts().rule, %kind, "prefilter skipped file");
        return Ok(Filtered::Skipped { kind });
    }
    outcomes(plan, input, rels).map(Filtered::Ran)
}
