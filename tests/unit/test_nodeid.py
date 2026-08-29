"""Unit tests for `frob.nodeid` (docs/modules/gates.md).

T-3350: `symref_to_nodeid` was extracted out of `frob.gates` into this
dependency-free leaf module to collapse CYCLE001's 16-node `frob.gates`
<-> `frob.tickets` SCC; these cases carry forward T-0324's parametrized-
case bracket-handling regression coverage against the new home.
"""

from __future__ import annotations

from frob.nodeid import symref_to_nodeid


def test_plain_dotted_qualname_becomes_double_colon() -> None:
    # frob:tests src/frob/nodeid.py::symref_to_nodeid kind="unit"
    """A bare `Class.method` qualname converts every dot to `::`."""
    assert (
        symref_to_nodeid("tests/test_gates.py::TestFoo.test_bar")
        == "tests/test_gates.py::TestFoo::test_bar"
    )


def test_bracketed_case_suffix_dots_pass_through_unchanged() -> None:
    # frob:tests src/frob/nodeid.py::symref_to_nodeid kind="unit"
    """T-0324: a parametrize case id's own literal dots (e.g. a version
    string) inside `[...]` are NOT touched -- only the pre-bracket qualname
    is dot-to-`::` converted."""
    assert (
        symref_to_nodeid("tests/test_lang.py::Foo.bar[015-python-3.11.4]")
        == "tests/test_lang.py::Foo::bar[015-python-3.11.4]"
    )


def test_no_qualname_separator_is_a_noop_on_the_path_side() -> None:
    # frob:tests src/frob/nodeid.py::symref_to_nodeid kind="unit"
    """A bare path with no `::qualname` at all round-trips through
    unchanged (empty qualname before and after)."""
    assert symref_to_nodeid("tests/test_gates.py") == "tests/test_gates.py::"
