//! COV005: unit test function counts per scope against the `[[testing.threshold]]` minimums.

// frob:ticket 01M5HT58NK23KQMMVXD1FZ0R2D

use std::path::Path;

use frob_tests::catalog::is_test_fn;
use frob_tests::reach::Sources;
use globset::GlobSet;
use gob_rules::{Finding, RuleDecl as _, Severity};
use gob_symbols::SymbolGraph;
use gob_text::FileInterner;

use crate::ObligationInputs;
use crate::config::{TestingConfig, UnitCaseMinimum};
use crate::coverage::{header_span, scope_matcher};
use crate::rules::cov005::Cov005;
use crate::util::{def_id, finding_def};

/// The header of one minimum entry, which findings point at.
const ENTRY_HEADER: &str = "[[testing.threshold]]";

/// An unresolved COV005 finding for entry `index`: the count could not be taken.
fn unresolved(
    root: &Path,
    index: usize,
    scope: &str,
    why: &str,
    files: &mut FileInterner,
) -> Finding {
    tracing::warn!(index, scope, why, "unit case minimum not measurable");
    Finding::new(
        def_id(Cov005::DEF),
        Severity::Unresolved,
        Some(header_span(root, ENTRY_HEADER, index, files)),
        format!("[testing] scope `{scope}` could not be measured: {why}"),
        &format!("testing[{index}]:{scope}"),
    )
}

/// The number of test functions of `graph` whose file `matcher` accepts.
fn count_cases(root: &Path, graph: &SymbolGraph, matcher: &GlobSet) -> u64 {
    let mut sources = Sources::new(root);
    let mut count = 0;
    for rec in graph
        .records()
        .filter(|r| matcher.is_match(r.symref.path()))
    {
        let text = sources.get(rec.symref.path()).map(str::to_owned);
        if is_test_fn(rec, text.as_deref()) {
            count += 1;
            tracing::trace!(symbol = %rec.symref, "unit case counted");
        }
    }
    count
}

/// Evaluate minimum `t` (entry `index`), pushing its finding onto `out`.
fn check_entry(
    inputs: &ObligationInputs<'_>,
    index: usize,
    t: &UnitCaseMinimum,
    files: &mut FileInterner,
    out: &mut Vec<Finding>,
) {
    let matcher = match scope_matcher(&t.scope) {
        Ok(m) => m,
        Err(err) => {
            let why = format!("scope is not a valid glob ({err})");
            out.push(unresolved(inputs.root, index, &t.scope, &why, files));
            return;
        }
    };
    let cases = count_cases(inputs.root, inputs.graph, &matcher);
    if cases >= t.min_unit_cases {
        tracing::debug!(scope = %t.scope, cases, required = t.min_unit_cases, "unit cases meet minimum");
        return;
    }
    let shortfall = t.min_unit_cases - cases;
    tracing::info!(scope = %t.scope, cases, required = t.min_unit_cases, shortfall, "unit cases below minimum");
    out.push(finding_def(
        Cov005::DEF,
        Some(header_span(inputs.root, ENTRY_HEADER, index, files)),
        format!(
            "scope `{}`: {cases} unit cases is below the required {} (short by {shortfall})",
            t.scope, t.min_unit_cases
        ),
        &format!("{}:unit-cases", t.scope),
    ));
}

/// COV005 over the repo: every `[[testing.threshold]]` entry against the test functions of the graph.
pub(crate) fn cov005(inputs: &ObligationInputs<'_>, files: &mut FileInterner) -> Vec<Finding> {
    let config = match TestingConfig::load(inputs.root) {
        Ok(c) => c,
        Err(err) => {
            tracing::warn!(%err, "[testing] table unreadable");
            return vec![Finding::new(
                def_id(Cov005::DEF),
                Severity::Unresolved,
                Some(header_span(inputs.root, ENTRY_HEADER, 0, files)),
                format!("[testing] table could not be read: {err}"),
                "testing-config",
            )];
        }
    };
    let mut out = Vec::new();
    for (i, t) in config.threshold.iter().enumerate() {
        check_entry(inputs, i, t, files, &mut out);
    }
    out
}
