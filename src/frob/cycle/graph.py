from __future__ import annotations

from collections import defaultdict


# frob:doc docs/commands/cycle.md#public-api
class DependencyGraph:
    def __init__(self) -> None:
        self._edges: dict[str, set[str]] = defaultdict(set)
        self._nodes: set[str] = set()

    def add_edge(self, src: str, dst: str) -> None:
        # frob:doc docs/commands/cycle.md#public-api
        self._nodes.add(src)
        self._nodes.add(dst)
        self._edges[src].add(dst)

    def add_node(self, node: str) -> None:
        # frob:doc docs/commands/cycle.md#public-api
        self._nodes.add(node)

    @property
    def nodes(self) -> frozenset[str]:
        # frob:doc docs/commands/cycle.md#public-api
        return frozenset(self._nodes)

    def neighbors(self, node: str) -> set[str]:
        # frob:doc docs/commands/cycle.md#public-api
        return self._edges.get(node, set())


# frob:doc docs/commands/cycle.md#public-api
def find_cycles(graph: DependencyGraph) -> list[list[str]]:
    """
    Return a list of cycles using Tarjan's SCC algorithm.
    Each cycle is the set of nodes in a strongly connected component
    with size >= 1 (self-loops count).
    """
    # frob:waive PERF003 reason="inherent to Tarjan SCC nested index-compare traversal"
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []
    # Deterministic node order, sorted once up front (not per-iteration).
    ordered_nodes = sorted(graph.nodes)

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.neighbors(v):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            # A single node with no self-loop is not a cycle
            if len(scc) > 1 or v in graph.neighbors(v):
                sccs.append(scc)

    for node in ordered_nodes:
        if node not in index:
            strongconnect(node)

    return sccs
