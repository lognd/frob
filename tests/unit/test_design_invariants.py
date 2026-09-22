"""INV007/INV008 gate tests (T-0757, docs/modules/gates.md#inv007-inv008-t-0757):
`frob.gates._design_invariants.inv007_violations`/`inv008_violations`
directly, over a hand-built `GraphSnapshot` -- no full `frob check` run
needed since both functions are pure over their inputs.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._design_invariants import (
    inv007_violations,
    inv008_violations,
    inv011_violations,
)
from frob.graph import Edge, EdgeKind, GraphSnapshot


def _snapshot(root: Path, edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A minimal `GraphSnapshot` carrying only `edges` -- both gates under
    test read nothing else off the snapshot."""
    return GraphSnapshot(root=str(root), symbols={}, edges=edges)


class TestInv007:
    """`frob:invariant ... no_import="..."` (import-forbidding)."""

    # frob:tests tests/unit/test_design_invariants.py::TestInv007.test_forbidden_import_fires  # noqa: E501
    # frob:tests src/frob/gates/_design_invariants.py::inv007_violations  # noqa: E501
    # frob:tests src/frob/arch/_normalized.py  # noqa: E501
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
# frob:tests src/frob/gates/_design_invariants.py::inv008_violations  # noqa: E501

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


class TestInv011:
    """`frob:invariant ... guards="..." entrypoints="..."` (forbidden-
    constant reachability, F-175/T-3962)."""

    _MODULE_SRC = """
_EXCLUDED_TABLES = frozenset({"users"})


def _sink(table):
    return table


def _guarded_entry(table):
    if table in _EXCLUDED_TABLES:
        return None
    return _sink(table)


def _unguarded_entry(table):
    return _sink(table)
"""

    def _write_module(self, tmp_path: Path) -> Path:
        mod = tmp_path / "writer.py"
        mod.write_text(self._MODULE_SRC)
        return mod

    # frob:tests tests/unit/test_design_invariants.py::TestInv011.test_unguarded_path_fires  # noqa: E501
    def test_unguarded_path_fires(self, tmp_path: Path) -> None:
        """Positive control: `_unguarded_entry` reaches `_sink` without
        ever consulting `_EXCLUDED_TABLES` -- INV011 must fire, naming
        the entrypoint."""
        self._write_module(tmp_path)
        edge = Edge(
            src="writer.py::_sink",
            kind=EdgeKind.INVARIANT,
            target="INV-100",
            origin="writer.py:5",
            attrs={
                "guards": "_EXCLUDED_TABLES",
                "entrypoints": "writer.py::_unguarded_entry",
            },
        )
        snapshot = _snapshot(tmp_path, (edge,))
        violations = inv011_violations(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].rule == "INV011"
        assert "writer.py::_unguarded_entry" in violations[0].message
        assert "_sink" in violations[0].message

    # frob:tests tests/unit/test_design_invariants.py::TestInv011.test_guarded_path_clears  # noqa: E501
    def test_guarded_path_clears(self, tmp_path: Path) -> None:
        """Negative control (same module/graph): `_guarded_entry`
        references `_EXCLUDED_TABLES` before ever reaching `_sink` -- no
        finding for that entrypoint."""
        self._write_module(tmp_path)
        edge = Edge(
            src="writer.py::_sink",
            kind=EdgeKind.INVARIANT,
            target="INV-100",
            origin="writer.py:5",
            attrs={
                "guards": "_EXCLUDED_TABLES",
                "entrypoints": "writer.py::_guarded_entry",
            },
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv011_violations(tmp_path, snapshot) == ()

    # frob:tests tests/unit/test_design_invariants.py::TestInv011.test_mixed_entrypoints_fires_only_for_unguarded_one  # noqa: E501
    def test_mixed_entrypoints_fires_only_for_unguarded_one(
        self, tmp_path: Path
    ) -> None:
        """Both entrypoints declared on the same obligation: only the
        genuinely unguarded one produces a finding."""
        self._write_module(tmp_path)
        edge = Edge(
            src="writer.py::_sink",
            kind=EdgeKind.INVARIANT,
            target="INV-100",
            origin="writer.py:5",
            attrs={
                "guards": "_EXCLUDED_TABLES",
                "entrypoints": (
                    "writer.py::_guarded_entry,writer.py::_unguarded_entry"
                ),
            },
        )
        snapshot = _snapshot(tmp_path, (edge,))
        violations = inv011_violations(tmp_path, snapshot)
        assert len(violations) == 1
        assert violations[0].file == "writer.py"
        assert "_unguarded_entry" in violations[0].message

    # frob:tests tests/unit/test_design_invariants.py::TestInv011.test_misnamed_constant_is_not_recognized  # noqa: E501
    def test_misnamed_constant_is_not_recognized(self, tmp_path: Path) -> None:
        """`guards=` naming must match `*_FORBIDDEN`/`*_EXCLUDED`/
        `*_ALLOWED` -- a differently-named attr value is simply not an
        INV011 obligation, not a malformed one."""
        self._write_module(tmp_path)
        edge = Edge(
            src="writer.py::_sink",
            kind=EdgeKind.INVARIANT,
            target="INV-100",
            origin="writer.py:5",
            attrs={
                "guards": "_TABLE_DENYLIST",
                "entrypoints": "writer.py::_unguarded_entry",
            },
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv011_violations(tmp_path, snapshot) == ()

    # frob:tests tests/unit/test_design_invariants.py::TestInv011.test_no_guards_attr_is_unaffected  # noqa: E501
    def test_no_guards_attr_is_unaffected(self, tmp_path: Path) -> None:
        self._write_module(tmp_path)
        edge = Edge(
            src="writer.py::_sink",
            kind=EdgeKind.INVARIANT,
            target="INV-001",
            origin="writer.py:5",
            attrs={},
        )
        snapshot = _snapshot(tmp_path, (edge,))
        assert inv011_violations(tmp_path, snapshot) == ()
