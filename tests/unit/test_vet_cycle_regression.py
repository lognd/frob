"""T-2233 regression: `frob.vet._hook`, `_closedworld.py`, `_scan_violations.py`,
and `_scan.py` used to import their leaf sibling modules (`_registry`,
`_typosquat`, `_cache`, `_capability`, `_source`, `_ecosystem`, `_lifecycle`,
`_obfuscation`, `_osv`, `_supplychain`) via `from frob.vet import X[, Y, ...]`
-- through the `frob.vet` PACKAGE namespace, whose own `__init__.py`
eagerly imports `_closedworld`/`_hook`/`_scan` back -- instead of importing
the leaf submodules directly. Same shape as T-2232's dup/_pipeline cluster:
`frob.lang._extract._python_import_specifiers` (T-2211) emits both the bare
"frob.vet" and the qualified "frob.vet._registry" (etc) specifiers for a
`from frob.vet import _registry` statement, and `resolve_local_import`
resolves the bare one to `vet/__init__.py`, closing the cycle. Retargeting
the imports at the leaf submodules closes it without touching detection
itself -- this test runs the real cycle detector
(`frob.check._python._build_import_graph` + `frob.cycle.graph.find_cycles`)
against this repo's actual `src/` tree and asserts no cycle contains any
vet cluster member.
"""

from __future__ import annotations

from pathlib import Path

from frob.check._python import _build_import_graph
from frob.cycle.graph import find_cycles

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

_CLUSTER_MEMBERS = {
    "frob/vet/_hook.py",
    "frob/vet/_closedworld.py",
    "frob/vet/_scan_violations.py",
    "frob/vet/_scan.py",
    "frob/vet/__init__.py",
}


class TestVetCycleRegression:
    def test_vet_cluster_is_not_a_cycle(self) -> None:
        # frob:tests src/frob/check/_python.py::_build_import_graph kind="unit"
        # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
        graph = _build_import_graph(_SRC_ROOT)
        cycles = find_cycles(graph)
        for cycle in cycles:
            nodes = set(cycle)
            assert not nodes & _CLUSTER_MEMBERS, (
                f"vet cluster reappeared in a cycle: {cycle}"
            )
