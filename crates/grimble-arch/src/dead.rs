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

/// The last segment of a spelled callee (`a::b`, `a.b`).
pub(crate) fn last_segment(name: &str) -> &str {
    name.rsplit([':', '.']).next().unwrap_or(name)
}

/// Findings for dead private functions and methods, and the candidates examined.
pub(crate) fn check(graph: &SymbolGraph) -> (Vec<Verdict>, usize) {
    let public: BTreeSet<String> = graph
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    let kinds: BTreeMap<String, SymbolKind> = graph
        .records()
        .map(|r| (r.symref.to_string(), r.kind))
        .collect();
    let candidates: Vec<&SymbolRecord> = graph
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
        .collect();
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
                let r = reach.entry(to.to_string()).or_default();
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
    let mut findings = Vec::new();
    for rec in &candidates {
        let key = rec.symref.to_string();
        let name = rec.symref.name().unwrap_or("unit");
        let site = (
            rec.symref.path(),
            (
                usize::try_from(u32::from(rec.span.start())).unwrap_or(0),
                usize::try_from(u32::from(rec.span.end())).unwrap_or(0),
            ),
        );
        let r = reach.get(&key);
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
