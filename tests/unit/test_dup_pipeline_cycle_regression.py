"""T-2232 regression: `frob.dup._pipeline`'s leaf modules (`_fingerprint.py`,
`_callgraph.py`) and `frob.dup._template` used to import `_cache`/`_core`
via `from frob.dup import _cache, _core` -- through the `frob.dup` PACKAGE
namespace, whose own `__init__.py` eagerly imports `_pipeline`/`_template`
back -- instead of importing the leaf submodules directly. That created a
real import cycle spanning `_fingerprint.py`, `_probe.py`, `_smt.py`,
`_callgraph.py`, `_pipeline/__init__.py`, `_template.py`, and `dup/
__init__.py` (`uv run frob check --only cycle`, 2026-08-16). Retargeting
the imports at the leaf submodules (`frob.dup._cache`, `frob.dup._core`)
closes the cycle without touching detection itself -- this test runs the
real cycle detector (`frob.check._python._build_import_graph` +
`frob.cycle.graph.find_cycles`) against this repo's actual `src/` tree and
asserts no cycle contains any dup/_pipeline cluster member.
"""

from __future__ import annotations

from pathlib import Path

from frob.check._python import _build_import_graph
from frob.cycle.graph import find_cycles

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

_CLUSTER_MEMBERS = {
    "frob/dup/_pipeline/_fingerprint.py",
    "frob/dup/_pipeline/_probe.py",
    "frob/dup/_pipeline/_smt.py",
    "frob/dup/_pipeline/_callgraph.py",
    "frob/dup/_pipeline/__init__.py",
    "frob/dup/_template.py",
    "frob/dup/__init__.py",
}


class TestDupPipelineCycleRegression:
    def test_dup_pipeline_cluster_is_not_a_cycle(self) -> None:
        # frob:tests src/frob/check/_python.py::_build_import_graph kind="unit"
        # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
        graph = _build_import_graph(_SRC_ROOT)
        cycles = find_cycles(graph)
        for cycle in cycles:
            nodes = set(cycle)
            assert not nodes & _CLUSTER_MEMBERS, (
                f"dup/_pipeline cluster reappeared in a cycle: {cycle}"
            )
