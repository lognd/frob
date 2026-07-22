"""Tests for `frob.graph.affects` (T-0325's north-star digest-graph query,
docs/modules/graph.md#affects)."""

from __future__ import annotations

from frob.graph._models import (
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    SymbolId,
    SymbolRecord,
)
from frob.graph.affects import affects
from frob.lang import SymbolKind


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


def _snapshot(symrefs: tuple[str, ...], edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A `GraphSnapshot` with one record per `symrefs` and `edges` set verbatim."""
    return GraphSnapshot(
        root="/repo",
        symbols={ref: _record(ref) for ref in symrefs},
        edges=edges,
        malformed=(),
        file_hashes={},
    )


class TestAffects:
    """`frob.graph.affects.affects` -- transitive doc-drift digest-graph query."""

    def test_no_edges_is_empty_set(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        snap = _snapshot(("a.py::foo",), ())
        result = affects(snap, "a.py::foo")
        assert result.root == "a.py::foo"
        assert result.dependents == ()
        assert result.docs == ()
        assert result.tests == ()
        assert result.truncated is False

    def test_direct_doc_and_test_edges(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        edges = (
            Edge(
                src="a.py::foo",
                kind=EdgeKind.DOC,
                target="docs/modules/x.md#foo",
                origin="a.py:1",
            ),
            Edge(
                src="docs/x.md#foo",
                kind=EdgeKind.DESCRIBES,
                target="a.py::foo",
                origin="docs/x.md:2",
            ),
            Edge(
                src="tests/test_a.py::test_foo",
                kind=EdgeKind.TESTS,
                target="a.py::foo",
                origin="tests/test_a.py:5",
            ),
        )
        snap = _snapshot(("a.py::foo",), edges)
        result = affects(snap, "a.py::foo")
        assert result.dependents == ()
        assert set(result.docs) == {"docs/modules/x.md#foo", "docs/x.md#foo"}
        assert result.tests == ("tests/test_a.py::test_foo",)

    def test_transitive_uses_contract_chain(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        # a.py::foo <- b.py::bar (uses-contract) <- c.py::baz (uses-contract)
        # b.py::bar has its own doc edge; c.py::baz has its own test edge.
        edges = (
            Edge(
                src="b.py::bar",
                kind=EdgeKind.USES_CONTRACT,
                target="a.py::foo",
                origin="b.py:1",
            ),
            Edge(
                src="c.py::baz",
                kind=EdgeKind.USES_CONTRACT,
                target="b.py::bar",
                origin="c.py:1",
            ),
            Edge(
                src="b.py::bar",
                kind=EdgeKind.DOC,
                target="docs/modules/b.md#bar",
                origin="b.py:2",
            ),
            Edge(
                src="tests/test_c.py::test_baz",
                kind=EdgeKind.TESTS,
                target="c.py::baz",
                origin="tests/test_c.py:1",
            ),
        )
        snap = _snapshot(("a.py::foo", "b.py::bar", "c.py::baz"), edges)
        result = affects(snap, "a.py::foo")
        assert set(result.dependents) == {"b.py::bar", "c.py::baz"}
        assert result.docs == ("docs/modules/b.md#bar",)
        assert result.tests == ("tests/test_c.py::test_baz",)
        assert result.truncated is False

    def test_cycle_guarded(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        # a <-uses-contract- b <-uses-contract- a (mutual cycle): must terminate.
        edges = (
            Edge(
                src="b.py::bar",
                kind=EdgeKind.USES_CONTRACT,
                target="a.py::foo",
                origin="b.py:1",
            ),
            Edge(
                src="a.py::foo",
                kind=EdgeKind.USES_CONTRACT,
                target="b.py::bar",
                origin="a.py:1",
            ),
        )
        snap = _snapshot(("a.py::foo", "b.py::bar"), edges)
        result = affects(snap, "a.py::foo")
        assert result.dependents == ("b.py::bar",)
        assert result.truncated is False

    def test_truncated_at_max_depth(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        # a chain of 5 uses-contract hops; max_depth=2 should stop early and
        # report truncated.
        refs = tuple(f"m{i}.py::f{i}" for i in range(6))
        edges = tuple(
            Edge(
                src=refs[i + 1],
                kind=EdgeKind.USES_CONTRACT,
                target=refs[i],
                origin=f"{refs[i + 1]}:1",
            )
            for i in range(5)
        )
        snap = _snapshot(refs, edges)
        result = affects(snap, refs[0], max_depth=2)
        assert result.truncated is True
        assert len(result.dependents) == 2

    def test_truncated_at_max_nodes(self) -> None:
        # frob:tests src/frob/graph/affects.py::affects
        refs = tuple(f"m{i}.py::f{i}" for i in range(6))
        edges = tuple(
            Edge(
                src=refs[i + 1],
                kind=EdgeKind.USES_CONTRACT,
                target=refs[0],
                origin=f"{refs[i + 1]}:1",
            )
            for i in range(5)
        )
        snap = _snapshot(refs, edges)
        result = affects(snap, refs[0], max_nodes=3)
        assert result.truncated is True
        assert len(result.dependents) <= 2
