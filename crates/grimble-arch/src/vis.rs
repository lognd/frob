//! VIS001: `pub` free functions no other package uses.

// frob:ticket 01M4D959JV48VTTKYTEKRWYGNW

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{EdgeKind, Status, SymbolGraph, SymbolKind, SymbolRecord};

use crate::dead::last_segment;
use crate::{VIS, Verdict};

/// What reaches a unit from outside its own package.
#[derive(Default)]
struct Outside {
    must: bool,
    may: bool,
}

/// The package that owns `path`; a file outside any package is its own node.
fn package<'a>(crates: &'a BTreeMap<String, String>, path: &'a str) -> &'a str {
    crates.get(path).map_or(path, String::as_str)
}

/// True for a Rust source file.
fn is_rust(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("rs"))
}

/// True when the walk holds at least one Rust unit, the only language `VIS001` measures.
pub(crate) fn has_rust(graph: &SymbolGraph) -> bool {
    graph.records().any(|r| is_rust(r.symref.path()))
}

/// Findings for `pub` Rust free functions that only their own package uses, and the candidates examined.
pub(crate) fn check(
    graph: &SymbolGraph,
    crates: &BTreeMap<String, String>,
) -> (Vec<Verdict>, usize) {
    let exported: BTreeSet<String> = graph
        .public_api()
        .iter()
        .map(|r| r.symref.to_string())
        .collect();
    let candidates: Vec<&SymbolRecord> = graph
        .records()
        .filter(|r| r.kind == SymbolKind::Function && is_rust(r.symref.path()))
        .filter(|r| r.visibility == gob_symbols::Visibility::Public)
        .filter(|r| r.implements.is_none() && r.symref.name() != Some("main"))
        .filter(|r| !grimble_bind::eval::is_test_unit(&r.symref.to_string()))
        .filter(|r| !exported.contains(&r.symref.to_string()))
        .collect();
    let mut reach: BTreeMap<String, Outside> = BTreeMap::new();
    let mut spelled: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    for e in graph.edges_with_status() {
        if !matches!(
            e.kind,
            EdgeKind::Calls | EdgeKind::References | EdgeKind::Imports
        ) {
            continue;
        }
        let from_pkg = package(crates, e.from.path());
        match &e.to {
            Some(to) => {
                if package(crates, to.path()) == from_pkg {
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
                    spelled.entry(last_segment(n)).or_default().insert(from_pkg);
                }
            }
        }
    }
    let mut findings = Vec::new();
    for rec in &candidates {
        let key = rec.symref.to_string();
        let name = rec.symref.name().unwrap_or("unit");
        let own = package(crates, rec.symref.path());
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
            tracing::debug!(unit = %key, "VIS001 only a May edge reaches the unit from outside");
            findings.push(Verdict::unresolved(
                VIS,
                UnresolvedReason::EdgeMay,
                site,
                format!(
                    "`{name}` is reached from another package only through a possible (May) edge"
                ),
                key,
            ));
        } else if spelled
            .get(name)
            .is_some_and(|pkgs| pkgs.iter().any(|p| *p != own))
        {
            tracing::debug!(unit = %key, "VIS001 an unresolved call from outside spells the name");
            findings.push(Verdict::unresolved(
                VIS,
                UnresolvedReason::EdgeUnknown,
                site,
                format!("`{name}` may be reached from another package by an unresolved call"),
                key,
            ));
        } else {
            findings.push(Verdict::fire(
                VIS,
                Severity::Error,
                site,
                format!(
                    "`{name}` is `pub` but no other package uses it; narrow it to `pub(crate)`"
                ),
                key,
            ));
        }
    }
    (findings, candidates.len())
}
