"""frob.cycle -- import-cycle detection over the language-agnostic call graph
(docs/modules/gates.md). Re-exports `graph.DependencyGraph`/`find_cycles`,
both consumed cross-package by `frob.check` and `frob.app.cycle_runner`
(T-0362).
"""

from __future__ import annotations

from frob.cycle.graph import DependencyGraph, find_cycles
from frob.graph.callgraph import capability_gap_disclosure

__all__ = [
    "DependencyGraph",
    "capability_gap_disclosure",
    "find_cycles",
    "import_graph_gap_disclosure",
]


# frob:ticket T-2683
# frob:doc docs/modules/graph.md#self-disclosure-of-a-silently-degraded-capability-t-2683  # noqa: E501
# frob:tests tests/test_graph.py::TestCycleImportGraphGapDisclosure.test_empty_for_no_gap  # noqa: E501
# frob:tests tests/test_graph.py::TestCycleImportGraphGapDisclosure.test_delegates_to_the_shared_primitive  # noqa: E501
def import_graph_gap_disclosure(languages: frozenset[str]) -> tuple[str, ...]:
    """T-2683: one human-readable warning per `languages` member whose
    `import_graph` capability cell is a live registry `KNOWN_GAP` --
    `frob.graph.callgraph.capability_gap_disclosure` pre-bound to the
    `import_graph` capability, the axis `frob.cycle`'s own dependency
    graph depends on.

    T-2700 wired this in for real:
    `frob.cycle.graph.DependencyGraph.degraded_languages` calls this
    function directly (a lazy import inside the property body, since
    `frob.cycle.graph` is imported BY this module and a top-level
    import here would cycle), so `find_cycles`'s own real output now
    self-discloses an import_graph gap the same way
    `CallGraph.degraded_languages` does for `build_call_graph`."""
    return capability_gap_disclosure(languages, "import_graph")
