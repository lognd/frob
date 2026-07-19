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
/// (flow_id, src, dst, barrier, transitive) where `barrier` marks a flow
/// carrying any endorse/declassify boundary (a declared trust/label change
/// point), and `transitive` marks whether the edge may be used as a MIDDLE
/// link in a longer chain (`_facts.py::FactBase.reachable` only emits
/// `false` for flows explicitly marked non-transitive, e.g. `std.krb`'s
/// non-transitive domain trusts, docs/strata/krb.md#domain-trust-lattice).
/// A non-transitive edge can still be the LAST hop of a path (its `dst` is
/// reachable), it just cannot be extended past -- see `reachable`'s BFS
/// below, which only enqueues a node for further expansion when it was
/// reached via a transitive edge.
type Edge = (String, String, String, bool, bool);

/// BIND: reachable
///
/// WHY: the influence closure is the single hottest operation in the
/// prover -- every noflow/reach claim walks it. Deterministic BFS over
/// lexicographically sorted out-edges so witness paths are reproducible
/// across runs and languages; first discovery wins, matching the
/// original Python semantics. A non-transitive edge (`edge.4 == false`,
/// docs/strata/kernel.md#strata-core) is a TERMINAL hop: its destination is
/// discovered (added to `paths`) but never enqueued into `frontier`, so no
/// further edge can chain off it -- this is the fix for T-0282/T-0262's
/// disclosed gap where a chain of non-transitive trusts wrongly reached as
/// far as a chain of transitive ones.
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
                    if edge.4 {
                        // Transitive: dst may extend the chain further.
                        frontier.push_back(edge.2.clone());
                    }
                    // Non-transitive: dst is reached (an endpoint) but is
                    // NOT enqueued -- it cannot become a middle link.
                }
            }
        }
    }
    paths
}

/// One age-carrying edge: (flow_id, src, dst, age_seconds).
type AgedEdge = (String, String, String, f64);

/// Depth-first search for a cycle through `start` (following forward
/// out-edges) whose accumulated age is strictly positive. Returns the cycle
/// witness (node/flow ids from `start` back to `start`) when found.
fn find_positive_cycle(
    start: &str,
    node: &str,
    acc: f64,
    outgoing: &HashMap<&str, Vec<&AgedEdge>>,
    active: &mut HashSet<String>,
    path: &mut Vec<String>,
) -> Option<Vec<String>> {
    active.insert(node.to_string());
    if let Some(edges) = outgoing.get(node) {
        for edge in edges {
            let next_acc = acc + edge.3;
            if edge.2 == start {
                if next_acc > 0.0 {
                    let mut witness = path.clone();
                    witness.push(edge.0.clone());
                    witness.push(start.to_string());
                    active.remove(node);
                    return Some(witness);
                }
                continue; // zero/negative-net return to start: not this cycle
            }
            if !active.contains(edge.2.as_str()) {
                path.push(edge.0.clone());
                path.push(edge.2.clone());
                if let Some(found) =
                    find_positive_cycle(start, &edge.2, next_acc, outgoing, active, path)
                {
                    return Some(found);
                }
                path.pop();
                path.pop();
            }
        }
    }
    active.remove(node);
    None
}

/// Whether any positive-age cycle exists that can reach `target` -- the
/// unbounded-staleness case (docs/strata/kernel.md#age-propagation-
/// semantics). Only nodes already known to reach `target` need be tried as
/// cycle starting points: if `start` is on a positive cycle and `start`
/// itself reaches `target`, the whole cycle reaches `target`.
fn has_positive_cycle_reaching(
    can_reach_target: &HashSet<String>,
    outgoing: &HashMap<&str, Vec<&AgedEdge>>,
) -> Option<Vec<String>> {
    let mut starts: Vec<&String> = can_reach_target.iter().collect();
    starts.sort();
    for start in starts {
        let mut active: HashSet<String> = HashSet::new();
        let mut path: Vec<String> = vec![start.clone()];
        if let Some(witness) =
            find_positive_cycle(start, start, 0.0, outgoing, &mut active, &mut path)
        {
            return Some(witness);
        }
    }
    None
}

/// Tarjan's SCC algorithm, one node at a time (small graphs only; the
/// caller bounds node counts). `outgoing` edges must already be sorted by
/// flow id so traversal order -- and therefore scc-id assignment -- is
/// reproducible across runs (T-0065 reviewer round: the earlier
/// memoized-DFS `worst_age` was rejected for exactly this kind of
/// context-dependent nondeterminism, so every helper here is deterministic
/// by construction, not by accident).
#[allow(clippy::too_many_arguments)]
fn strongconnect(
    v: &str,
    outgoing: &HashMap<&str, Vec<&AgedEdge>>,
    index_counter: &mut usize,
    stack: &mut Vec<String>,
    on_stack: &mut HashSet<String>,
    indices: &mut HashMap<String, usize>,
    lowlink: &mut HashMap<String, usize>,
    scc_id: &mut HashMap<String, usize>,
    scc_counter: &mut usize,
) {
    indices.insert(v.to_string(), *index_counter);
    lowlink.insert(v.to_string(), *index_counter);
    *index_counter += 1;
    stack.push(v.to_string());
    on_stack.insert(v.to_string());

    if let Some(edges) = outgoing.get(v) {
        for edge in edges {
            let w = edge.2.as_str();
            if !indices.contains_key(w) {
                strongconnect(
                    w, outgoing, index_counter, stack, on_stack, indices, lowlink, scc_id,
                    scc_counter,
                );
                let wl = lowlink[w];
                let vl = lowlink[v];
                lowlink.insert(v.to_string(), vl.min(wl));
            } else if on_stack.contains(w) {
                let wi = indices[w];
                let vl = lowlink[v];
                lowlink.insert(v.to_string(), vl.min(wi));
            }
        }
    }

    if lowlink[v] == indices[v] {
        loop {
            let w = stack.pop().expect("strongconnect: scc stack underflow");
            on_stack.remove(&w);
            scc_id.insert(w.clone(), *scc_counter);
            if w == v {
                break;
            }
        }
        *scc_counter += 1;
    }
}

/// Partition `nodes` into strongly connected components; node ids visited
/// in sorted order for determinism. Returns node id -> scc id (scc ids are
/// not in any particular order; callers topologically sort separately).
fn compute_sccs(
    nodes: &[String],
    outgoing: &HashMap<&str, Vec<&AgedEdge>>,
) -> HashMap<String, usize> {
    let mut sorted_nodes = nodes.to_vec();
    sorted_nodes.sort();
    sorted_nodes.dedup();
    let mut index_counter = 0usize;
    let mut stack: Vec<String> = Vec::new();
    let mut on_stack: HashSet<String> = HashSet::new();
    let mut indices: HashMap<String, usize> = HashMap::new();
    let mut lowlink: HashMap<String, usize> = HashMap::new();
    let mut scc_id: HashMap<String, usize> = HashMap::new();
    let mut scc_counter = 0usize;
    for v in &sorted_nodes {
        if !indices.contains_key(v.as_str()) {
            strongconnect(
                v,
                outgoing,
                &mut index_counter,
                &mut stack,
                &mut on_stack,
                &mut indices,
                &mut lowlink,
                &mut scc_id,
                &mut scc_counter,
            );
        }
    }
    scc_id
}

/// Deterministic BFS for a path between two nodes known to share an SCC.
/// Sound only when every intra-SCC edge is 0-weight, which is guaranteed
/// once `has_positive_cycle_reaching` finds nothing (docs/strata/kernel.md
/// #age-propagation-semantics): any intra-SCC edge lies on a cycle, so a
/// positive one would already have triggered the `+inf` case. Used only to
/// stitch together the witness path; never to compute the age itself.
fn zero_weight_path(
    from: &str,
    to: &str,
    scc_id: &HashMap<String, usize>,
    outgoing: &HashMap<&str, Vec<&AgedEdge>>,
) -> Vec<String> {
    if from == to {
        return vec![from.to_string()];
    }
    let scc = scc_id[from];
    let mut prev: HashMap<String, (String, String)> = HashMap::new();
    let mut visited: HashSet<String> = HashSet::new();
    visited.insert(from.to_string());
    let mut frontier: VecDeque<String> = VecDeque::new();
    frontier.push_back(from.to_string());
    while let Some(cur) = frontier.pop_front() {
        if cur == to {
            break;
        }
        if let Some(edges) = outgoing.get(cur.as_str()) {
            for edge in edges {
                if scc_id.get(edge.2.as_str()) != Some(&scc) {
                    continue;
                }
                if !visited.contains(&edge.2) {
                    visited.insert(edge.2.clone());
                    prev.insert(edge.2.clone(), (edge.0.clone(), cur.clone()));
                    frontier.push_back(edge.2.clone());
                }
            }
        }
    }
    let mut path: Vec<String> = vec![to.to_string()];
    let mut cur = to.to_string();
    while cur != from {
        let (flow_id, prev_node) = prev
            .get(&cur)
            .expect("zero_weight_path: unreachable within the same SCC");
        path.push(flow_id.clone());
        path.push(prev_node.clone());
        cur = prev_node.clone();
    }
    path.reverse();
    path
}

/// BIND: worst_age
///
/// WHY: worst-case staleness is a longest-path problem re-run for every AGE
/// bound. T-0065 reviewer round: an earlier memoized-DFS attempt was
/// REJECTED for unsoundness -- `best[node]` computed under one caller's
/// active-set was reused by a caller with a different active-set, silently
/// undercounting the true longest simple path (verified counterexample:
/// edges B->A, B->T, A->T(3), A->B, C->B(1) with target T; the memoized
/// version returned 3.0 via A->T while the true worst case is 4.0 via
/// C->B->A->T). The provably-correct replacement: with non-negative ages
/// (`_facts.py` fails closed on negative age/rate/size), any intra-SCC edge
/// lies on a cycle, so it must be 0-weight once no positive-age cycle
/// reaches `target` (the pre-pass below is unchanged and still handles that
/// case, returning `+inf` with the cycle witness). Condensing to SCCs and
/// running longest-path DP over the resulting DAG in topological order is
/// then exact -- no caller-context-dependent memoization anywhere.
#[pyfunction]
fn worst_age(edges: Vec<AgedEdge>, target: String) -> (f64, Vec<String>) {
    // frob:doc docs/strata/kernel.md#strata-core
    let mut incoming: HashMap<&str, Vec<&AgedEdge>> = HashMap::new();
    let mut outgoing: HashMap<&str, Vec<&AgedEdge>> = HashMap::new();
    for edge in &edges {
        incoming.entry(edge.2.as_str()).or_default().push(edge);
        outgoing.entry(edge.1.as_str()).or_default().push(edge);
    }
    for ins in incoming.values_mut() {
        ins.sort_by(|a, b| a.0.cmp(&b.0));
    }
    for outs in outgoing.values_mut() {
        outs.sort_by(|a, b| a.0.cmp(&b.0));
    }

    // Nodes that can reach `target` via forward edges (predecessor closure).
    let mut can_reach_target: HashSet<String> = HashSet::new();
    can_reach_target.insert(target.clone());
    let mut frontier: VecDeque<String> = VecDeque::new();
    frontier.push_back(target.clone());
    while let Some(cur) = frontier.pop_front() {
        if let Some(edges_in) = incoming.get(cur.as_str()) {
            for edge in edges_in {
                if can_reach_target.insert(edge.1.clone()) {
                    frontier.push_back(edge.1.clone());
                }
            }
        }
    }

    if let Some(witness) = has_positive_cycle_reaching(&can_reach_target, &outgoing) {
        return (f64::INFINITY, witness);
    }

    // Restrict to nodes that can reach `target` -- sufficient and closed
    // (any edge whose dst is in this set has its src in it too, by
    // construction of the backward BFS above).
    let r_nodes: Vec<String> = can_reach_target.iter().cloned().collect();
    let r_outgoing: HashMap<&str, Vec<&AgedEdge>> = outgoing
        .iter()
        .filter(|(k, _)| can_reach_target.contains(**k))
        .map(|(k, v)| {
            (
                *k,
                v.iter()
                    .filter(|e| can_reach_target.contains(&e.2))
                    .copied()
                    .collect::<Vec<&AgedEdge>>(),
            )
        })
        .collect();

    let scc_id = compute_sccs(&r_nodes, &r_outgoing);
    let num_sccs = scc_id.values().copied().max().map(|m| m + 1).unwrap_or(0);

    // Condensation edges (inter-SCC only -- intra-SCC edges are 0-weight
    // and folded into `zero_weight_path` for witness reconstruction),
    // grouped by destination SCC and sorted by flow id for determinism.
    let mut incoming_by_scc: Vec<Vec<(usize, f64, String, String, String)>> =
        vec![Vec::new(); num_sccs]; // (src_scc, weight, u_node, flow_id, v_node)
    let mut indegree: Vec<usize> = vec![0; num_sccs];
    let mut scc_out: Vec<Vec<usize>> = vec![Vec::new(); num_sccs];
    let mut seen_pair: HashSet<(usize, usize)> = HashSet::new();
    for (u, edges_out) in &r_outgoing {
        let u_scc = scc_id[*u];
        for edge in edges_out {
            let v_scc = scc_id[&edge.2];
            if u_scc == v_scc {
                continue;
            }
            incoming_by_scc[v_scc].push((
                u_scc,
                edge.3,
                edge.1.clone(),
                edge.0.clone(),
                edge.2.clone(),
            ));
            if seen_pair.insert((u_scc, v_scc)) {
                indegree[v_scc] += 1;
                scc_out[u_scc].push(v_scc);
            }
        }
    }
    for lst in incoming_by_scc.iter_mut() {
        lst.sort_by(|a, b| a.3.cmp(&b.3));
    }
    for lst in scc_out.iter_mut() {
        lst.sort();
    }

    // Kahn's topological sort over the condensation DAG (small graphs;
    // O(V^2) is fine at this scale).
    let mut remaining = indegree.clone();
    let mut processed = vec![false; num_sccs];
    let mut topo: Vec<usize> = Vec::new();
    while topo.len() < num_sccs {
        let next = (0..num_sccs)
            .find(|i| !processed[*i] && remaining[*i] == 0)
            .expect("worst_age: condensation of a DAG must have a zero-indegree scc");
        processed[next] = true;
        topo.push(next);
        for &v in &scc_out[next] {
            remaining[v] -= 1;
        }
    }

    // Longest-path DP over the condensation DAG in topological order.
    let mut dist: Vec<f64> = vec![0.0; num_sccs];
    let mut chosen: Vec<Option<(String, String, String)>> = vec![None; num_sccs];
    for &scc in &topo {
        let mut best = 0.0;
        let mut best_edge: Option<(String, String, String)> = None;
        for (u_scc, weight, u_node, flow_id, v_node) in &incoming_by_scc[scc] {
            let total = dist[*u_scc] + weight;
            if total > best {
                best = total;
                best_edge = Some((u_node.clone(), flow_id.clone(), v_node.clone()));
            }
        }
        dist[scc] = best;
        chosen[scc] = best_edge;
    }

    let target_scc = scc_id[target.as_str()];
    let age = dist[target_scc];

    // Reconstruct the witness: walk the chosen-edge chain backward from
    // target's SCC to a root (dist 0, no chosen edge), then stitch the
    // inter-SCC hops together with zero-weight intra-SCC BFS segments.
    let mut chain: Vec<(String, String, String)> = Vec::new();
    let mut cur_scc = target_scc;
    while let Some((u_node, flow_id, v_node)) = chosen[cur_scc].clone() {
        cur_scc = scc_id[u_node.as_str()];
        chain.push((u_node, flow_id, v_node));
    }
    chain.reverse();

    if chain.is_empty() {
        return (age, vec![target.clone()]);
    }

    let mut path: Vec<String> = vec![chain[0].0.clone()];
    let mut cursor = chain[0].0.clone();
    for (u_node, flow_id, v_node) in &chain {
        let bridge = zero_weight_path(&cursor, u_node, &scc_id, &r_outgoing);
        path.extend(bridge.into_iter().skip(1));
        path.push(flow_id.clone());
        path.push(v_node.clone());
        cursor = v_node.clone();
    }
    let tail = zero_weight_path(&cursor, &target, &scc_id, &r_outgoing);
    path.extend(tail.into_iter().skip(1));

    (age, path)
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

/// One demand-carrying edge: (flow_id, src, dst, declared_rate, fanout).
/// `declared_rate` is `None` when the flow has no declared rate (demand
/// must propagate upstream through it); `fanout` is 1.0 when the flow
/// declares no `fanout` attr.
type DemandEdge = (String, String, String, Option<f64>, f64);

/// Recursive demand computation with cycle detection via an explicit
/// active-recursion stack (mirrors `find_positive_cycle`'s pattern, but
/// SUM-aggregates instead of taking a single accumulated value, since
/// load adds across converging paths -- unlike age, which maxes).
///
/// `incoming_undeclared[node]` are `(flow_id, src, fanout)` triples for
/// flows into `node` with no declared rate (demand recurses into `src`);
/// `incoming_declared[node]` are `(flow_id, src, contribution)` triples
/// where `contribution = declared_rate * fanout` is a constant, computed
/// once and never recursed into (a declared rate terminates propagation
/// on that hop, docs/strata/kernel.md#capacity-semantics).
///
/// `Err` carries the witness path of a cycle that both (a) lies entirely
/// on flows without declared rates and (b) is reachable, forward, from
/// some node with a declared outbound rate (`reach`) -- the documented v0
/// unboundedness rule.
#[allow(clippy::too_many_arguments)]
fn compute_demand(
    node: &str,
    incoming_undeclared: &HashMap<String, Vec<(String, String, f64)>>,
    incoming_declared: &HashMap<String, Vec<(String, String, f64)>>,
    reach: &HashSet<String>,
    memo: &mut HashMap<String, f64>,
    active: &mut Vec<String>,
) -> Result<f64, Vec<String>> {
    if let Some(v) = memo.get(node) {
        return Ok(*v);
    }
    active.push(node.to_string());
    let mut total = 0.0;
    if let Some(consts) = incoming_declared.get(node) {
        let mut sorted = consts.clone();
        sorted.sort_by(|a, b| a.0.cmp(&b.0));
        for (_, _, contribution) in sorted {
            total += contribution;
        }
    }
    if let Some(ins) = incoming_undeclared.get(node) {
        let mut sorted = ins.clone();
        sorted.sort_by(|a, b| a.0.cmp(&b.0));
        for (flow_id, src, fanout) in sorted {
            if let Some(pos) = active.iter().position(|n| n == &src) {
                let cycle_reaches_source = active[pos..].iter().any(|n| reach.contains(n))
                    || reach.contains(node);
                if !cycle_reaches_source {
                    continue; // cycle with no rate feeding it: contributes 0
                }
                let mut witness: Vec<String> = active[pos..].to_vec();
                witness.push(flow_id);
                witness.push(node.to_string());
                active.pop();
                return Err(witness);
            }
            match compute_demand(&src, incoming_undeclared, incoming_declared, reach, memo, active)
            {
                Ok(v) => total += v * fanout,
                Err(w) => {
                    active.pop();
                    return Err(w);
                }
            }
        }
    }
    active.pop();
    memo.insert(node.to_string(), total);
    Ok(total)
}

/// BIND: propagated_demand
///
/// WHY: fanout multiplies demand as it propagates along a flow (charter
/// docs/strata/kernel.md#capacity-semantics); unlike `worst_age`, which
/// maxes over paths, demand SUMS over converging paths (load adds). A
/// declared flow `rate` terminates propagation on that hop -- it does not
/// recurse into its source's own demand. Positive-rate cycles (a cycle of
/// undeclared-rate flows reachable, forward, from a node with a declared
/// outbound rate, and which also reaches `target`) are unbounded: `+inf`
/// with the cycle as witness, never a silent clamp (deny-by-default,
/// charter law 2).
#[pyfunction]
fn propagated_demand(edges: Vec<DemandEdge>, target: String) -> (f64, Vec<String>) {
    // frob:doc docs/strata/kernel.md#capacity-semantics
    let mut outgoing_all: HashMap<String, Vec<String>> = HashMap::new();
    let mut rate_sources: HashSet<String> = HashSet::new();
    let mut incoming_undeclared: HashMap<String, Vec<(String, String, f64)>> = HashMap::new();
    let mut incoming_declared: HashMap<String, Vec<(String, String, f64)>> = HashMap::new();
    for (flow_id, src, dst, rate, fanout) in &edges {
        outgoing_all.entry(src.clone()).or_default().push(dst.clone());
        match rate {
            Some(r) => {
                rate_sources.insert(src.clone());
                incoming_declared
                    .entry(dst.clone())
                    .or_default()
                    .push((flow_id.clone(), src.clone(), r * fanout));
            }
            None => {
                incoming_undeclared
                    .entry(dst.clone())
                    .or_default()
                    .push((flow_id.clone(), src.clone(), *fanout));
            }
        }
    }

    // Forward closure from every declared-rate source: the set of nodes a
    // rate can reach, used to decide whether a cycle is fed (see above).
    let mut reach: HashSet<String> = HashSet::new();
    let mut sources: Vec<&String> = rate_sources.iter().collect();
    sources.sort();
    let mut frontier: VecDeque<String> = VecDeque::new();
    for s in sources {
        if reach.insert(s.clone()) {
            frontier.push_back(s.clone());
        }
    }
    while let Some(cur) = frontier.pop_front() {
        if let Some(outs) = outgoing_all.get(&cur) {
            let mut sorted = outs.clone();
            sorted.sort();
            for n in sorted {
                if reach.insert(n.clone()) {
                    frontier.push_back(n);
                }
            }
        }
    }

    let mut memo: HashMap<String, f64> = HashMap::new();
    let mut active: Vec<String> = Vec::new();
    match compute_demand(
        &target,
        &incoming_undeclared,
        &incoming_declared,
        &reach,
        &mut memo,
        &mut active,
    ) {
        Ok(v) => (v, vec![target]),
        Err(witness) => (f64::INFINITY, witness),
    }
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
    m.add_function(wrap_pyfunction!(propagated_demand, m)?)?;
    m.add_function(wrap_pyfunction!(parse_source, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn edge(f: &str, s: &str, d: &str, barrier: bool) -> Edge {
        (f.to_string(), s.to_string(), d.to_string(), barrier, true)
    }

    fn nontransitive_edge(f: &str, s: &str, d: &str) -> Edge {
        (f.to_string(), s.to_string(), d.to_string(), false, false)
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
    fn non_transitive_edge_is_a_terminal_hop() {
        // frob:tests strata-core/src/lib.rs::reachable kind="unit"
        //
        // T-0282: a --(non-transitive)--> b --(non-transitive)--> c must
        // reach b (single hop, always correct) but NOT c (chaining past a
        // non-transitive edge is the disclosed gap this ticket fixes).
        let paths = reachable(
            vec![
                nontransitive_edge("f1", "a", "b"),
                nontransitive_edge("f2", "b", "c"),
            ],
            "a".to_string(),
            true,
        );
        assert!(paths.contains_key("b"));
        assert!(!paths.contains_key("c"));
    }

    #[test]
    fn non_transitive_edge_may_still_be_the_final_hop_of_a_mixed_chain() {
        // frob:tests strata-core/src/lib.rs::reachable kind="unit"
        //
        // a --(transitive)--> b --(non-transitive)--> c: c IS reachable
        // (the non-transitive edge is the LAST hop, which is allowed) but
        // nothing past c is, since c was never enqueued.
        let paths = reachable(
            vec![edge("f1", "a", "b", false), nontransitive_edge("f2", "b", "c")],
            "a".to_string(),
            true,
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
    fn worst_age_reviewer_regression_context_dependent_memo() {
        // frob:tests strata-core/src/lib.rs::worst_age kind="unit"
        //
        // T-0065 reviewer round: this exact counterexample was verified
        // against the built extension to REJECT the earlier memoized-DFS
        // `worst_age`. That version returned (3.0, [A, e2, T]) because
        // best[A] was memoized as (0.0, [A]) while B was on the active
        // stack (correctly excluding the A<-B<-C continuation IN THAT
        // CONTEXT), then wrongly reused when A was visited again with B
        // inactive. The true worst case is 4.0 via C -> B -> A -> T. A
        // silent undercount here means an AGE bound claim could be FALSELY
        // PROVED -- the SCC-condensation replacement must get this right.
        let (age, path) = worst_age(
            vec![
                ("e0".into(), "B".into(), "A".into(), 0.0),
                ("e1".into(), "B".into(), "T".into(), 0.0),
                ("e2".into(), "A".into(), "T".into(), 3.0),
                ("e3".into(), "A".into(), "B".into(), 0.0),
                ("e4".into(), "C".into(), "B".into(), 1.0),
            ],
            "T".to_string(),
        );
        assert_eq!(age, 4.0);
        assert_eq!(path, vec!["C", "e4", "B", "e0", "A", "e2", "T"]);
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
    fn propagated_demand_chain_multiplies_fanout() {
        // frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"
        // src(10/s) -> a (fanout 2) -> b (fanout 3): 10 * 2 * 3 = 60.
        let (v, _) = propagated_demand(
            vec![
                ("f1".into(), "src".into(), "a".into(), Some(10.0), 2.0),
                ("f2".into(), "a".into(), "b".into(), None, 3.0),
            ],
            "b".to_string(),
        );
        assert_eq!(v, 60.0);
    }

    #[test]
    fn propagated_demand_sums_converging_paths() {
        // frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"
        // two independent declared sources into the same target: sums.
        let (v, _) = propagated_demand(
            vec![
                ("f1".into(), "s1".into(), "t".into(), Some(4.0), 1.0),
                ("f2".into(), "s2".into(), "t".into(), Some(6.0), 1.0),
            ],
            "t".to_string(),
        );
        assert_eq!(v, 10.0);
    }

    #[test]
    fn propagated_demand_positive_cycle_is_infinite() {
        // frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"
        // src feeds a, a<->b cycle (both undeclared), b is the target.
        let (v, witness) = propagated_demand(
            vec![
                ("f0".into(), "src".into(), "a".into(), Some(5.0), 1.0),
                ("f1".into(), "a".into(), "b".into(), None, 1.0),
                ("f2".into(), "b".into(), "a".into(), None, 1.0),
            ],
            "b".to_string(),
        );
        assert!(v.is_infinite());
        assert!(witness.contains(&"a".to_string()));
        assert!(witness.contains(&"b".to_string()));
    }

    #[test]
    fn propagated_demand_unfed_cycle_contributes_zero() {
        // frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"
        // a<->b cycle with no declared rate anywhere reaching it: 0, finite.
        let (v, _) = propagated_demand(
            vec![
                ("f1".into(), "a".into(), "b".into(), None, 1.0),
                ("f2".into(), "b".into(), "a".into(), None, 1.0),
            ],
            "b".to_string(),
        );
        assert_eq!(v, 0.0);
    }

    #[test]
    fn demand_sums_only_the_target_node() {
        // frob:tests strata-core/src/lib.rs::demand kind="unit"
        let total = demand(
            vec![
                ("api".into(), 100.0),
                ("api".into(), 2.0),
                ("db".into(), 9.0),
            ],
            "api".to_string(),
        );
        assert_eq!(total, 102.0);
    }
}
