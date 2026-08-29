from pathlib import Path

from frob.graph import EdgeKind, GraphSnapshot
from frob.nodeid import symref_to_nodeid as _symref_to_nodeid
from frob.tickets import Ticket
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    is_cmd_evidence,
    scope_has_python_surface,
    scope_matches,
)


# frob:ticket T-0398
# frob:doc docs/modules/gates.md#public-api
# frob:tests \
# tests/test_evidence_integrity.py::TestD02ScopeBinding.test_evidence_covers_scope_true\
# _for_bound_test
def evidence_covers_scope(ticket: Ticket, snapshot: GraphSnapshot) -> bool:
    """D-02: whether at least one of `ticket`'s non-cmd evidence ids binds
    to a symbol/file under `ticket.scope`, via EITHER of two routes:

    1. A `TESTS` edge: walks the same `TESTS`-edge graph
       `frob.testing.select_tests` builds selections from, from the
       evidence side -- for each evidence id, find the `TESTS` edge whose
       test-side symref maps (via `_symref_to_nodeid`, honoring T-0137's
       either-direction `frob:tests` convention) to that id, and check
       whether the OTHER (source) side's file falls under `ticket.scope`.
    2. The evidence id's OWN file is directly inside `ticket.scope` --
       e.g. a ticket scoped to both its source AND its test file
       (`scope: [src/foo.py, tests/test_foo.py]`, this repo's own common
       convention, see T-0398's own ticket entry) needs no separate
       `frob:tests` directive for its evidence to count as covering: the
       human/agent already declared the test file itself in scope, which
       is exactly as strong a binding signal as a graph edge would be.

    Without either route, ANY collected pytest node id (however unrelated
    to the ticket) satisfies close/land -- `frob ticket evidence
    T-feature-x tests/test_logging.py::test_levels` closed T-feature-x
    just as well as a real covering test.

    A caller (today: `frob.app.ticket_runner`'s `_close`/`_land`, via
    `_covers_scope_for_ticket`/`_land_covers_scope_fn`; see
    `_done_transition_guard`'s `covers_scope` docstring for why it is
    injected rather than automatic) computes this against a
    `GraphSnapshot` and passes the result into
    `frob.tickets.transition`/`land`'s `covers_scope` parameter.

    A docs-kind ticket (T-0444) is exempt from the covering-TEST requirement:
    its scope is documentation/data files with no coverable code symbols, and
    T-0215 already sanctions it closing on a `--evidence-cmd` exit status. So
    a ticket whose kind permits cmd evidence (`CMD_EVIDENCE_ALLOWED_KINDS`,
    today `docs`/`ux`) and which carries at least one real cmd: evidence entry
    is considered covered.

    T-3156: the SAME cmd: route also opens for any OTHER kind whose entire
    declared scope has no Python file at all (`scope_has_python_surface`,
    a real filesystem check, never inferred from ticket.kind or glob text
    alone) -- frob's obligation graph only ever indexes Python source, so a
    Rust-only crate or a docs/ledger-only `bug`-kind investigation ticket
    has no OTHER legitimate D-02 route (T-3147's audit named both gaps).
    A ticket with even one Python file in scope still requires kind in
    `CMD_EVIDENCE_ALLOWED_KINDS`, unchanged -- this can never loophole a
    real Python code change into closing on an unrelated command."""
    if (
        ticket.kind in CMD_EVIDENCE_ALLOWED_KINDS
        or not scope_has_python_surface(Path(snapshot.root), ticket.scope)
    ) and any(is_cmd_evidence(evidence) for evidence in ticket.evidence):
        return True
    # T-1944: `evidence_scope` covers a pre-existing test's file with NO
    # write-lease claim (see the field's own docstring) -- checked here
    # alongside `scope` so D-02 still holds for evidence recorded there,
    # without that evidence ever having to widen `scope` (and thus a
    # lease) just to stay provably covered.
    combined_scope = ticket.scope + ticket.evidence_scope
    return any(
        not is_cmd_evidence(evidence)
        and (
            _evidence_binds_to_scope(evidence, combined_scope, snapshot)
            or scope_matches(evidence.split("::", 1)[0], combined_scope)
        )
        for evidence in ticket.evidence
    )


def _evidence_binds_to_scope(
    evidence: str, scope: tuple[str, ...], snapshot: GraphSnapshot
) -> bool:
    """Whether `evidence` (a pytest/cargo node id) is the test-side of some
    `TESTS` edge whose source-side symbol's file is covered by `scope`."""
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        for test_side, source_side in (
            (edge.src, edge.target),
            (edge.target, edge.src),
        ):
            if _node_id_matches_symref(
                evidence, test_side
            ) and _file_of_symref_in_scope(source_side, scope):
                return True
    return False


# frob:ticket T-1396
# frob:tests tests/gates/test_scope_symref_helpers.py::TestNodeIdMatchesSymref
def _node_id_matches_symref(evidence: str, symref: str) -> bool:
    """Whether `evidence` (a pytest/cargo node id) is the test named by
    `symref`: exact `_symref_to_nodeid` match (or its parametrize-expanded
    form), or -- for a bare test FILE symref with no `::` -- the file
    itself (or a path under it)."""
    if "::" not in symref:
        return evidence == symref or evidence.startswith(symref.rstrip("/") + "/")
    node_id = _symref_to_nodeid(symref)
    return evidence == node_id or evidence.startswith(node_id + "[")


# frob:ticket T-1396
# frob:tests tests/gates/test_scope_symref_helpers.py::TestFileOfSymrefInScope
def _file_of_symref_in_scope(symref: str, scope: tuple[str, ...]) -> bool:
    """Whether `symref`'s file (the part before `::`, or itself if bare)
    is covered by `scope` (`scope_matches`)."""
    path = symref.split("::", 1)[0]
    return scope_matches(path, scope)
