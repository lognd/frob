from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)


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

    # frob:ticket T-2700
    # frob:doc \
    # docs/modules/graph.md#self-disclosure-of-a-silently-degraded-capability-t-2683
    # frob:waive WIRE001 reason="already called at runtime from find_cycles in this \
    # same file (graph.degraded_languages, a few lines below) -- a @property is \
    # accessed WITHOUT call-parens by design, which is exactly the shape WIRE001's \
    # syntactic short(...) scan cannot see; genuinely wired, not dead, proven by \
    # tests/test_graph.py::TestDependencyGraphDegradedLanguages" \
    # follow_up="T-2746"
    @property
    def degraded_languages(self) -> tuple[str, ...]:
        """T-2700: `CallGraph.degraded_languages`'s (T-2683) analogue for
        `DependencyGraph` -- one human-readable warning per language
        present among THIS graph's own node ids whose `import_graph`
        capability cell is a live registry `KNOWN_GAP`, so cycle
        detection's own input can self-disclose "my edges are silently
        incomplete for language X" the same way `build_call_graph`'s
        output already does. Empty in the common case (every registered
        language is `import_graph`-`IMPLEMENTED` today, T-1599).

        Every real caller in this repo (`frob.app.cycle_runner`,
        `frob.check._python._build_import_graph`, `frob.arch._smells`)
        adds nodes as project-relative FILE paths (`add_node`/`add_edge`
        both take the same string identity `_process_path` and friends
        register), so the language present per node can be derived from
        its suffix the same way `frob.graph.callgraph._languages_present`
        derives it from an explicit `paths` argument -- no second
        parameter needs threading through every caller, the graph
        already carries what it needs."""
        from frob.cycle import import_graph_gap_disclosure
        from frob.lang import language_for_extension

        languages: set[str] = set()
        for node in self._nodes:
            label = language_for_extension(Path(node).suffix)
            if label is not None:
                languages.add(label)
        return import_graph_gap_disclosure(frozenset(languages))


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

    def _visit(self, v: str) -> None:
        """Index `v` and mark it on-stack; shared by the iterative driver's push."""
        self.index[v] = self.counter
        self.lowlink[v] = self.counter
        self.counter += 1
        self.stack.append(v)
        self.on_stack.add(v)

    # frob:ticket T-0952
    def _strongconnect(self, start: str) -> None:
        """Tarjan's SCC step for `start`'s component, iterative (explicit frame stack).

        Equivalent to the classic recursive `_strongconnect(v)` formulation but
        with an explicit stack of `(node, neighbor-iterator)` frames in place of
        native call recursion, so `find_cycles` cannot raise `RecursionError` on
        a long dependency chain (T-0952). Output ordering is identical to the
        recursive version: neighbors of a given node are still visited in
        `graph.neighbors(v)` order, one recursive descent at a time, and each
        completed component is popped at the same point in that traversal.
        """
        # frob:waive PERF003 reason="inherent to Tarjan SCC nested index-compare"
        self._visit(start)
        frames: list[tuple[str, Iterator[str]]] = [
            (start, iter(self.graph.neighbors(start)))
        ]

        while frames:
            v, it = frames[-1]
            descended = False
            for w in it:
                if w not in self.index:
                    # frob:invariant terminates reason="each pushed frame marks w in self.index before being pushed, and only unindexed w are pushed" measure="len(self.graph.nodes) - len(self.index) strictly decreases each push"  # noqa: E501
                    self._visit(w)
                    frames.append((w, iter(self.graph.neighbors(w))))
                    descended = True
                    break
                elif w in self.on_stack:
                    self.lowlink[v] = min(self.lowlink[v], self.index[w])
            if descended:
                continue

            frames.pop()
            if frames:
                parent = frames[-1][0]
                self.lowlink[parent] = min(self.lowlink[parent], self.lowlink[v])
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
# frob:ticket T-2700
# frob:doc \
# docs/modules/graph.md#self-disclosure-of-a-silently-degraded-capability-t-2683
def find_cycles(graph: DependencyGraph) -> list[list[str]]:
    """
    Return a list of cycles using Tarjan's SCC algorithm.
    Each cycle is the set of nodes in a strongly connected component
    with size >= 1 (self-loops count).

    T-2700: logs a WARNING (once per call, never raises/mutates the
    return shape -- every existing caller's `list[list[str]]` contract
    is unchanged) when `graph.degraded_languages` is non-empty, the
    same self-disclosure posture `build_call_graph` already has for
    `CallGraph.degraded_languages` (T-2683). This is what makes every
    real consumer -- `frob.app.cycle_runner`, `frob.check._python`'s
    CYCLE001 gate, `frob.arch._smells` -- actually SEE the disclosure
    on its own real invocation, without any of those three files
    needing an edit: they all already call `find_cycles(graph)`.
    """
    degraded = graph.degraded_languages
    if degraded:
        _log.warning(
            "find_cycles: %d language(s) present with a live import_graph "
            "capability KNOWN_GAP -- cycle detection silently omits edges "
            "for them: %s",
            len(degraded),
            degraded,
        )
    state = _TarjanState(graph)
    # Deterministic node order, sorted once up front (not per-iteration).
    ordered_nodes = sorted(graph.nodes)
    for node in ordered_nodes:
        if node not in state.index:
            state._strongconnect(node)
    return state.sccs
