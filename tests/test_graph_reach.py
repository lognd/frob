"""Tests for `frob.graph.reach` (T-3046: evidence-reach classification --
docs/modules/graph.md#evidence-reach-t-3046)."""

from __future__ import annotations

from pathlib import Path

from frob.graph._models import Digests, GraphSnapshot, SymbolId, SymbolRecord
from frob.graph.reach import EvidenceReach, classify_evidence_reach
from frob.lang import SymbolKind


# frob:waive DUP001 reason="mirrors tests/test_graph_affects.py::_record -- same \
# minimal-fixture-builder shape every frob.graph test module needs; T-2018's \
# established precedent for a small, stable helper duplicated once rather than \
# imported across test modules"
def _record(symref: str) -> SymbolRecord:
    """A minimal `SymbolRecord` for `symref` ("path::qualname")."""
    path, qualname = symref.split("::", 1)
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=True,
        digests=Digests(sig="s", body="b", doc="d"),
        span=(1, 3),
    )


def _snapshot(root: Path, symrefs: tuple[str, ...]) -> GraphSnapshot:
    """A `GraphSnapshot` with one record per `symrefs`, no edges -- reach
    is computed from the real call graph, not from graph edges."""
    return GraphSnapshot(
        root=str(root),
        symbols={ref: _record(ref) for ref in symrefs},
        edges=(),
        malformed=(),
        file_hashes={},
    )


class TestClassifyEvidenceReach:
    """`frob.graph.reach.classify_evidence_reach`."""

    def test_reaches_via_call_graph_closure(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "impl.py").write_text(
            "def _target():\n    return 1\n"
        )
        (tmp_path / "pkg" / "test_impl.py").write_text(
            "from pkg.impl import _target\n\n\ndef test_x():\n    _target()\n"
        )
        snap = _snapshot(
            tmp_path,
            ("pkg/impl.py::_target", "pkg/test_impl.py::test_x"),
        )
        result = classify_evidence_reach(
            tmp_path, snap, ("pkg/impl.py",), "pkg/test_impl.py::test_x"
        )
        assert result.status == EvidenceReach.REACHES

    def test_reaches_via_co_located_test_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "test_impl.py").write_text("def test_x():\n    pass\n")
        snap = _snapshot(tmp_path, ("pkg/test_impl.py::test_x",))
        result = classify_evidence_reach(
            tmp_path,
            snap,
            ("pkg/test_impl.py",),
            "pkg/test_impl.py::test_x",
        )
        assert result.status == EvidenceReach.REACHES
        assert "co-located" in result.reason

    def test_does_not_reach_when_closure_misses_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "impl.py").write_text(
            "def _target():\n    return 1\n"
        )
        (tmp_path / "pkg" / "test_unrelated.py").write_text(
            "def _helper():\n    return 2\n\n\ndef test_y():\n    _helper()\n"
        )
        snap = _snapshot(
            tmp_path,
            ("pkg/impl.py::_target", "pkg/test_unrelated.py::test_y"),
        )
        result = classify_evidence_reach(
            tmp_path, snap, ("pkg/impl.py",), "pkg/test_unrelated.py::test_y"
        )
        assert result.status == EvidenceReach.DOES_NOT_REACH

    def test_unknown_when_test_symbol_unresolved(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "impl.py").write_text("def _target():\n    return 1\n")
        (tmp_path / "pkg" / "test_unrelated.py").write_text(
            "def test_y():\n    pass\n"
        )
        snap = _snapshot(tmp_path, ("pkg/impl.py::_target",))
        result = classify_evidence_reach(
            tmp_path, snap, ("pkg/impl.py",), "pkg/test_unrelated.py::test_y"
        )
        assert result.status == EvidenceReach.UNKNOWN
        assert "not resolvable" in result.reason

    def test_unknown_when_scope_is_native_only(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        (tmp_path / "crate").mkdir()
        (tmp_path / "crate" / "lib.rs").write_text("pub fn f() {}\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_parse.py").write_text(
            "def test_parses():\n    pass\n"
        )
        snap = _snapshot(tmp_path, ("tests/test_parse.py::test_parses",))
        result = classify_evidence_reach(
            tmp_path,
            snap,
            ("crate/lib.rs",),
            "tests/test_parse.py::test_parses",
        )
        assert result.status == EvidenceReach.UNKNOWN
        assert "non-Python" in result.reason

    def test_evidence_scope_alone_does_not_launder_reach(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/reach.py::classify_evidence_reach
        # T-3046's own reproduction of the M6 hole: a Python scope with a
        # pytest evidence id whose file is named ONLY in `evidence_scope`
        # (a bare pointer, no lease) and whose test body never calls
        # anything the ticket's real `scope` names must still classify as
        # DOES_NOT_REACH, not REACHES -- otherwise this checker
        # reintroduces the exact laundering path it exists to close.
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "impl.py").write_text("def _target():\n    return 1\n")
        (tmp_path / "pkg" / "test_unrelated.py").write_text(
            "def test_y():\n    pass\n"
        )
        snap = _snapshot(
            tmp_path,
            ("pkg/impl.py::_target", "pkg/test_unrelated.py::test_y"),
        )
        result = classify_evidence_reach(
            tmp_path,
            snap,
            ("pkg/impl.py",),
            "pkg/test_unrelated.py::test_y",
            evidence_scope=("pkg/test_unrelated.py",),
        )
        assert result.status == EvidenceReach.DOES_NOT_REACH
