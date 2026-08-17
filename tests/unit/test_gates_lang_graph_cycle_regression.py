"""T-2231 regression: the gates/lang/graph import-cycle cluster merged two
distinct problems (docs/design note on the ticket itself, and this repo's
own investigation):

(a) `frob.gates._docblocks` and `frob.gates._docblocks_refs` mutually
    imported each other at module level -- a real, mechanical cycle, not a
    lazy-import false positive. `_ProjectNamespaces`, `_read_toml`, and
    `_doc004_violation` (the only names `_docblocks_refs.py` needed back
    from `_docblocks.py`) moved to a new leaf module,
    `frob.gates._docblocks_shared`, that neither sibling needs to import
    back from.

(b) `frob.graph._models`/`frob.graph.cache` imported `SymbolKind`/
    `GRAMMAR_FINGERPRINT_PACKAGES` from the `frob.lang` PACKAGE namespace
    (`frob.lang.__init__`), whose own `__init__.py` lazily imports
    `frob.graph.cache` back (T-1464, documented, deliberate). The static
    cycle checker does not distinguish module-level from function-scope
    imports, so this read as a live cycle even though it was already
    broken at runtime. Genuinely inverted (not a checker change): both
    names now live in `frob.lang._models`, a pure leaf with zero `frob.*`
    imports; `frob.graph._models`/`frob.graph.cache` import them from
    there directly, and `frob.lang.__init__` re-exports them for every
    existing `frob.lang.X` caller.

This test runs the real cycle detector
(`frob.check._python._build_import_graph` + `frob.cycle.graph.find_cycles`)
against this repo's actual `src/` tree and asserts no cycle contains any
member of the original 6-node cluster (`_docblocks_refs.py` ->
`_docblocks.py` -> `lang/_support.py` -> `graph/cache.py` ->
`lang/__init__.py` -> `graph/_models.py` -> `_docblocks_refs.py`).
"""

from __future__ import annotations

from pathlib import Path

from frob.check._python import _build_import_graph
from frob.cycle.graph import find_cycles

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

_CLUSTER_MEMBERS = {
    "frob/gates/_docblocks_refs.py",
    "frob/gates/_docblocks.py",
    "frob/lang/_support.py",
    "frob/graph/cache.py",
    "frob/lang/__init__.py",
    "frob/graph/_models.py",
}


class TestGatesLangGraphCycleRegression:
    def test_gates_lang_graph_cluster_is_not_an_error_cycle(self) -> None:
        # frob:tests src/frob/check/_python.py::_build_import_graph kind="unit"
        # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
        graph = _build_import_graph(_SRC_ROOT)
        cycles = find_cycles(graph)
        for cycle in cycles:
            nodes = set(cycle)
            overlap = nodes & _CLUSTER_MEMBERS
            # T-2231 case (b) is a genuine structural inversion, not a
            # checker change -- it does not (and is not required to)
            # eliminate the SEPARATE, pre-existing lang/_support.py <->
            # lang/__init__.py lazy-only 2-node info-severity finding
            # (same class as this repo's other already-accepted
            # lazy-import-only cycles); only the original 6-node
            # ERROR-severity cluster spanning gates/_docblocks*.py AND
            # graph/*.py together must be gone.
            if overlap == {"frob/lang/_support.py", "frob/lang/__init__.py"}:
                continue
            assert not overlap, (
                f"gates/lang/graph cluster reappeared in a cycle: {cycle}"
            )
