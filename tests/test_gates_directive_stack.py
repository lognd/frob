"""Tests for `frob.gates._directive_stack` (DSTACK001, T-4713).

Constructs `Edge`s directly rather than through `parse_directives` --
the grouping/threshold logic this module owns is graph-level, not
parse-level; `tests/unit/graph/test_dsl.py` covers the parser itself.
"""

from __future__ import annotations

from frob.gates._directive_stack import (
    DEFAULT_STACK_THRESHOLD,
    RULE_DSTACK001,
    stack_lint_violations,
)
from frob.graph import Edge, EdgeKind, GraphSnapshot


def _snapshot(edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A minimal `GraphSnapshot` carrying only `edges` -- every other
    field this gate never reads."""
    return GraphSnapshot(root=".", symbols={}, edges=edges)


def _edge(
    *, src: str, kind: EdgeKind, target: str, origin: str, attrs: dict | None = None
) -> Edge:
    return Edge(src=src, kind=kind, target=target, origin=origin, attrs=attrs or {})


class TestStackThresholdOffByOne:
    """N-1 directives above a symbol: no finding. N: exactly one finding.
    The off-by-one IS the whole configurability surface this leaf's
    ticket body names."""

    def _edges_for_count(self, count: int) -> tuple[Edge, ...]:
        return tuple(
            _edge(
                src="a.py::Foo.bar",
                kind=EdgeKind.TICKET,
                target=f"T-000{i}",
                origin=f"a.py:{i}",
            )
            for i in range(count)
        )

    def test_n_minus_one_is_not_a_finding(self) -> None:
        # frob:tests tests/test_gates_directive_stack.py::TestStackThresholdOffByOne.test_n_minus_one_is_not_a_finding  # noqa: E501
        snapshot = _snapshot(self._edges_for_count(DEFAULT_STACK_THRESHOLD - 1))
        assert stack_lint_violations(snapshot) == ()

    def test_n_is_exactly_one_finding(self) -> None:
        # frob:tests tests/test_gates_directive_stack.py::TestStackThresholdOffByOne.test_n_is_exactly_one_finding  # noqa: E501
        snapshot = _snapshot(self._edges_for_count(DEFAULT_STACK_THRESHOLD))
        violations = stack_lint_violations(snapshot)
        assert len(violations) == 1
        assert violations[0].rule == RULE_DSTACK001
        assert violations[0].file == "a.py"
        assert violations[0].line == 0

    def test_custom_threshold_is_honored(self) -> None:
        snapshot = _snapshot(self._edges_for_count(2))
        assert stack_lint_violations(snapshot, threshold=2) != ()
        assert stack_lint_violations(snapshot, threshold=3) == ()


class TestOnlyStackedSymbolFires:
    """A same-length run of directives NOT stacked above one symbol (each
    at its own distinct src) does not fire, even though the total
    directive count matches a genuine stack's."""

    def test_scattered_directives_across_symbols_do_not_fire(self) -> None:
        # frob:tests tests/test_gates_directive_stack.py::TestOnlyStackedSymbolFires.test_scattered_directives_across_symbols_do_not_fire  # noqa: E501
        edges = tuple(
            _edge(
                src=f"a.py::Foo.method_{i}",
                kind=EdgeKind.TICKET,
                target="T-0001",
                origin=f"a.py:{i}",
            )
            for i in range(DEFAULT_STACK_THRESHOLD)
        )
        snapshot = _snapshot(edges)
        assert stack_lint_violations(snapshot) == ()

    def test_stacked_symbol_fires_alongside_a_scattered_run_of_the_same_length(
        self,
    ) -> None:
        stacked = tuple(
            _edge(
                src="a.py::Foo.bar",
                kind=EdgeKind.TICKET,
                target=f"T-000{i}",
                origin=f"a.py:{i}",
            )
            for i in range(DEFAULT_STACK_THRESHOLD)
        )
        scattered = tuple(
            _edge(
                src=f"a.py::Other.method_{i}",
                kind=EdgeKind.TICKET,
                target="T-0009",
                origin=f"a.py:{100 + i}",
            )
            for i in range(DEFAULT_STACK_THRESHOLD)
        )
        snapshot = _snapshot(stacked + scattered)
        violations = stack_lint_violations(snapshot)
        assert len(violations) == 1
        assert "Foo.bar" in violations[0].message


class TestMultiTargetLineCountsOnce:
    """A T-4711 multi-target directive line produces several `Edge`s
    sharing ONE `origin` -- the stack count is DISTINCT origins, so a
    multi-target line counts as one physical line, not one per target."""

    def test_multi_target_edges_sharing_an_origin_count_as_one_line(self) -> None:
        multi_target = tuple(
            _edge(
                src="a.py::Foo.bar",
                kind=EdgeKind.TESTS,
                target=f"b.py::T.test_{i}",
                origin="a.py:1",
            )
            for i in range(DEFAULT_STACK_THRESHOLD)
        )
        snapshot = _snapshot(multi_target)
        # DEFAULT_STACK_THRESHOLD edges, but only ONE distinct origin --
        # below threshold.
        assert stack_lint_violations(snapshot) == ()


class TestDstack001MergeFix:
    """`frob.gates._fix_engine_text.fix_dstack001_merge` -- the Tier-A
    merge fix. Round-trips through the real parser (`frob.graph.dsl.
    parse_directives`) rather than hand-asserting file text, so these
    tests prove the merge preserves the edge set, not just that SOME
    rewrite happened."""

    def _build(self, tmp_path, src: str):  # noqa: ANN001
        from frob.graph.dsl import parse_directives
        from frob.lang import parse_file

        path = tmp_path / "foo.py"
        path.write_text(src)
        parsed = parse_file(path).danger_ok
        parsed = parsed.model_copy(update={"path": "foo.py"})
        edges, malformed = parse_directives(parsed)
        assert not malformed
        return path, edges

    def _edge_key_set(self, edges):  # noqa: ANN001
        return {
            (e.src, e.kind, e.target, tuple(sorted((e.attrs or {}).items())))
            for e in edges
        }

    def test_interleaved_doc_tests_doc_collapses_to_one_doc_then_one_tests(
        self, tmp_path
    ) -> None:
        # frob:tests tests/test_gates_directive_stack.py::TestDstack001MergeFix.test_interleaved_doc_tests_doc_collapses_to_one_doc_then_one_tests  # noqa: E501
        from frob.gates._fix_engine_text import fix_dstack001_merge
        from frob.graph import GraphSnapshot

        src = (
            "class Foo:\n"
            "    # frob:doc docs/a.md#x\n"
            "    # frob:tests a.py::A.m\n"
            "    # frob:doc docs/b.md#y\n"
            "    # frob:tests b.py::B.n\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        path, edges = self._build(tmp_path, src)
        before_keys = self._edge_key_set(edges)
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges)
        applied = fix_dstack001_merge(tmp_path, snapshot, None, "T-TEST")
        assert len(applied) == 1
        rewritten = path.read_text()
        lines = [
            line
            for line in rewritten.splitlines()
            if "frob:doc" in line or "frob:tests" in line
        ]
        assert len(lines) == 2
        assert "frob:doc" in lines[0]
        assert "frob:tests" in lines[1]
        _, after_edges = self._build(tmp_path, rewritten)
        assert self._edge_key_set(after_edges) == before_keys

    def test_tests_doc_tests_puts_tests_first_not_a_hardcoded_kind_order(
        self, tmp_path
    ) -> None:
        # The test cannot pass on a hardcoded kind order -- this plants
        # tests-first instead of doc-first.
        from frob.gates._fix_engine_text import fix_dstack001_merge
        from frob.graph import GraphSnapshot

        src = (
            "class Foo:\n"
            "    # frob:tests a.py::A.m\n"
            "    # frob:doc docs/a.md#x\n"
            "    # frob:tests b.py::B.n\n"
            "    # frob:doc docs/b.md#y\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        path, edges = self._build(tmp_path, src)
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges)
        fix_dstack001_merge(tmp_path, snapshot, None, "T-TEST")
        rewritten = path.read_text()
        lines = [
            line
            for line in rewritten.splitlines()
            if "frob:tests" in line or "frob:doc" in line
        ]
        assert len(lines) == 2
        assert "frob:tests" in lines[0]
        assert "frob:doc" in lines[1]

    def test_merge_is_idempotent(self, tmp_path) -> None:
        from frob.gates._fix_engine_text import fix_dstack001_merge
        from frob.graph import GraphSnapshot

        src = (
            "class Foo:\n"
            "    # frob:doc docs/a.md#x\n"
            "    # frob:tests a.py::A.m\n"
            "    # frob:doc docs/b.md#y\n"
            "    # frob:tests b.py::B.n\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        path, edges = self._build(tmp_path, src)
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges)
        first = fix_dstack001_merge(tmp_path, snapshot, None, "T-TEST")
        assert len(first) == 1
        _, edges2 = self._build(tmp_path, path.read_text())
        snapshot2 = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges2)
        second = fix_dstack001_merge(tmp_path, snapshot2, None, "T-TEST")
        assert second == []

    def test_only_paths_scoping_leaves_an_unlisted_file_untouched(
        self, tmp_path
    ) -> None:
        from frob.gates._fix_engine_text import fix_dstack001_merge
        from frob.graph import GraphSnapshot

        src = (
            "class Foo:\n"
            "    # frob:doc docs/a.md#x\n"
            "    # frob:tests a.py::A.m\n"
            "    # frob:doc docs/b.md#y\n"
            "    # frob:tests b.py::B.n\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        path, edges = self._build(tmp_path, src)
        original = path.read_text()
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges)
        applied = fix_dstack001_merge(
            tmp_path, snapshot, None, "T-TEST", only_paths=frozenset({"other.py"})
        )
        assert applied == []
        assert path.read_text() == original

    def test_non_default_attrs_leaves_the_stack_untouched(self, tmp_path) -> None:
        # A genuinely non-default kind= on one target must not be
        # silently dropped by the merge -- never invent a binding.
        from frob.gates._fix_engine_text import fix_dstack001_merge
        from frob.graph import GraphSnapshot

        src = (
            "class Foo:\n"
            '    # frob:tests a.py::A.m kind="integration"\n'
            "    # frob:doc docs/a.md#x\n"
            "    # frob:tests b.py::B.n\n"
            "    # frob:doc docs/b.md#y\n"
            "    def bar(self) -> None:\n"
            "        pass\n"
        )
        path, edges = self._build(tmp_path, src)
        original = path.read_text()
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=edges)
        applied = fix_dstack001_merge(tmp_path, snapshot, None, "T-TEST")
        assert applied == []
        assert path.read_text() == original
