"""INV007/INV008 gate tests (T-0757, docs/modules/gates.md#inv007-inv008-t-0757):
`frob.gates._design_invariants.inv007_violations`/`inv008_violations`
directly, over a hand-built `GraphSnapshot` -- no full `frob check` run
needed since both functions are pure over their inputs.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._design_invariants import inv007_violations, inv008_violations
from frob.graph import Edge, EdgeKind, GraphSnapshot


def _snapshot(root: Path, edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A minimal `GraphSnapshot` carrying only `edges` -- both gates under
    test read nothing else off the snapshot."""
    return GraphSnapshot(root=str(root), symbols={}, edges=edges)


class TestInv007:
    """`frob:invariant ... no_import="..."` (import-forbidding)."""

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_forbidden_import_fires  # noqa: E501
    def test_forbidden_import_fires(self, tmp_path: Path) -> None:
        mod = tmp_path / "pure.py"
        mod.write_text("import tree_sitter\n")
        edge = Edge(
            src="pure.py",
            kind=EdgeKind.INVARIANT,
            target="INV-042",
            origin="pure.py:1",
            attrs={"no_import": "tree_sitter"},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        violations = inv007_violations(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].rule == "INV007"
        assert violations[0].file == "pure.py"

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_clean_module_no_finding  # noqa: E501
    def test_clean_module_no_finding(self, tmp_path: Path) -> None:
        mod = tmp_path / "pure.py"
        mod.write_text("import os\n")
        edge = Edge(
            src="pure.py",
            kind=EdgeKind.INVARIANT,
            target="INV-042",
            origin="pure.py:1",
            attrs={"no_import": "tree_sitter"},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv007_violations(tmp_path, snapshot) == ()

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_submodule_import_also_forbidden  # noqa: E501
    def test_submodule_import_also_forbidden(self, tmp_path: Path) -> None:
        mod = tmp_path / "pure.py"
        mod.write_text("from tree_sitter.binding import Parser\n")
        edge = Edge(
            src="pure.py",
            kind=EdgeKind.INVARIANT,
            target="INV-042",
            origin="pure.py:1",
            attrs={"no_import": "tree_sitter"},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert len(inv007_violations(tmp_path, snapshot)) == 1

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_lookalike_module_name_not_a_false_positive  # noqa: E501
    def test_lookalike_module_name_not_a_false_positive(self, tmp_path: Path) -> None:
        mod = tmp_path / "pure.py"
        mod.write_text("import tree_sitter_python\n")
        edge = Edge(
            src="pure.py",
            kind=EdgeKind.INVARIANT,
            target="INV-042",
            origin="pure.py:1",
            attrs={"no_import": "tree_sitter"},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv007_violations(tmp_path, snapshot) == ()

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_no_obligation_attr_is_unaffected  # noqa: E501
    def test_no_obligation_attr_is_unaffected(self, tmp_path: Path) -> None:
        mod = tmp_path / "pure.py"
        mod.write_text("import tree_sitter\n")
        edge = Edge(
            src="pure.py",
            kind=EdgeKind.INVARIANT,
            target="INV-001",
            origin="pure.py:1",
            attrs={},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv007_violations(tmp_path, snapshot) == ()


class TestInv008:
    """`frob:invariant ... establishes="..."` (establish-property)."""

    # frob:tests tests/unit/test_design_invariants.py::TestInv008.test_missing_property_test_fires  # noqa: E501
    def test_missing_property_test_fires(self, tmp_path: Path) -> None:
        edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.INVARIANT,
            target="INV-043",
            origin="a.py:10",
            attrs={"establishes": "richer state always wins unless outranked"},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        violations = inv008_violations(snapshot)
        assert len(violations) == 1
        assert violations[0].rule == "INV008"

    # frob:tests tests/unit/test_design_invariants.py::TestInv008.test_bound_property_test_clears  # noqa: E501
    def test_bound_property_test_clears(self, tmp_path: Path) -> None:
        inv_edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.INVARIANT,
            target="INV-043",
            origin="a.py:10",
            attrs={"establishes": "richer state always wins unless outranked"},
        )
        test_edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.TESTS,
            target="tests/test_a.py::test_newer_property",
            origin="a.py:10",
            attrs={"kind": "property"},
        )
        snapshot = _snapshot(tmp_path, (inv_edge, test_edge))
        assert inv008_violations(snapshot) == ()

    # frob:tests tests/unit/test_design_invariants.py::TestInv008.test_non_property_kind_test_does_not_clear  # noqa: E501
    def test_non_property_kind_test_does_not_clear(self, tmp_path: Path) -> None:
        inv_edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.INVARIANT,
            target="INV-043",
            origin="a.py:10",
            attrs={"establishes": "richer state always wins unless outranked"},
        )
        test_edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.TESTS,
            target="tests/test_a.py::test_newer_one_example",
            origin="a.py:10",
            attrs={"kind": "unit"},
        )
        snapshot = _snapshot(tmp_path, (inv_edge, test_edge))
        assert len(inv008_violations(snapshot)) == 1

    # frob:tests tests/unit/test_design_invariants.py::TestInv008.test_no_obligation_attr_is_unaffected  # noqa: E501
    def test_no_obligation_attr_is_unaffected(self, tmp_path: Path) -> None:
        edge = Edge(
            src="a.py::_newer",
            kind=EdgeKind.INVARIANT,
            target="INV-001",
            origin="a.py:10",
            attrs={},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv008_violations(snapshot) == ()
