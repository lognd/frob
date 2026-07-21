from __future__ import annotations

from collections import defaultdict


# frob:doc docs/commands/cycle.md#public-api
class DependencyGraph:
    def __init__(self) -> None:
        self._edges: dict[str, set[str]] = defaultdict(set)
        self._nodes: set[str] = set()

    # frob:doc docs/commands/cycle.md#public-api
    def add_edge(self, src: str, dst: str) -> None:
        self._nodes.add(src)
        self._nodes.add(dst)
        self._edges[src].add(dst)

    # frob:doc docs/commands/cycle.md#public-api
    def add_node(self, node: str) -> None:
        self._nodes.add(node)

    # frob:doc docs/commands/cycle.md#public-api
    @property
    def nodes(self) -> frozenset[str]:
        return frozenset(self._nodes)

    # frob:doc docs/commands/cycle.md#public-api
    def neighbors(self, node: str) -> set[str]:
        return self._edges.get(node, set())


class _TarjanState:
    """Mutable working state for one `find_cycles` run (index/lowlink/stack/sccs)."""

    def __init__(self, graph: DependencyGraph) -> None:
        """Bind Tarjan's bookkeeping structures to the `graph` being traversed."""
        self.graph = graph
        self.counter = 0
        self.stack: list[str] = []
        self.on_stack: set[str] = set()
        self.index: dict[str, int] = {}
        self.lowlink: dict[str, int] = {}
        self.sccs: list[list[str]] = []

    def _strongconnect(self, v: str) -> None:
        """Tarjan's SCC recursion step, pushing a completed component into `sccs`."""
        # frob:waive PERF003 reason="inherent to Tarjan SCC nested index-compare"
        self.index[v] = self.counter
        self.lowlink[v] = self.counter
        self.counter += 1
        self.stack.append(v)
        self.on_stack.add(v)

        for w in self.graph.neighbors(v):
            if w not in self.index:
                # frob:invariant terminates reason="each recursive call marks w in self.index before descending, and only unindexed w reach the call" measure="len(self.graph.nodes) - len(self.index) strictly decreases each call"  # noqa: E501
                self._strongconnect(w)
                self.lowlink[v] = min(self.lowlink[v], self.lowlink[w])
            elif w in self.on_stack:
                self.lowlink[v] = min(self.lowlink[v], self.index[w])

        if self.lowlink[v] == self.index[v]:
            self._pop_component(v)

    def _pop_component(self, v: str) -> None:
        """Pop the just-completed component off `stack`, recording it if a cycle."""
        scc: list[str] = []
        while True:
            w = self.stack.pop()
            self.on_stack.remove(w)
            scc.append(w)
            if w == v:
                break
        # A single node with no self-loop is not a cycle
        if len(scc) > 1 or v in self.graph.neighbors(v):
            self.sccs.append(scc)


# frob:doc docs/commands/cycle.md#public-api
def find_cycles(graph: DependencyGraph) -> list[list[str]]:
    """
    Return a list of cycles using Tarjan's SCC algorithm.
    Each cycle is the set of nodes in a strongly connected component
    with size >= 1 (self-loops count).
    """
    state = _TarjanState(graph)
    # Deterministic node order, sorted once up front (not per-iteration).
    ordered_nodes = sorted(graph.nodes)
    for node in ordered_nodes:
        if node not in state.index:
            state._strongconnect(node)
    return state.sccs
