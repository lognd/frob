"""frob.cycle -- import-cycle detection over the language-agnostic call graph
(docs/modules/gates.md). Re-exports `graph.DependencyGraph`/`find_cycles`,
both consumed cross-package by `frob.check` and `frob.app.cycle_runner`
(T-0362).
"""

from __future__ import annotations

from frob.cycle.graph import DependencyGraph, find_cycles

__all__ = ["DependencyGraph", "find_cycles"]
