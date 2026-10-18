//! `TEST001`: a `frob:tests` directive names nothing the graph can find.

use gob_directives::DirectiveRecord;
use gob_rules::{Finding, RuleDecl, RuleId};
use gob_symbols::{ResolveError, SymbolGraph};

use crate::catalog::is_test_fn;
use crate::rules::test001::Test001;

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
    let id: RuleId = Test001::DEF
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("the rule macro validates the id: {e}"));
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
        let dotted = dotted_member_form(target)
            .filter(|d| !matches!(graph.resolve(d), Err(ResolveError::NotFound(_))));
        let message = if let Some(d) = dotted {
            tracing::debug!(target, dotted = %d, "TEST001 dotted-member hint");
            format!(
                "`frob:tests {target}` names no symbol in the graph; members nest with `.` (code-model.md section 2), write `{d}`"
            )
        } else if covers {
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
            Test001::DEF.severity,
            Some(rec.span),
            message,
            target,
        ));
    }
    out
}

/// The `path::Type.method` spelling of a `path::Type::method` symref, when it nests more than one qualname segment.
// frob:ticket 01M4BMRXQ0H30CBE9V02RPYTC8
fn dotted_member_form(target: &str) -> Option<String> {
    let (locator, qualname) = target.split_once("::")?;
    qualname
        .contains("::")
        .then(|| format!("{locator}::{}", qualname.replace("::", ".")))
}

fn is_test(rec: &gob_symbols::SymbolRecord, read: &dyn Fn(&str) -> Option<String>) -> bool {
    let text = read(rec.symref.path());
    is_test_fn(rec, text.as_deref())
}
