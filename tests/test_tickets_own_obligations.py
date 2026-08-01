"""T-1384: regression tests for `transition`/`reverify_close_guard`'s
`own_obligations_clean` injected parameter -- the tickets-package half of
closing the T-1377/T-1379/T-1381 residue class, where a ticket closed
clean (via a `--ticket`-scoped close/gate sweep) and left its OWN new
public symbols with no `frob:doc` edge, its own new public test classes
undeclared on the testsuite strata node, or its own changed public API
with no REL001 bump -- surfacing only on the NEXT unscoped `frob check`
as someone else's surprise.

Mirrors `tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose`'s
shape exactly: `own_obligations_clean` is injected (never computed inside
`frob.tickets`, per that module's docstring -- the actual COV001/
SELFAUDIT/REL computation lives in `frob.gates`/`frob.app`, outside this
ticket's declared scope), so these tests only exercise the state-machine
guard clause itself: `False` refuses with `OwnObligationsUnclean`, `True`
allows, `None` (the default, matching every pre-T-1384 caller) is fully
permissive."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    transition,
)
from frob.tickets._store import atomic_write, ledger_path, write_ticket


def _ticket(
    *,
    state: TicketState = TicketState.IN_PROGRESS,
    evidence: tuple[str, ...] = (),
    body: str = "",
) -> Ticket:
    return Ticket(
        id="T-0001",
        title="Own obligations test ticket",
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        state=state,
        evidence=evidence,
        body=body,
    )


def _write(root: Path, ticket: Ticket) -> None:
    atomic_write(ledger_path(root), "# Tickets\n\n")
    assert write_ticket(root, ticket).is_ok


class TestT1384OwnObligationsOnClose:
    """`own_obligations_clean=False` refuses `done` naming the exact
    remedy; `True` allows it; `None` (the default) is fully permissive --
    mirroring T-0844's own injected-boolean test shape."""

    def test_transition_rejects_when_own_obligations_clean_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_rejects_when_own_obligations_clean_false kind="unit"  # noqa: E501
        ticket = _ticket(
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, own_obligations_clean=False
        )
        assert result.is_err
        assert result.danger_err == TicketError.OwnObligationsUnclean

    def test_transition_allows_when_own_obligations_clean_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_allows_when_own_obligations_clean_true kind="unit"  # noqa: E501
        ticket = _ticket(
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, own_obligations_clean=True
        )
        assert result.is_ok

    def test_transition_permissive_when_own_obligations_clean_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_own_obligations.py::TestT1384OwnObligationsOnClose.test_transition_permissive_when_own_obligations_clean_none kind="unit"  # noqa: E501
        ticket = _ticket(
            evidence=("tests/test_thing.py::test_x",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok
