"""Symref -> pytest node id spelling (docs/modules/gates.md,
docs/modules/tickets-data-storage.md).

T-3350: extracted out of `frob.gates` into this dependency-free leaf module
so `frob.gates` and `frob.tickets._scope_coverage` can both import it
without either package importing the other -- the ONE genuine runtime
back-edge closing CYCLE001's 16-node `frob.gates` <-> `frob.tickets` SCC
was `frob.tickets._scope_coverage`'s top-level `from frob.gates import
_symref_to_nodeid` for a pure string-transform helper with no dependency
on either package's own state. Home chosen over `frob.gates` (its prior
home) and `frob.testing` (arguably the closer domain fit, since this
produces pytest node ids) because `frob.testing` is not itself a leaf --
routing through it would just relocate the cycle rather than collapse it.
Deliberately NOT re-exported from `frob/__init__.py`: doing so would
create a new import-time edge from the package root into every one of
this module's callers' callers, trading one hub edge for another.
"""

from __future__ import annotations


# frob:doc docs/modules/gates.md#frobnodeid-t-3350
# frob:ticket T-0324
# frob:ticket T-3350
# T-3413: the WIRE001 alias-attribution gap this waiver used to
# paper over is fixed at the source, not waived -- frob.gates.__init__ and
# frob.tickets._scope_coverage now import `symref_to_nodeid` under its real
# name (no more `as _symref_to_nodeid`), so static call-graph analysis sees
# every real call site directly. A WIRE001 waiver was the wrong mechanism
# for a permanent alias choice; removing the alias removed the need for one.
# frob:tests tests/unit/test_nodeid.py::test_plain_dotted_qualname_becomes_double_colon kind="unit"  # noqa: E501
# frob:tests tests/unit/test_nodeid.py::test_bracketed_case_suffix_dots_pass_through_unchanged kind="unit"  # noqa: E501
# frob:tests tests/unit/test_nodeid.py::test_no_qualname_separator_is_a_noop_on_the_path_side kind="unit"  # noqa: E501
def symref_to_nodeid(symref: str) -> str:
    """`path::a.b` -> `path::a::b`, the pytest node id spelling of a qualname.

    frob:ticket T-0324
    A parametrized test's `frob:tests`/evidence symref carries its case
    suffix verbatim (`path::a.b[015-python-3.11.4]`) -- pytest node ids for
    a `@pytest.mark.parametrize`-expanded case routinely contain their own
    literal dots (version strings, floats, dotted module paths passed as
    case values). A blanket `qualname.replace('.', '::')` over the WHOLE
    qualname corrupted those in-bracket dots too (`3.11.4` ->`3::11::4`),
    so a bracketed case id could never resolve against its real collected
    node id even though the bracket-less base did (only the base's dots,
    if any, sit outside a `[...]` suffix). Only the qualname portion before
    the first `[` is a dotted Class.method path; the `[...]` suffix (if
    any) is opaque pytest-generated case text and must pass through
    unchanged."""
    path, _, qualname = symref.partition("::")
    head, bracket, tail = qualname.partition("[")
    return f"{path}::{head.replace('.', '::')}{bracket}{tail}"
