//! strata-core: compute-only kernels for frob.strata (docs/strata/kernel.md).
//!
//! Every function is data-in/data-out: flattened graph tuples in, witness
//! paths and numbers out. No IO, no model validation, no vocabulary words --
//! validation and elaboration stay in Python (frob.strata), which remains
//! the open interface. This crate is fully independent of every other
//! project (charter decision D2: NOT shared with lithos).
//!
//! The prover runs constantly (per claim, per check, per save), so the
//! fixpoint/propagation loops live here rather than in Python (charter
//! decision D3 as amended 2026-07-17).

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

mod parse;

/// One directed edge of the influence graph, flattened for the boundary:
/// (flow_id, src, dst, barrier) where `barrier` marks a flow carrying any
/// endorse/declassify boundary (a declared trust/label change point).
type Edge = (String, String, String, bool);

/// BIND: reachable
///
/// WHY: the influence closure is the single hottest operation in the
/// prover -- every noflow/reach claim walks it. Deterministic BFS over
/// lexicographically sorted out-edges so witness paths are reproducible
/// across runs and languages; first discovery wins, matching the
/// original Python semantics.
#[pyfunction]
fn reachable(
    edges: Vec<Edge>,
    src: String,
    through_barriers: bool,
) -> HashMap<String, Vec<String>> {
    // frob:doc docs/strata/kernel.md#strata-core
    let mut outgoing: HashMap<&str, Vec<&Edge>> = HashMap::new();
    for edge in &edges {
        outgoing.entry(edge.1.as_str()).or_default().push(edge);
    }
    for out in outgoing.values_mut() {
        out.sort_by(|a, b| a.0.cmp(&b.0));
    }

    let mut paths: HashMap<String, Vec<String>> = HashMap::new();
    paths.insert(src.clone(), vec![src.clone()]);
    let mut frontier: VecDeque<String> = VecDeque::new();
    frontier.push_back(src);
    while let Some(current) = frontier.pop_front() {
        let base = paths.get(&current).cloned().unwrap_or_default();
        if let Some(outs) = outgoing.get(current.as_str()) {
            for edge in outs {
                if !through_barriers && edge.3 {
                    continue; // barrier stops taint
                }
                if !paths.contains_key(&edge.2) {
                    let mut path = base.clone();
                    path.push(edge.0.clone());
                    path.push(edge.2.clone());
                    paths.insert(edge.2.clone(), path);
                    frontier.push_back(edge.2.clone());
                }
            }
        }
    }
    paths
}

/// One age-carrying edge: (flow_id, src, dst, age_seconds).
type AgedEdge = (String, String, String, f64);

fn worst_age_visit(
    node: &str,
    incoming: &HashMap<&str, Vec<&AgedEdge>>,
    active: &mut HashSet<String>,
    best: &mut HashMap<String, (f64, Vec<String>)>,
) -> (f64, Vec<String>) {
    if active.contains(node) {
        return (f64::INFINITY, vec![node.to_string()]);
    }
    if let Some(found) = best.get(node) {
        return found.clone();
    }
    let mut worst: (f64, Vec<String>) = (0.0, vec![node.to_string()]);
    active.insert(node.to_string());
    if let Some(edges) = incoming.get(node) {
        for edge in edges {
            let (up_age, up_path) = worst_age_visit(&edge.1, incoming, active, best);
            let total = up_age + edge.3;
            if total > worst.0 {
                let mut path = up_path;
                path.push(edge.0.clone());
                path.push(node.to_string());
                worst = (total, path);
            }
        }
    }
    active.remove(node);
    best.insert(node.to_string(), worst.clone());
    worst
}

/// BIND: worst_age
///
/// WHY: worst-case staleness is a longest-path problem re-run for every
/// AGE bound; memoized DFS with an active set so a positive-age cycle
/// yields +inf plus the cycle witness instead of nontermination or a
/// silent clamp.
#[pyfunction]
fn worst_age(edges: Vec<AgedEdge>, target: String) -> (f64, Vec<String>) {
    // frob:doc docs/strata/kernel.md#strata-core
    let mut incoming: HashMap<&str, Vec<&AgedEdge>> = HashMap::new();
    for edge in &edges {
        incoming.entry(edge.2.as_str()).or_default().push(edge);
    }
    for ins in incoming.values_mut() {
        ins.sort_by(|a, b| a.0.cmp(&b.0));
    }
    let mut active: HashSet<String> = HashSet::new();
    let mut best: HashMap<String, (f64, Vec<String>)> = HashMap::new();
    worst_age_visit(&target, &incoming, &mut active, &mut best)
}

/// BIND: demand
///
/// WHY: inbound-rate aggregation is trivial today but sits on the same
/// hot path as the closures and grows fanout/skew multipliers in phase 2;
/// keeping every propagation kernel on one side of the boundary avoids a
/// Python/Rust split of the arithmetic later.
#[pyfunction]
fn demand(rates: Vec<(String, f64)>, node: String) -> f64 {
    // frob:doc docs/strata/kernel.md#strata-core
    rates
        .iter()
        .filter(|(dst, _)| *dst == node)
        .map(|(_, rate)| rate)
        .sum()
}

/// BIND: parse_source
///
/// WHY: the surface grammar parser is compute-heavy (charter D3, amended
/// 2026-07-17) so it lives here; the JSON string is the narrowest
/// possible boundary back to the Python validators in `frob.strata._ast`.
#[pyfunction]
fn parse_source(text: &str) -> String {
    // frob:doc docs/strata/surface.md#parser
    parse::parse_source_impl(text)
}

#[pymodule]
fn strata_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // frob:doc docs/strata/kernel.md#strata-core
    m.add_function(wrap_pyfunction!(reachable, m)?)?;
    m.add_function(wrap_pyfunction!(worst_age, m)?)?;
    m.add_function(wrap_pyfunction!(demand, m)?)?;
    m.add_function(wrap_pyfunction!(parse_source, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn edge(f: &str, s: &str, d: &str, barrier: bool) -> Edge {
        (f.to_string(), s.to_string(), d.to_string(), barrier)
    }

    #[test]
    fn reachable_returns_witness_paths() {
        // frob:tests strata-core/src/lib.rs::reachable kind="unit"
        // frob:tests strata-core/src/lib.rs::strata_core kind="unit"
        let paths = reachable(
            vec![edge("f1", "a", "b", false), edge("f2", "b", "c", false)],
            "a".to_string(),
            false,
        );
        assert_eq!(paths["c"], vec!["a", "f1", "b", "f2", "c"]);
    }

    #[test]
    fn barriers_stop_taint_unless_asked() {
        // frob:tests strata-core/src/lib.rs::reachable kind="unit"
        let edges = vec![edge("f1", "evil", "api", true)];
        assert!(!reachable(edges.clone(), "evil".to_string(), false).contains_key("api"));
        assert!(reachable(edges, "evil".to_string(), true).contains_key("api"));
    }

    #[test]
    fn worst_age_takes_the_stalest_path() {
        // frob:tests strata-core/src/lib.rs::worst_age kind="unit"
        let (age, path) = worst_age(
            vec![
                ("f1".into(), "truth".into(), "replica".into(), 300.0),
                ("f2".into(), "replica".into(), "view".into(), 30.0),
                ("f3".into(), "truth".into(), "view".into(), 0.0),
            ],
            "view".to_string(),
        );
        assert_eq!(age, 330.0);
        assert_eq!(path, vec!["truth", "f1", "replica", "f2", "view"]);
    }

    #[test]
    fn worst_age_is_infinite_on_positive_cycles() {
        // frob:tests strata-core/src/lib.rs::worst_age kind="unit"
        let (age, _) = worst_age(
            vec![
                ("f1".into(), "a".into(), "b".into(), 1.0),
                ("f2".into(), "b".into(), "a".into(), 1.0),
            ],
            "a".to_string(),
        );
        assert!(age.is_infinite());
    }

    #[test]
    fn demand_sums_only_the_target_node() {
        // frob:tests strata-core/src/lib.rs::demand kind="unit"
        let total = demand(
            vec![("api".into(), 100.0), ("api".into(), 2.0), ("db".into(), 9.0)],
            "api".to_string(),
        );
        assert_eq!(total, 102.0);
    }
}
