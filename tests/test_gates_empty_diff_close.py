"""Tests for T-3092: TICK014 (`frob.gates._empty_diff_close`) -- warn when
a FEATURE/BUG ticket closes done with a diff touching only ticket
bookkeeping (tickets/tickets.md/tickets-archive.md).

Positive controls (per the ticket's own acceptance criteria): a BUG-kind
ticket with no scope exemption that closes with a diff touching only
`tickets/` MUST fire (`test_bug_warns`); the symmetric
FEATURE-kind case also fires. A docs-kind, epic-tier, or
no_scope_declared ticket that closes with an empty code diff MUST stay
quiet (one fixture per exemption, per the acceptance criteria's own "each
exemption needs its own must-stay-quiet fixture" instruction). A ticket
with a REAL code diff, an open (non-done) ticket, and a Done report with
no parsable Changed block at all are additional must-stay-quiet controls
this module's own docstring commits to.
"""

from __future__ import annotations

from datetime import date

from frob.gates._empty_diff_close import empty_code_diff_violations
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
)


def _changed_block(*lines: str) -> str:
    """Render lines as the exact `### Changed` fenced shape
    `frob.tickets._evidence.render_changed_block` produces, so fixtures
    exercise the real parse target rather than a hand-approximated one."""
    body = "\n".join(lines)
    return f"### Changed\n```\n{body}\n```\n"


def _ticket(
    *,
    ticket_id: str,
    kind: TicketKind = TicketKind.BUG,
    state: TicketState = TicketState.DONE,
    tier: TicketTier = TicketTier.TICKET,
    no_scope_declared: bool = False,
    body: str = "",
) -> Ticket:
    """Minimal Done-ticket fixture, same shape `test_gates_milestone.py::
    _ticket` uses (kept as its own local copy for the same "two unrelated
    test modules should not couple on a tiny constructor" reasoning that
    file's docstring gives)."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=Priority.MEDIUM,
        blocked_by=(),
        parent=None,
        tier=tier,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body=body,
        no_scope_declared=no_scope_declared,
    )


class TestTick014:
    """`empty_code_diff_violations(queue)` -- TICK014."""

    def test_bug_warns(self) -> None:
        """MUST-FIRE: a done BUG-kind ticket whose Changed block lists
        only a `tickets/` path fires TICK014."""
        t = _ticket(
            ticket_id="T-9001",
            kind=TicketKind.BUG,
            body=_changed_block(
                " tickets/T-9001/ticket.md | 12 +++++++",
                " 1 file changed, 12 insertions(+)",
            ),
        )
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(queue)
        assert len(violations) == 1
        assert violations[0].rule == "TICK014"
        assert "T-9001" in violations[0].message

    def test_feature_warns(self) -> None:
        """MUST-FIRE: the symmetric FEATURE-kind case, and the exact
        `(no changed files detected)` sentinel (a ticket with a Done
        report but literally zero diff, `render_changed_block`'s other
        output shape)."""
        t = _ticket(
            ticket_id="T-9002",
            kind=TicketKind.FEATURE,
            body="### Changed\n(no changed files detected)\n",
        )
        queue = TicketQueue(tickets={t.id: t})
        violations = empty_code_diff_violations(queue)
        assert len(violations) == 1
        assert violations[0].rule == "TICK014"

    def test_docs_kind_quiet(self) -> None:
        """MUST-STAY-QUIET: a docs-kind ticket legitimately closes with
        only a ledger-touching diff -- no code was ever expected."""
        t = _ticket(
            ticket_id="T-9003",
            kind=TicketKind.DOCS,
            body=_changed_block(" tickets/T-9003/ticket.md | 5 +++"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()

    def test_epic_tier_quiet(self) -> None:
        """MUST-STAY-QUIET: an epic-tier rollup ticket legitimately closes
        without its own code diff (its descendants carry the code)."""
        t = _ticket(
            ticket_id="T-9004",
            kind=TicketKind.BUG,
            tier=TicketTier.EPIC,
            body=_changed_block(" tickets/T-9004/ticket.md | 3 +"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()

    def test_no_scope_quiet(self) -> None:
        """MUST-STAY-QUIET: a ticket with an explicit `no_scope_declared`
        opt-out (a decision record, per this module's own docstring) --
        the ticket already told the ledger it never expected a code
        diff."""
        t = _ticket(
            ticket_id="T-9005",
            kind=TicketKind.BUG,
            no_scope_declared=True,
            body=_changed_block(" tickets/T-9005/ticket.md | 8 ++++"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()

    def test_real_diff_quiet(self) -> None:
        """MUST-STAY-QUIET: a done BUG ticket whose Changed block touches
        a real source file alongside the ticket file -- the normal,
        expected shape."""
        t = _ticket(
            ticket_id="T-9006",
            kind=TicketKind.BUG,
            body=_changed_block(
                " src/frob/gitio.py | 4 ++--",
                " tickets/T-9006/ticket.md | 12 +++++++",
                " 2 files changed, 14 insertions(+), 2 deletions(-)",
            ),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()

    def test_no_block_quiet(self) -> None:
        """MUST-STAY-QUIET: a Done report with no parsable `### Changed`
        block at all (predates T-0458, or a hand-written narrative) is a
        disclosed "cannot tell" gap, not a claimed empty diff -- silent,
        never a false-positive finding."""
        t = _ticket(
            ticket_id="T-9007",
            kind=TicketKind.BUG,
            body="## Done report\n\nDid the thing.\n",
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()

    def test_open_never_fires(self) -> None:
        """MUST-STAY-QUIET: a non-done ticket (queued here) never fires --
        it has not closed yet, so there is nothing to check."""
        t = _ticket(
            ticket_id="T-9008",
            kind=TicketKind.BUG,
            state=TicketState.QUEUED,
            body=_changed_block(" tickets/T-9008/ticket.md | 2 ++"),
        )
        queue = TicketQueue(tickets={t.id: t})
        assert empty_code_diff_violations(queue) == ()
