//! Garbage-input probes: every language cell fed unparseable text must yield Unresolved or `NotApplicable`, never a panic.
//!
//! `docs/design/testing.md` section 5 requires each adapter to ship a garbage-input case. The
//! probe texts here are one per matrix cell ([`crate::matrix::CELLS`]) and the check is injected
//! with the same [`Runner`] a corpus uses, so any product's rule runner can be held to it.

// frob:ticket 01M48PC1C64V7SN640NSASXGW5

use gob_rules::{RuleId, Severity};

use crate::matrix::CELLS;
use crate::run::{Case, CaseOutput, Runner};

/// One garbage probe: the cell it targets and the unparseable file it presents.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Garbage {
    /// Matrix cell (one of [`CELLS`]).
    pub cell: &'static str,
    /// Language tag handed to the runner as [`Case::language`].
    pub language: &'static str,
    /// Virtual file name handed to the runner.
    pub file_name: &'static str,
    /// Unparseable text: NULs, stray delimiters and DEL around a language keyword.
    pub text: &'static str,
}

/// The garbage probe of every matrix cell, in [`CELLS`] order.
pub const PROBES: [Garbage; 8] = [
    Garbage {
        cell: "rust",
        language: "rust",
        file_name: "garbage.rs",
        text: "\u{0}\u{1}}}}{{((( \u{7f} fn ::",
    },
    Garbage {
        cell: "python",
        language: "python",
        file_name: "garbage.py",
        text: "\u{0}\u{1})))((( \u{7f} def",
    },
    Garbage {
        cell: "typescript",
        language: "typescript",
        file_name: "garbage.ts",
        text: "\u{0}\u{1}}}}{{((( \u{7f} =>",
    },
    Garbage {
        cell: "csharp",
        language: "csharp",
        file_name: "garbage.cs",
        text: "\u{0}\u{1}}}}{{((( \u{7f} class",
    },
    Garbage {
        cell: "markdown",
        language: "markdown",
        file_name: "garbage.md",
        text: "\u{0}\u{1}]]]((( ``` \u{7f}",
    },
    Garbage {
        cell: "text",
        language: "text",
        file_name: "garbage.txt",
        text: "\u{0}\u{1}\u{2} \u{7f} ??? \u{fffd}",
    },
    Garbage {
        cell: "binary",
        language: "binary",
        file_name: "garbage.bin",
        text: "\u{0}\u{0}\u{0}\u{1}\u{2}\u{3}\u{7f}",
    },
    Garbage {
        cell: "island",
        language: "html",
        file_name: "garbage.html",
        text: "<<<>>> <script>}}}{{{ \u{0} </ <style> \u{7f}",
    },
];

/// A probe whose outcome broke the garbage-input contract.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("garbage input for cell `{cell}`: {why}")]
pub struct GarbageFailure {
    /// The cell whose probe failed.
    pub cell: String,
    /// What the runner did instead of reporting Unresolved or `NotApplicable`.
    pub why: String,
}

/// Feed the probe of each of `cells` to `runner` as rule `rule`; empty result means the contract holds.
///
/// Holds when the runner does not panic and either reports `NotApplicable` or returns at least one
/// finding, all of them Unresolved (anything else claimed knowledge about text it cannot parse).
/// A cell name outside [`CELLS`] is reported as a failure rather than skipped.
#[must_use]
pub fn check_garbage<R: CaseOutput, F: Fn(&Case) -> R>(
    runner: &Runner<F>,
    rule: &RuleId,
    cells: &[&str],
) -> Vec<GarbageFailure> {
    cells
        .iter()
        .filter_map(|cell| probe_cell(runner, rule, cell).err())
        .collect()
}

/// Run one cell's probe; `Err` names the contract breach.
fn probe_cell<R: CaseOutput, F: Fn(&Case) -> R>(
    runner: &Runner<F>,
    rule: &RuleId,
    cell: &str,
) -> Result<(), GarbageFailure> {
    let Some(probe) = PROBES.iter().find(|p| p.cell == cell) else {
        return Err(GarbageFailure {
            cell: cell.to_owned(),
            why: format!("no such matrix cell (expected one of {})", CELLS.join(", ")),
        });
    };
    let fail = |why: String| GarbageFailure {
        cell: probe.cell.to_owned(),
        why,
    };
    let case = Case {
        language: probe.language.to_owned(),
        file_name: probe.file_name.to_owned(),
        text: probe.text.to_owned(),
        rule: rule.clone(),
        rules: Vec::new(),
        config: None,
    };
    let result = runner
        .evaluate(&case)
        .map_err(|p| fail(format!("the runner panicked: {}", p.message)))?;
    if result.not_applicable.is_some() {
        return Ok(());
    }
    if result.findings.is_empty() {
        return Err(fail(
            "the runner reported neither Unresolved nor NotApplicable".into(),
        ));
    }
    if let Some(f) = result
        .findings
        .iter()
        .find(|f| f.severity != Severity::Unresolved)
    {
        return Err(fail(format!(
            "expected only Unresolved findings, got {:?} {}",
            f.severity, f.rule
        )));
    }
    tracing::debug!(cell = probe.cell, "garbage probe resolved to Unresolved");
    Ok(())
}
