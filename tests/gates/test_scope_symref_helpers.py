"""T-1396 TEST005 burn-down: three small `frob.gates.__init__` helper
functions used by the ticket-evidence/scope machinery
(`_macro_symbol_file`, `_node_id_matches_symref`,
`_file_of_symref_in_scope`) had no direct unit test anywhere in the
suite -- only indirect exercise through larger integration-shaped
tests (`evidence_covers_scope`, `_evidence_binds_to_scope`) that never
walk every one of their own branches. This file pins each function's
branches directly: the macro-suffix match/no-match/no-separator paths,
the bare-file-vs-dotted-symref paths for node-id matching, and the
bare-vs-scoped-path split for scope containment."""

from __future__ import annotations

from frob.gates import (
    _file_of_symref_in_scope,
    _macro_symbol_file,
    _node_id_matches_symref,
)


class TestMacroSymbolFile:
    """`_macro_symbol_file` recognizes a T-0318 macro stand-in symref and
    extracts its file path; anything else yields None."""

    def test_no_separator_returns_none(self) -> None:
        """A bare path with no `::` qualname part has nothing to check --
        must return None (the line-407 guard branch), not raise."""
        assert _macro_symbol_file("strata-core/src/lib.rs") is None

    def test_qualname_not_macro_suffixed_returns_none(self) -> None:
        """A real, non-macro qualname (ordinary function) is not a macro
        stand-in -- returns None."""
        assert _macro_symbol_file("strata-core/src/lib.rs::tests.ordinary_fn") is None

    def test_macro_suffixed_qualname_returns_file_path(self) -> None:
        """A qualname whose leaf ends in the macro-stand-in suffix
        resolves to the file path it names."""
        result = _macro_symbol_file("strata-core/src/parse.rs::tests.proptest!")
        assert result == "strata-core/src/parse.rs"


class TestNodeIdMatchesSymref:
    """`_node_id_matches_symref` matches a pytest/cargo node id against a
    symref, either an exact/parametrized dotted match or a bare-file
    prefix match."""

    def test_bare_file_symref_exact_match(self) -> None:
        """A symref with no `::` is a bare file path -- an evidence id
        equal to it matches."""
        assert _node_id_matches_symref("tests/test_gates.py", "tests/test_gates.py")

    def test_bare_file_symref_prefix_match(self) -> None:
        """A bare-file symref also matches an evidence id nested under it
        as a path prefix (directory-shaped symref)."""
        assert _node_id_matches_symref(
            "tests/gates/test_foo.py::TestFoo::test_bar", "tests/gates"
        )

    def test_bare_file_symref_no_match(self) -> None:
        """An evidence id under an unrelated path does not match a bare
        file/dir symref."""
        assert not _node_id_matches_symref(
            "tests/other/test_x.py::test_y", "tests/gates"
        )

    def test_dotted_symref_exact_match(self) -> None:
        """A dotted `path::Class.method` symref matches the exact
        `_symref_to_nodeid`-converted pytest node id."""
        assert _node_id_matches_symref(
            "tests/test_gates.py::TestFoo::test_bar",
            "tests/test_gates.py::TestFoo.test_bar",
        )

    def test_dotted_symref_parametrized_match(self) -> None:
        """A dotted symref also matches a parametrize-expanded node id
        (`[...]` suffix on the exact node id)."""
        assert _node_id_matches_symref(
            "tests/test_gates.py::TestFoo::test_bar[case0]",
            "tests/test_gates.py::TestFoo.test_bar",
        )

    def test_dotted_symref_no_match(self) -> None:
        """A dotted symref naming a different test does not match."""
        assert not _node_id_matches_symref(
            "tests/test_gates.py::TestFoo::test_other",
            "tests/test_gates.py::TestFoo.test_bar",
        )


class TestFileOfSymrefInScope:
    """`_file_of_symref_in_scope` strips a symref down to its file path
    (bare, or before `::`) and checks it against a ticket's scope
    globs."""

    def test_dotted_symref_file_in_scope(self) -> None:
        """The file portion of a dotted symref is checked against scope,
        not the whole symref string."""
        assert _file_of_symref_in_scope(
            "src/frob/gates/__init__.py::some_func", ("src/frob/gates/**",)
        )

    def test_dotted_symref_file_out_of_scope(self) -> None:
        """A dotted symref whose file falls outside every scope glob does
        not match."""
        assert not _file_of_symref_in_scope(
            "src/frob/tickets/__init__.py::some_func", ("src/frob/gates/**",)
        )

    def test_bare_path_symref_in_scope(self) -> None:
        """A bare (no `::`) symref is used as-is against scope."""
        assert _file_of_symref_in_scope(
            "src/frob/gates/_coverage.py", ("src/frob/gates/**",)
        )
