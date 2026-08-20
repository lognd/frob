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
# frob:waive WIRE001 reason="exposed for frob.cycle.graph's own future use, not called \
# outside its own tests yet -- wiring it into DependencyGraph/find_cycles's real \
# output needs frob.cycle.graph, out of T-2683's own scope, see this function's \
# docstring" follow_up="T-2700"
def import_graph_gap_disclosure(languages: frozenset[str]) -> tuple[str, ...]:
    """T-2683: one human-readable warning per `languages` member whose
    `import_graph` capability cell is a live registry `KNOWN_GAP` --
    `frob.graph.callgraph.capability_gap_disclosure` pre-bound to the
    `import_graph` capability, the axis `frob.cycle`'s own dependency
    graph depends on.

    SCOPE BOUNDARY, disclosed rather than silently worked around: this
    ticket's declared scope is this module (the re-export shim) plus
    `frob.graph.callgraph`, `docs/modules/lang.md`, `docs/modules/
    graph.md` -- NOT `frob.cycle.graph`, where `DependencyGraph`/`find_
    cycles`'s own OUTPUT type actually lives. That means this function
    exists and is real/tested, but nothing in `frob.cycle.graph` calls
    it yet -- `find_cycles`'s own return value does not YET self-
    disclose an import_graph gap the way `CallGraph.degraded_languages`
    does for `build_call_graph`. Wiring it in requires touching `frob.
    cycle.graph`, out of this ticket's own scope; filed as follow-up
    (T-2700) rather than silently widening scope to finish it here."""
    return capability_gap_disclosure(languages, "import_graph")
