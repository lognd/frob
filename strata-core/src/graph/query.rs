//! Bidirectional closure, reachability, and cycle detection over a `Graph`
//! (docs/strata/graph.md). T-3004 section 2's four closure rules are the
//! reason this kernel exists; these queries are what makes expressing them
//! cheap for a consumer (T-3006/T-3007, deferred) -- the rules themselves
//! stay out of this crate, only the traversal primitives live here.

use super::model::{Edge, Graph, Kind, NodeId};
use std::collections::{BTreeSet, VecDeque};

/// Which edges a traversal or cycle search should follow: every edge in the
/// graph, or only edges whose kind is in the given set. Generic over kind
/// names on purpose (same "caller supplies the vocabulary" rule as
/// `GraphSchema`).
pub enum KindFilter<'a> {
    /// Follow every edge regardless of kind.
    Any,
    /// Follow only edges whose kind is a member of this set.
    Only(&'a BTreeSet<Kind>),
}

impl<'a> KindFilter<'a> {
    fn allows(&self, kind: &str) -> bool {
        match self {
            KindFilter::Any => true,
            KindFilter::Only(set) => set.contains(kind),
        }
    }
}

fn matching_edges<'g, 'f>(
    edges: &'g [Edge],
    filter: &'f KindFilter,
) -> impl Iterator<Item = &'g Edge> + use<'g, 'f> {
    edges.iter().filter(move |e| filter.allows(&e.kind))
}

impl Graph {
    /// Every node reachable from `start` by following matching edges
    /// FORWARD (src -> dst), zero or more hops. `start` itself is included
    /// only if a cycle routes back to it. Empty result (aside from
    /// unreached start) means nothing is reachable -- the negative case a
    /// closure query must be able to produce as readily as the positive one.
    pub fn forward_closure(&self, start: &str, filter: &KindFilter) -> BTreeSet<NodeId> {
        self.closure(start, filter, true)
    }

    /// Every node that can reach `start` by following matching edges
    /// BACKWARD (dst -> src), zero or more hops -- the other half of
    /// "bidirectional closure" (T-3004 section 2's closure rules are
    /// checked in both directions).
    pub fn backward_closure(&self, start: &str, filter: &KindFilter) -> BTreeSet<NodeId> {
        self.closure(start, filter, false)
    }

    fn closure(&self, start: &str, filter: &KindFilter, forward: bool) -> BTreeSet<NodeId> {
        let mut seen: BTreeSet<NodeId> = BTreeSet::new();
        let mut queue: VecDeque<NodeId> = VecDeque::new();
        queue.push_back(start.to_string());
        seen.insert(start.to_string());

        while let Some(cur) = queue.pop_front() {
            for edge in matching_edges(&self.edges(), filter) {
                let (from, to) = if forward {
                    (&edge.src, &edge.dst)
                } else {
                    (&edge.dst, &edge.src)
                };
                if from == &cur && !seen.contains(to) {
                    seen.insert(to.clone());
                    queue.push_back(to.clone());
                }
            }
        }
        seen.remove(start);
        seen
    }

    /// True if `to` is reachable from `from` by following matching edges
    /// forward, zero or more hops (a node reaches itself trivially).
    pub fn reachable(&self, from: &str, to: &str, filter: &KindFilter) -> bool {
        if from == to {
            return true;
        }
        self.forward_closure(from, filter).contains(to)
    }

    /// Find one cycle among matching edges, if any exists, as the ordered
    /// list of node ids forming it (first id repeated as the last to make
    /// the loop explicit). `None` means the matching subgraph is acyclic.
    ///
    /// WHY a returned witness, not just a bool: this repo has shipped a
    /// cycle checker that found a planted cycle in one layout and missed
    /// the identical one in another (docs/guides/agent-playbook.md sec on
    /// positive controls) -- a witness path is checkable by a test, a bare
    /// bool is not.
    pub fn find_cycle(&self, filter: &KindFilter) -> Option<Vec<NodeId>> {
        #[derive(Clone, Copy, PartialEq, Eq)]
        enum Mark {
            Visiting,
            Done,
        }
        use std::collections::HashMap;

        let mut mark: HashMap<NodeId, Mark> = HashMap::new();
        let mut stack: Vec<NodeId> = Vec::new();

        fn adj<'g>(graph: &'g Graph, node: &str, filter: &KindFilter) -> Vec<&'g NodeId> {
            matching_edges(graph.edges(), filter)
                .filter(|e| e.src == node)
                .map(|e| &e.dst)
                .collect()
        }

        fn visit(
            graph: &Graph,
            node: &NodeId,
            filter: &KindFilter,
            mark: &mut HashMap<NodeId, Mark>,
            stack: &mut Vec<NodeId>,
        ) -> Option<Vec<NodeId>> {
            mark.insert(node.clone(), Mark::Visiting);
            stack.push(node.clone());

            for next in adj(graph, node, filter) {
                match mark.get(next) {
                    Some(Mark::Visiting) => {
                        let start_idx = stack.iter().position(|n| n == next).unwrap();
                        let mut cycle: Vec<NodeId> = stack[start_idx..].to_vec();
                        cycle.push(next.clone());
                        return Some(cycle);
                    }
                    Some(Mark::Done) => continue,
                    None => {
                        if let Some(cycle) = visit(graph, next, filter, mark, stack) {
                            return Some(cycle);
                        }
                    }
                }
            }

            stack.pop();
            mark.insert(node.clone(), Mark::Done);
            None
        }

        let ids: Vec<NodeId> = self.node_ids().cloned().collect();
        for id in ids {
            if mark.get(&id).is_none() {
                if let Some(cycle) = visit(self, &id, filter, &mut mark, &mut stack) {
                    return Some(cycle);
                }
            }
        }
        None
    }

    /// True if any cycle exists among matching edges.
    // frob:ticket T-3120
    // frob:tests strata-core/src/graph/query.rs::tests.has_cycle_true_on_a_planted_cycle
    // frob:tests strata-core/src/graph/query.rs::tests.has_cycle_false_on_an_acyclic_graph
    pub fn has_cycle(&self, filter: &KindFilter) -> bool {
        self.find_cycle(filter).is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::model::{EdgeKindSchema, GraphSchema, LevelRelation};
    use std::collections::BTreeSet;

    fn chain_schema() -> GraphSchema {
        let mut s = GraphSchema::new();
        s.declare_node_kind("thing");
        s.declare_edge_kind(
            "refines",
            EdgeKindSchema {
                allowed_src_kinds: BTreeSet::new(),
                allowed_dst_kinds: BTreeSet::new(),
                level_relation: LevelRelation::Any,
                required_attrs: BTreeSet::new(),
            },
        );
        s.declare_edge_kind("decides", EdgeKindSchema::unconstrained());
        s
    }

    #[test]
    // frob:ticket T-3005
    fn forward_closure_finds_transitive_targets() {
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c", "d"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        // d is disconnected -- must NOT show up (the negative case).
        let closure = g.forward_closure("a", &KindFilter::Any);
        assert_eq!(closure, BTreeSet::from(["b".to_string(), "c".to_string()]));
    }

    #[test]
    // frob:ticket T-3005
    fn forward_closure_is_empty_for_a_sink() {
        let mut g = Graph::new(chain_schema());
        g.add_node("a", "thing", None).unwrap();
        g.add_node("b", "thing", None).unwrap();
        g.add_edge("refines", "a", "b").unwrap();
        // b has no outgoing edges: closure from b must be empty, not "closed".
        assert!(g.forward_closure("b", &KindFilter::Any).is_empty());
    }

    #[test]
    // frob:ticket T-3005
    fn backward_closure_finds_transitive_sources() {
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        let closure = g.backward_closure("c", &KindFilter::Any);
        assert_eq!(closure, BTreeSet::from(["a".to_string(), "b".to_string()]));
    }

    #[test]
    // frob:ticket T-3005
    fn kind_filter_excludes_non_matching_edges() {
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("decides", "b", "c").unwrap();
        let only_refines = BTreeSet::from(["refines".to_string()]);
        let closure = g.forward_closure("a", &KindFilter::Only(&only_refines));
        // c is reachable only via a "decides" edge, which the filter excludes.
        assert_eq!(closure, BTreeSet::from(["b".to_string()]));
    }

    #[test]
    // frob:ticket T-3005
    fn reachable_true_for_connected_pair() {
        let mut g = Graph::new(chain_schema());
        g.add_node("a", "thing", None).unwrap();
        g.add_node("b", "thing", None).unwrap();
        g.add_edge("refines", "a", "b").unwrap();
        assert!(g.reachable("a", "b", &KindFilter::Any));
    }

    #[test]
    // frob:ticket T-3005
    fn reachable_false_for_disconnected_pair() {
        let mut g = Graph::new(chain_schema());
        g.add_node("a", "thing", None).unwrap();
        g.add_node("b", "thing", None).unwrap();
        assert!(!g.reachable("a", "b", &KindFilter::Any));
    }

    #[test]
    // frob:ticket T-3005
    fn find_cycle_detects_a_planted_cycle() {
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        g.add_edge("refines", "c", "a").unwrap();
        let cycle = g.find_cycle(&KindFilter::Any);
        assert!(cycle.is_some(), "expected a cycle to be found");
        let cycle = cycle.unwrap();
        assert_eq!(cycle.first(), cycle.last());
        assert!(cycle.contains(&"a".to_string()));
        assert!(cycle.contains(&"b".to_string()));
        assert!(cycle.contains(&"c".to_string()));
    }

    #[test]
    // frob:ticket T-3005
    fn find_cycle_reports_none_on_a_clean_dag() {
        // Same shape as the planted-cycle fixture above MINUS the closing
        // edge -- a must-fail-vs-must-pass pair over the identical layout,
        // per the positive-control lesson (a checker that only ever sees
        // ONE layout can silently be blind to the other).
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        assert_eq!(g.find_cycle(&KindFilter::Any), None);
        assert!(!g.has_cycle(&KindFilter::Any));
    }

    #[test]
    // frob:ticket T-3005
    fn find_cycle_respects_kind_filter() {
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("decides", "b", "a").unwrap();
        // The full graph has a cycle across mixed kinds...
        assert!(g.has_cycle(&KindFilter::Any));
        // ...but restricted to "refines" alone there is no cycle.
        let only_refines = BTreeSet::from(["refines".to_string()]);
        assert!(!g.has_cycle(&KindFilter::Only(&only_refines)));
    }

    // frob:ticket T-3120
    // frob:tests strata-core/src/graph/query.rs::tests.has_cycle_true_on_a_planted_cycle
    #[test]
    fn has_cycle_true_on_a_planted_cycle() {
        // T-3120: TEST001 gap -- `has_cycle` itself (not just `find_cycle`,
        // which it delegates to) had no test directly bound to it by name
        // or `frob:tests` directive. A genuine cycle must-fire true.
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        g.add_edge("refines", "c", "a").unwrap();
        assert!(g.has_cycle(&KindFilter::Any));
    }

    // frob:ticket T-3120
    // frob:tests strata-core/src/graph/query.rs::tests.has_cycle_false_on_an_acyclic_graph
    #[test]
    fn has_cycle_false_on_an_acyclic_graph() {
        // T-3120: must-stay-quiet pair for the fixture above -- same node
        // set and edge kind, minus the closing edge that makes it a cycle.
        let mut g = Graph::new(chain_schema());
        for id in ["a", "b", "c"] {
            g.add_node(id, "thing", None).unwrap();
        }
        g.add_edge("refines", "a", "b").unwrap();
        g.add_edge("refines", "b", "c").unwrap();
        assert!(!g.has_cycle(&KindFilter::Any));
    }
}
