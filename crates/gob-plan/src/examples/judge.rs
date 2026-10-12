//! The verdict of one example: pass, or GRL016 with the diff of expected and actual findings.

// frob:ticket 01M3ZX7F8WQQ8JKW7GVVB2EYG6
use std::fmt::Write as _;

use super::markers::{Actual, Expected, Mark};
use crate::grl::ast::ExpectKind;

/// The code of an example expectation that does not match (a test failure, not a compile error).
pub const GRL016: &str = "GRL016";

/// The verdict of one example.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExampleResult {
    /// True when the example behaved as written.
    pub passed: bool,
    /// `GRL016` on a failure.
    pub code: Option<&'static str>,
    /// One line saying what went wrong; empty on a pass.
    pub message: String,
    /// The expected-versus-actual diff; empty on a pass.
    pub diff: String,
    /// The findings the run reported, sorted; empty for a `fixed` block.
    pub found: Vec<Actual>,
}

impl ExampleResult {
    fn pass() -> Self {
        Self {
            passed: true,
            code: None,
            message: String::new(),
            diff: String::new(),
            found: Vec::new(),
        }
    }

    fn fail(message: &str, diff: String) -> Self {
        Self {
            passed: false,
            code: Some(GRL016),
            message: message.to_owned(),
            diff,
            found: Vec::new(),
        }
    }
}

fn diff(expected: &[Expected], actual: &[Actual]) -> String {
    let mut out = String::new();
    for e in expected {
        let _ = writeln!(out, "- expected {e}");
    }
    for a in actual {
        let _ = writeln!(out, "+ actual   {a}");
    }
    out
}

fn sorted(findings: &[Actual]) -> Vec<Actual> {
    let mut v = findings.to_vec();
    v.sort();
    v
}

/// Judge one example against what the run reported.
///
/// `not_applicable` says the rule was decided `NotApplicable` for the example's language.
/// `fire` passes iff the reported findings equal the expected ones and are not empty; `clean`
/// iff nothing is reported; `unresolved` iff only Unresolved is reported, on the marked lines;
/// `known-gap` iff the rule does not fire (it fails the moment it does, so a fix is noticed).
pub fn judge(
    kind: ExpectKind,
    expected: &[Expected],
    actual: &[Actual],
    not_applicable: bool,
) -> ExampleResult {
    let (exp, act) = (sorted(expected), sorted(actual));
    let fires = act.iter().any(|a| matches!(a.mark, Mark::Finding(_)));
    let verdict = match kind {
        ExpectKind::NotApplicable if not_applicable => ExampleResult::pass(),
        ExpectKind::NotApplicable => ExampleResult::fail(
            "expected notapplicable but the rule applied",
            diff(&exp, &act),
        ),
        _ if not_applicable => ExampleResult::fail(
            "the rule was notapplicable for this example",
            diff(&exp, &act),
        ),
        ExpectKind::Fire if !fires => {
            ExampleResult::fail("expected the rule to fire", diff(&exp, &act))
        }
        ExpectKind::Fire | ExpectKind::Unresolved if exp != act => ExampleResult::fail(
            "reported findings differ from the expected ones",
            diff(&exp, &act),
        ),
        ExpectKind::Unresolved if fires => {
            ExampleResult::fail("expected Unresolved but the rule fired", diff(&exp, &act))
        }
        ExpectKind::Unresolved if act.is_empty() => ExampleResult::fail(
            "expected Unresolved but nothing was reported",
            diff(&exp, &act),
        ),
        ExpectKind::Clean if !act.is_empty() => {
            ExampleResult::fail("expected no findings", diff(&exp, &act))
        }
        ExpectKind::KnownGap if fires => ExampleResult::fail(
            "known-gap now fires: the gap is closed, make it a fire example",
            diff(&exp, &act),
        ),
        _ => ExampleResult::pass(),
    };
    tracing::debug!(passed = verdict.passed, ?kind, "judged example");
    ExampleResult {
        found: act,
        ..verdict
    }
}

/// Judge a `fixed` block: the rule's fix output must equal it byte for byte.
pub fn judge_fixed(expected: &str, actual: &str) -> ExampleResult {
    if expected == actual {
        return ExampleResult::pass();
    }
    let mut d = String::new();
    for l in expected.lines() {
        let _ = writeln!(d, "- {l}");
    }
    for l in actual.lines() {
        let _ = writeln!(d, "+ {l}");
    }
    ExampleResult::fail("fix output differs from the fixed block", d)
}
