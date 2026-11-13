//! CYCLE001: import cycles between crates (or files outside any crate).

// frob:ticket 01M3Z7141TW2H3HXJRK1QBHP7T
// frob:ticket 01M7BJPF2BB15JWV88XXFEA9MD

use std::collections::{BTreeMap, BTreeSet};

use gob_rules::{Severity, UnresolvedReason};
use gob_symbols::{EdgeKind, Status, SymbolGraph};

use crate::{CYCLE, Verdict};

/// Node-index adjacency: `adj[n]` is the sorted successors of node `n`.
type Adj = Vec<BTreeSet<usize>>;

/// Strongly connected components with more than one node, each sorted (iterative Tarjan).
fn cycles(adj: &Adj) -> Vec<BTreeSet<usize>> {
    let n = adj.len();
    let mut index = vec![usize::MAX; n];
    let mut low = vec![0; n];
    let mut on = vec![false; n];
    let mut stack = Vec::new();
    let mut next = 0;
    let mut out = Vec::new();
    for root in 0..n {
        if index[root] != usize::MAX {
            continue;
        }
        let mut work = vec![(root, adj[root].iter().copied().collect::<Vec<_>>(), 0usize)];
        index[root] = next;
        low[root] = next;
        next += 1;
        stack.push(root);
        on[root] = true;
        while let Some((v, succ, i)) = work.last_mut() {
            let v = *v;
            if let Some(&w) = succ.get(*i) {
                *i += 1;
                if index[w] == usize::MAX {
                    index[w] = next;
                    low[w] = next;
                    next += 1;
                    stack.push(w);
                    on[w] = true;
                    work.push((w, adj[w].iter().copied().collect(), 0));
                } else if on[w] {
                    low[v] = low[v].min(index[w]);
                }
            } else {
                work.pop();
                if let Some((p, _, _)) = work.last() {
                    low[*p] = low[*p].min(low[v]);
                }
                if low[v] == index[v] {
                    let mut comp = BTreeSet::new();
                    while let Some(w) = stack.pop() {
                        on[w] = false;
                        comp.insert(w);
                        if w == v {
                            break;
                        }
                    }
                    if comp.len() > 1 {
                        out.push(comp);
                    }
                }
            }
        }
    }
    out
}

/// Findings for import cycles, and the number of nodes examined.
pub(crate) fn check(
    graph: &SymbolGraph,
    crates: &BTreeMap<String, String>,
) -> (Vec<Verdict>, usize) {
    let node_of = |file: &str| crates.get(file).cloned().unwrap_or_else(|| file.to_owned());
    let mut ids: BTreeMap<String, usize> = BTreeMap::new();
    let mut first_file: Vec<String> = Vec::new();
    let mut intern = |name: String, file: &str| -> usize {
        let next = ids.len();
        let id = *ids.entry(name).or_insert(next);
        if id == first_file.len() {
            first_file.push(file.to_owned());
        } else if file < first_file[id].as_str() {
            file.clone_into(&mut first_file[id]);
        }
        id
    };
    let mut must: Vec<(usize, usize)> = Vec::new();
    let mut may: Vec<(usize, usize)> = Vec::new();
    for e in graph.edges_with_status() {
        if !matches!(
            e.kind,
            EdgeKind::Imports | EdgeKind::Calls | EdgeKind::References
        ) {
            continue;
        }
        let Some(to) = &e.to else { continue };
        let a = intern(node_of(e.from.path()), e.from.path());
        let b = intern(node_of(to.path()), to.path());
        if a == b {
            continue;
        }
        match e.status {
            Status::Must => must.push((a, b)),
            Status::May => may.push((a, b)),
            Status::Unknown => {}
        }
    }
    let mut names = vec![String::new(); ids.len()];
    for (name, &i) in &ids {
        names[i].clone_from(name);
    }
    let findings = findings_of(&names, &first_file, &must, &may);
    tracing::debug!(
        nodes = names.len(),
        cycles = findings.len(),
        "CYCLE001 evaluated"
    );
    (findings, names.len())
}

/// The unnamed root node (files outside any crate): never part of a May-only cycle.
fn is_root(names: &[String], node: usize) -> bool {
    names[node].is_empty()
}

/// Cycle findings over interned `must` and `may` edges; May edges touching the root node are ignored.
fn findings_of(
    names: &[String],
    first_file: &[String],
    must: &[(usize, usize)],
    may: &[(usize, usize)],
) -> Vec<Verdict> {
    let mut strict: Adj = vec![BTreeSet::new(); names.len()];
    for &(a, b) in must {
        strict[a].insert(b);
    }
    let mut loose = strict.clone();
    for &(a, b) in may {
        if is_root(names, a) || is_root(names, b) {
            tracing::debug!(from = %names[a], to = %names[b], "CYCLE001 skips May edge at the root node");
            continue;
        }
        loose[a].insert(b);
    }
    let sure = cycles(&strict);
    let mut findings = Vec::new();
    for comp in &sure {
        findings.push(report(comp, names, first_file, None));
    }
    for comp in cycles(&loose) {
        if !sure.contains(&comp) {
            findings.push(report(
                &comp,
                names,
                first_file,
                Some(UnresolvedReason::EdgeMay),
            ));
        }
    }
    findings
}

/// One cycle finding naming every member.
fn report(
    comp: &BTreeSet<usize>,
    names: &[String],
    first_file: &[String],
    reason: Option<UnresolvedReason>,
) -> Verdict {
    let members: Vec<&str> = comp.iter().map(|&i| names[i].as_str()).collect();
    let anchor = format!("cycle/{}", members.join(","));
    let file = comp
        .iter()
        .map(|&i| first_file[i].as_str())
        .min()
        .unwrap_or("");
    let site = (file, (0, 0));
    match reason {
        None => Verdict::fire(
            CYCLE,
            Severity::Error,
            site,
            format!("import cycle between {}", members.join(", ")),
            anchor,
        ),
        Some(r) => Verdict::unresolved(
            CYCLE,
            r,
            site,
            format!(
                "possible import cycle between {} (needs a May import edge)",
                members.join(", ")
            ),
            anchor,
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| (*s).to_owned()).collect()
    }

    fn files(n: usize) -> Vec<String> {
        (0..n).map(|i| format!("f{i}.rs")).collect()
    }

    #[test]
    fn may_cycle_through_root_is_ignored() {
        // frob:tests crates/grimble-arch/src/cycle.rs::findings_of
        let n = names(&["", "a", "b"]);
        let may = [(0, 1), (1, 2), (2, 0)];
        assert!(findings_of(&n, &files(3), &[], &may).is_empty());
    }

    #[test]
    fn may_cycle_between_crates_is_unresolved() {
        // frob:tests crates/grimble-arch/src/cycle.rs::findings_of
        let n = names(&["", "a", "b"]);
        let may = [(1, 2), (2, 1), (0, 1)];
        let found = findings_of(&n, &files(3), &[], &may);
        assert_eq!(found.len(), 1);
    }

    #[test]
    fn must_cycle_between_crates_is_reported() {
        // frob:tests crates/grimble-arch/src/cycle.rs::findings_of
        let n = names(&["", "a", "b"]);
        let must = [(1, 2), (2, 1)];
        let found = findings_of(&n, &files(3), &must, &[(0, 1)]);
        assert_eq!(found.len(), 1);
    }
}
