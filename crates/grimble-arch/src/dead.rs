//! DEAD001: private functions and methods nothing references.

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{EdgeKind, Status, SymbolGraph, SymbolKind, SymbolRecord, Symref};

use crate::{DEAD, Verdict};

/// What reaches a unit.
#[derive(Default)]
struct Reach {
    must: bool,
    may: bool,
}

/// True when `inner` is `outer` or lies inside it.
fn within(inner: &Symref, outer: &Symref) -> bool {
    inner.path() == outer.path() && inner.segments().starts_with(outer.segments())
}

/// True when the unit, or any unit enclosing it, is a test (`#[test]`, `#[cfg(test)]`): test scaffolding is an entry point.
fn in_test(key: &str, tests: &BTreeSet<String>, parents: &BTreeMap<String, String>) -> bool {
    let mut cur = key;
    while !tests.contains(cur) {
        match parents.get(cur) {
            Some(p) => cur = p,
            None => return false,
        }
    }
    true
}

/// The last segment of a spelled callee (`a::b`, `a.b`).
pub(crate) fn last_segment(name: &str) -> &str {
    name.rsplit([':', '.']).next().unwrap_or(name)
}

/// A symref string without the `[dupN]` mark on its last segment: cfg-gated variants of one function share reachability.
fn undup(key: &str) -> &str {
    match key.rfind("[dup") {
        Some(i) if key.ends_with(']') => &key[..i],
        _ => key,
    }
}

/// True for a file under a `benches/` directory: `criterion_group!` names its functions in item-level macro tokens.
fn is_bench_file(path: &str) -> bool {
    path.split('/').any(|seg| seg == "benches")
}

/// The symrefs marked as tests and the child-to-parent map used to find enclosing test units.
fn test_scaffolding(graph: &SymbolGraph) -> (BTreeSet<String>, BTreeMap<String, String>) {
    let tests = graph
        .records()
        .filter(|r| r.test)
        .map(|r| r.symref.to_string())
        .collect();
    let parents = graph
        .records()
        .filter_map(|r| Some((r.symref.to_string(), r.parent.as_ref()?.to_string())))
        .collect();
    (tests, parents)
}

/// True for a C# method the engine calls by name (`Awake`, `Update`): an entry point, never dead.
fn is_engine_entry(rec: &SymbolRecord, is_entry: &dyn Fn(&str) -> bool) -> bool {
    let named = rec.symref.name().is_some_and(|n| is_entry(undup(n)));
    let root = named
        && std::path::Path::new(rec.symref.path())
            .extension()
            .is_some_and(|ext| ext.eq_ignore_ascii_case("cs"));
    if root {
        tracing::debug!(unit = %rec.symref, "DEAD001 skips an engine entry point");
    }
    root
}

/// The private functions and methods that `DEAD001` examines.
fn candidates_of<'g>(
    graph: &'g SymbolGraph,
    is_entry: &dyn Fn(&str) -> bool,
) -> Vec<&'g SymbolRecord> {
    let public: BTreeSet<String> = graph
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    let kinds: BTreeMap<String, SymbolKind> = graph
        .records()
        .map(|r| (r.symref.to_string(), r.kind))
        .collect();
    let (tests, parents) = test_scaffolding(graph);
    graph
        .records()
        .filter(|r| matches!(r.kind, SymbolKind::Function | SymbolKind::Method))
        .filter(|r| !public.contains(&r.symref.to_string()))
        .filter(|r| r.symref.name() != Some("main") && r.implements.is_none())
        .filter(|r| {
            r.parent
                .as_ref()
                .is_none_or(|p| kinds.get(&p.to_string()) != Some(&SymbolKind::Trait))
        })
        .filter(|r| !grimble_bind::eval::is_test_unit(&r.symref.to_string()))
        .filter(|r| !is_bench_file(r.symref.path()))
        .filter(|r| !is_engine_entry(r, is_entry))
        .filter(|r| !in_test(&r.symref.to_string(), &tests, &parents))
        .collect()
}

/// How each unit is reached, and the names spelled by unresolved calls.
fn reach_of(graph: &SymbolGraph) -> (BTreeMap<String, Reach>, BTreeSet<&str>) {
    let mut reach: BTreeMap<String, Reach> = BTreeMap::new();
    let mut spelled: BTreeSet<&str> = BTreeSet::new();
    for e in graph.edges_with_status() {
        if !matches!(
            e.kind,
            EdgeKind::Calls | EdgeKind::References | EdgeKind::Imports
        ) {
            continue;
        }
        match &e.to {
            Some(to) => {
                if within(&e.from, to) {
                    continue;
                }
                let r = reach.entry(undup(&to.to_string()).to_owned()).or_default();
                match e.status {
                    Status::Must => r.must = true,
                    Status::May => r.may = true,
                    Status::Unknown => {}
                }
            }
            None => {
                if let Some(n) = &e.name {
                    spelled.insert(last_segment(n));
                }
            }
        }
    }
    (reach, spelled)
}

/// Findings for dead private functions and methods, and the candidates examined; `is_entry` names engine entry points.
pub(crate) fn check(graph: &SymbolGraph, is_entry: &dyn Fn(&str) -> bool) -> (Vec<Verdict>, usize) {
    let candidates = candidates_of(graph, is_entry);
    let (reach, spelled) = reach_of(graph);
    judge(&candidates, &reach, &spelled)
}

/// Verdicts for each candidate given how it is reached.
fn judge(
    candidates: &[&SymbolRecord],
    reach: &BTreeMap<String, Reach>,
    spelled: &BTreeSet<&str>,
) -> (Vec<Verdict>, usize) {
    let mut findings = Vec::new();
    for rec in candidates {
        let key = rec.symref.to_string();
        let name = undup(rec.symref.name().unwrap_or("unit"));
        let site = (
            rec.symref.path(),
            (
                usize::try_from(u32::from(rec.span.start())).unwrap_or(0),
                usize::try_from(u32::from(rec.span.end())).unwrap_or(0),
            ),
        );
        let r = reach.get(undup(&key));
        if r.is_some_and(|r| r.must) {
            continue;
        }
        if r.is_some_and(|r| r.may) {
            tracing::debug!(unit = %key, "DEAD001 only a May edge reaches the unit");
            findings.push(Verdict::unresolved(
                DEAD,
                UnresolvedReason::EdgeMay,
                site,
                format!("`{name}` is reached only through a possible (May) edge"),
                key,
            ));
        } else if spelled.contains(name) {
            tracing::debug!(unit = %key, "DEAD001 an unresolved call spells the name");
            findings.push(Verdict::unresolved(
                DEAD,
                UnresolvedReason::EdgeUnknown,
                site,
                format!("`{name}` may be reached by an unresolved call"),
                key,
            ));
        } else {
            findings.push(Verdict::fire(
                DEAD,
                Severity::Error,
                site,
                format!("`{name}` is private and nothing references it"),
                key,
            ));
        }
    }
    (findings, candidates.len())
}
