//! `TEST001`: a `frob:tests` directive names nothing the graph can find.

use gob_directives::DirectiveRecord;
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_symbols::{ResolveError, SymbolGraph};

use crate::catalog::is_test_fn;

/// A `frob:tests` directive whose target resolves to no test (or, inside a test, to no symbol).
///
/// On a non-test item the target names a test and must resolve to a test
/// function; inside a test item the target is the symbol the test covers and
/// must resolve to any symbol. Fix the symref or remove the directive.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TEST001",
    slug = "tests-target-missing",
    family = "TEST",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Test001;

/// `TEST001` using only the naming heuristic to recognise tests.
pub fn test001(records: &[DirectiveRecord], graph: &SymbolGraph) -> Vec<Finding> {
    test001_with_sources(records, graph, &|_| None)
}

/// `TEST001` with `read(path)` supplying file text for the `#[test]` attribute scan.
pub fn test001_with_sources(
    records: &[DirectiveRecord],
    graph: &SymbolGraph,
    read: &dyn Fn(&str) -> Option<String>,
) -> Vec<Finding> {
    let id: RuleId = Test001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let mut out = Vec::new();
    for rec in records
        .iter()
        .filter(|r| r.namespace == "frob" && r.verb == "tests")
    {
        let Some(target) = rec.args.positional.first().map(|t| t.value.as_str()) else {
            continue;
        };
        let covers = rec.source.is_some();
        let ok = match graph.resolve(target) {
            Ok(found) => covers || is_test(found, read),
            Err(ResolveError::Ambiguous(candidates)) => {
                covers
                    || candidates
                        .iter()
                        .filter_map(|c| graph.get(c))
                        .any(|c| is_test(c, read))
            }
            Err(ResolveError::NotFound(_)) => false,
        };
        if ok {
            continue;
        }
        let message = if covers {
            format!(
                "`frob:tests {target}` names no symbol in the graph; fix the symref or remove the directive"
            )
        } else {
            format!(
                "`frob:tests {target}` names no test function in the graph; fix the symref or remove the directive"
            )
        };
        tracing::debug!(target, covers, "TEST001");
        out.push(Finding::new(
            id.clone(),
            Severity::Error,
            Some(rec.span),
            message,
            target,
        ));
    }
    out
}

fn is_test(rec: &gob_symbols::SymbolRecord, read: &dyn Fn(&str) -> Option<String>) -> bool {
    let text = read(rec.symref.path());
    is_test_fn(rec, text.as_deref())
}
