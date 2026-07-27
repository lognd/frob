"""Tests for `frob.gates.affect_drift_gate` (AFFECT001/AFFECT002, T-0628):
the `affects()`-closure digest-drift enforcement half T-0325 cut as future
work (docs/modules/graph.md#affects) -- FAIL when a touched symbol's
dependent doc anchor or dependent symbol's file was not also touched in the
same diff."""

from __future__ import annotations

from frob.gates import affect_drift_gate
from frob.gitio import Diff, Hunk
from frob.graph._models import (
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    SymbolId,
    SymbolRecord,
)
from frob.lang import SymbolKind


def _record(symref: str, span: tuple[int, int] = (1, 3)) -> SymbolRecord:
    """A minimal `SymbolRecord` for `symref` ("path::qualname")."""
    path, qualname = symref.split("::", 1)
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=True,
        digests=Digests(sig="s", body="b", doc="d"),
        span=span,
    )


def _snapshot(
    records: dict[str, tuple[int, int]], edges: tuple[Edge, ...]
) -> GraphSnapshot:
    """A `GraphSnapshot` with one record per `records` (symref -> span) and
    `edges` set verbatim."""
    return GraphSnapshot(
        root="/repo",
        symbols={ref: _record(ref, span) for ref, span in records.items()},
        edges=edges,
        malformed=(),
        file_hashes={},
    )


def _diff(*files_and_spans: tuple[str, tuple[int, int]]) -> Diff:
    """A `Diff` with one hunk per `(file, span)` pair."""
    return Diff(
        base="main",
        hunks=tuple(Hunk(file=f, span=s) for f, s in files_and_spans),
    )


class TestAffectDriftGate:
    """`affect_drift_gate` -- AFFECT001 (stale doc) / AFFECT002 (stale dependent)."""

    def test_no_closure_is_silent(self) -> None:
        # frob:tests src/frob/gates/__init__.py::affect_drift_gate
        snap = _snapshot({"a.py::root": (1, 3)}, ())
        diff = _diff(("a.py", (1, 3)))
        assert affect_drift_gate(snap, diff) == ()

    def test_stale_dependent_doc_flagged(self) -> None:
        # frob:tests src/frob/gates/__init__.py::affect_drift_gate
        edges = (
            Edge(
                src="a.py::root",
                kind=EdgeKind.DOC,
                target="docs/x.md#root",
                origin="a.py:1",
            ),
        )
        snap = _snapshot({"a.py::root": (1, 3)}, edges)
        diff = _diff(("a.py", (1, 3)))  # docs/x.md NOT touched
        violations = affect_drift_gate(snap, diff)
        assert any(v.rule == "AFFECT001" for v in violations)
        assert any("docs/x.md#root" in v.message for v in violations)

    def test_stale_dependent_code_flagged(self) -> None:
        # frob:tests src/frob/gates/__init__.py::affect_drift_gate
        edges = (
            Edge(
                src="dep.py::dependent",
                kind=EdgeKind.USES_CONTRACT,
                target="a.py::root",
                origin="dep.py:1",
            ),
        )
        snap = _snapshot({"a.py::root": (1, 3), "dep.py::dependent": (1, 3)}, edges)
        diff = _diff(("a.py", (1, 3)))  # dep.py NOT touched
        violations = affect_drift_gate(snap, diff)
        assert any(v.rule == "AFFECT002" for v in violations)
        assert any("dep.py::dependent" in v.message for v in violations)

    def test_clean_when_closure_also_touched(self) -> None:
        # frob:tests src/frob/gates/__init__.py::affect_drift_gate
        edges = (
            Edge(
                src="a.py::root",
                kind=EdgeKind.DOC,
                target="docs/x.md#root",
                origin="a.py:1",
            ),
            Edge(
                src="dep.py::dependent",
                kind=EdgeKind.USES_CONTRACT,
                target="a.py::root",
                origin="dep.py:1",
            ),
        )
        snap = _snapshot({"a.py::root": (1, 3), "dep.py::dependent": (1, 3)}, edges)
        diff = _diff(("a.py", (1, 3)), ("docs/x.md", (1, 1)), ("dep.py", (1, 3)))
        assert affect_drift_gate(snap, diff) == ()
